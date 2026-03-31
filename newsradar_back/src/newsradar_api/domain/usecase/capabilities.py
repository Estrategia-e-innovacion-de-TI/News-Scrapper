"""Classification, severity scoring, and evidence extraction capabilities.

Ported from news_radar_mvp/extractor/capabilities/ for use in the backend API.
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Sequence

from newsradar_api.domain.model.pipeline_models import (
    EvidenceSpanDTO,
    SeverityResult as PipelineSeverityResult,
)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ── Classification ──

@dataclass
class ClassifyResult:
    label: str
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

ARAS_KEYWORDS: dict[str, list[str]] = {
    "lavado_activos": ["lavado de activos", "lavado de dinero", "blanqueo", "money laundering", "lavado", "activos ilicitos", "antilavado", "laft"],
    "financiamiento_terrorismo": ["financiamiento del terrorismo", "financiacion del terrorismo", "terrorism financing"],
    "fraude": ["fraude", "estafa", "timo", "fraud", "defraudacion", "fraude financiero", "fraude electronico", "fraude bancario", "falsificacion", "suplantacion", "ponzi"],
    "corrupcion": ["corrupcion", "soborno", "cohecho", "corruption", "bribery", "peculado", "enriquecimiento ilicito"],
    "sanciones": ["sanciones", "sancion", "lista ofac", "ofac", "lista clinton", "sanctions", "embargo", "lista restrictiva"],
    "pep": ["persona expuesta politicamente", "pep", "politically exposed", "funcionario publico"],
    "ambiental": ["ambiental", "medio ambiente", "environmental", "ecologico", "ecosistema", "biodiversidad", "cambio climatico", "sostenibilidad"],
    "social": ["social", "derechos humanos", "human rights", "comunidad", "responsabilidad social", "impacto social"],
    "contaminacion": ["contaminacion", "contaminante", "pollution", "vertido", "residuos toxicos"],
    "deforestacion": ["deforestacion", "tala ilegal", "deforestation", "perdida de bosque"],
    "derrame": ["derrame", "derrame de petroleo", "oil spill", "derrame quimico"],
    "incendio": ["incendio", "incendio forestal", "fire", "wildfire"],
    "conflictos_comunidades": ["conflicto con comunidades", "consulta previa", "consulta popular", "conflicto social"],
    "protestas_bloqueos": ["protesta", "bloqueo", "manifestacion", "paro", "huelga"],
    "accidentes_laborales": ["accidente laboral", "accidente de trabajo", "fatalidad laboral", "siniestro laboral"],
    "desplazamiento_involuntario": ["desplazamiento involuntario", "desplazamiento forzado", "reasentamiento"],
}

RISK_KEYWORDS: dict[str, list[str]] = {
    "cibernetico": ["ciberataque", "ransomware", "phishing", "malware", "ddos", "data leak", "breach", "ciberseguridad", "vulnerabilidad", "hacking", "cyber", "ataque informatico"],
    "operacional": ["operacional", "interrupcion", "falla sistemica", "outage", "caida de servicio", "error operativo", "falla operativa"],
    "fraude": ["fraude", "estafa", "lavado", "ponzi", "falsificacion", "suplantacion", "defraudacion"],
    "asg": ["asg", "esg", "sostenibilidad", "responsabilidad social empresarial", "gobernanza corporativa"],
    "ia": ["inteligencia artificial", "machine learning", "deep learning", "artificial intelligence", "modelo de lenguaje", "riesgo de ia"],
    "talento": ["talento", "rotacion de personal", "fuga de talento", "escasez de talento", "capital humano"],
    "regulatorio": ["regulatorio", "regulacion", "normativa", "cumplimiento", "compliance", "regulatory"],
    "ambiental": ["ambiental", "medio ambiente", "contaminacion", "derrame", "deforestacion", "cambio climatico"],
    "social": ["social", "derechos humanos", "comunidad", "protesta", "conflicto social", "desplazamiento"],
    "laboral": ["laboral", "accidente laboral", "conflicto laboral", "huelga", "sindicato", "trabajo infantil", "fatalidad"],
}

EVENT_KEYWORDS: dict[str, list[str]] = {
    "multa": ["multa", "sancion pecuniaria", "fine"],
    "perdida": ["perdida", "perdida economica", "loss"],
    "outage": ["outage", "caida de servicio", "interrupcion de servicio"],
    "breach": ["breach", "brecha de seguridad", "filtracion de datos", "data breach"],
    "sancion": ["sancion", "sancion administrativa", "penalty"],
    "demanda": ["demanda", "demanda judicial", "lawsuit", "litigio"],
    "fatalidad": ["fatalidad", "muerte", "fallecimiento", "fatality"],
    "derrame": ["derrame", "derrame de petroleo", "oil spill"],
    "incendio": ["incendio", "incendio forestal", "fire"],
    "bloqueo": ["bloqueo", "bloqueo de vias", "blockade"],
    "denuncia": ["denuncia", "denuncia ambiental", "denuncia penal"],
}


class RulesClassifier:
    def __init__(self):
        self._aras_kw = {cat: [normalize_text(kw) for kw in kws] for cat, kws in ARAS_KEYWORDS.items()}
        self._risk_kw = {cat: [normalize_text(kw) for kw in kws] for cat, kws in RISK_KEYWORDS.items()}
        self._event_kw = {evt: [normalize_text(kw) for kw in kws] for evt, kws in EVENT_KEYWORDS.items()}

    def classify(self, text: str, title: str = "", query_type: str = "aras") -> ClassifyResult:
        combined = f"{normalize_text(title)} {normalize_text(text)}"
        kw_dict = self._aras_kw if query_type == "aras" else self._risk_kw

        hits: dict[str, list[str]] = {}
        for cat, kws in kw_dict.items():
            matched = [kw for kw in kws if kw in combined]
            if matched:
                hits[cat] = matched

        if not hits:
            return ClassifyResult(label="otro", confidence=0.0)

        best_cat = max(hits, key=lambda c: len(hits[c]))
        all_matched = []
        for kws in hits.values():
            all_matched.extend(kws)

        n = len(hits[best_cat])
        confidence = min(0.3 + (n - 1) * 0.2, 1.0) if n > 0 else 0.0

        events = self._detect_events(combined) if query_type == "riesgos" else []

        return ClassifyResult(
            label=best_cat, confidence=confidence,
            matched_keywords=list(dict.fromkeys(all_matched)),
            events=events,
        )

    def _detect_events(self, text: str) -> list[str]:
        detected = []
        for evt, kws in self._event_kw.items():
            if any(kw in text for kw in kws):
                detected.append(evt)
        return detected


# ── Severity Scoring ──

HIGH_SEVERITY_KW = ["multa", "sancion", "demanda", "fatalidad", "muerte", "fraude", "lavado", "terrorismo", "corrupcion", "soborno", "breach", "ransomware"]
MEDIUM_SEVERITY_KW = ["investigacion", "denuncia", "protesta", "bloqueo", "accidente", "incidente", "contaminacion", "derrame", "incendio", "suspension"]


@dataclass
class SeverityResult:
    """Legacy dataclass kept for backward compatibility.

    New code should use ``PipelineSeverityResult`` from pipeline_models.
    """
    severity: str  # H, M, L
    confidence: float
    evidence_spans: list[EvidenceSpanDTO] = field(default_factory=list)

    @property
    def evidence(self) -> list[str]:
        """Backward-compatible property returning matched_term strings."""
        return [s.matched_term for s in self.evidence_spans]


class SeverityScorer:
    """Assigns severity H/M/L using keyword heuristics.

    Validates: Requirements 10.1-10.5
    """

    def __init__(self) -> None:
        self._high = [normalize_text(k) for k in HIGH_SEVERITY_KW]
        self._medium = [normalize_text(k) for k in MEDIUM_SEVERITY_KW]

    def score(self, text: str, title: str = "") -> SeverityResult:
        combined = f"{title} {text}".strip()

        # Req 10.4: text <100 chars → L/0.1 with empty evidence_spans
        if len(combined) < 100:
            return SeverityResult(severity="L", confidence=0.1, evidence_spans=[])

        norm = normalize_text(combined)

        high_matches = self._find_matches(norm, self._high, HIGH_SEVERITY_KW)
        medium_matches = self._find_matches(norm, self._medium, MEDIUM_SEVERITY_KW)

        h, m = len(high_matches), len(medium_matches)

        # Req 10.1: H when ≥3 high-severity keywords
        if h >= 3:
            severity, confidence = "H", min(0.5 + h * 0.1, 1.0)
        # Req 10.2: M when ≥1 high or ≥3 medium
        elif h >= 1 or m >= 3:
            total = h + m
            severity, confidence = "M", min(0.3 + total * 0.08, 0.9)
        # Req 10.3: L otherwise
        elif m > 0:
            severity, confidence = "L", min(0.2 + m * 0.05, 0.5)
        else:
            severity, confidence = "L", 0.2

        # Req 10.5: build up to 3 EvidenceSpanDTO with ±150 chars, no overlap
        all_matches = high_matches + medium_matches
        evidence_spans = self._build_evidence_spans(combined, all_matches)

        return SeverityResult(
            severity=severity,
            confidence=confidence,
            evidence_spans=evidence_spans,
        )

    @staticmethod
    def _find_matches(
        normalized_text: str,
        normalized_keywords: list[str],
        original_keywords: list[str],
    ) -> list[str]:
        """Return original keywords whose normalized form appears in text."""
        return [
            orig for norm_kw, orig in zip(normalized_keywords, original_keywords)
            if norm_kw in normalized_text
        ]

    @staticmethod
    def _build_evidence_spans(
        text: str,
        matched_keywords: list[str],
    ) -> list[EvidenceSpanDTO]:
        """Build up to 3 non-overlapping EvidenceSpanDTO around matched keywords."""
        if not matched_keywords:
            return []

        norm_text = normalize_text(text)
        spans: list[EvidenceSpanDTO] = []

        for kw in matched_keywords:
            if len(spans) >= 3:
                break
            norm_kw = normalize_text(kw)
            idx = norm_text.find(norm_kw)
            if idx == -1:
                continue

            start = max(0, idx - 150)
            end = min(len(text), idx + len(norm_kw) + 150)

            # Check overlap with existing spans
            if any(start < s.end_offset and end > s.start_offset for s in spans):
                continue

            spans.append(EvidenceSpanDTO(
                text=text[start:end],
                start_offset=start,
                end_offset=end,
                matched_term=kw,
            ))

        return spans


# ── Evidence Extraction ──

class EvidenceExtractor:
    """Extracts highlighted evidence spans around matched terms.

    Validates: Requirements 11.1-11.5
    """

    def extract(
        self,
        text: str,
        matched_terms: list[str],
        max_spans: int = 3,
        window: int = 150,
    ) -> list[EvidenceSpanDTO]:
        """Extract evidence spans from *text* around *matched_terms*.

        Returns up to *max_spans* ``EvidenceSpanDTO`` objects with:
        - highlighted terms ``[term]`` preserving original case
        - merged overlapping windows
        - ``...`` prefix/suffix when span doesn't start/end at document boundary
        """
        if not text or not matched_terms or max_spans <= 0:
            return []

        norm_text = normalize_text(text)

        # Req 11.1: locate first occurrence per unique term
        hits: list[tuple[int, int, str]] = []  # (start, end, original_term)
        seen_terms: set[str] = set()
        for term in matched_terms:
            norm_term = normalize_text(term)
            if not norm_term or norm_term in seen_terms:
                continue
            idx = norm_text.find(norm_term)
            if idx == -1:
                continue
            seen_terms.add(norm_term)
            hits.append((idx, idx + len(norm_term), term))

        if not hits:
            return []

        # Sort by position
        hits.sort(key=lambda h: h[0])

        # Req 11.2: build ±window char windows and merge overlapping
        windows: list[tuple[int, int, str]] = []
        for hit_start, hit_end, term in hits:
            win_start = max(0, hit_start - window)
            win_end = min(len(text), hit_end + window)
            windows.append((win_start, win_end, term))

        merged = self._merge_windows(windows)

        # Req 11.5: limit to max_spans
        merged = merged[:max_spans]

        # Build EvidenceSpanDTO objects
        spans: list[EvidenceSpanDTO] = []
        for win_start, win_end, primary_term in merged:
            fragment = text[win_start:win_end]

            # Req 11.3: highlight terms with [term] preserving case
            highlighted = self._highlight_terms(fragment, win_start, text, matched_terms)

            # Req 11.4: add ... prefix/suffix
            prefix = "..." if win_start > 0 else ""
            suffix = "..." if win_end < len(text) else ""
            highlighted = f"{prefix}{highlighted}{suffix}"

            spans.append(EvidenceSpanDTO(
                text=highlighted,
                start_offset=win_start,
                end_offset=win_end,
                matched_term=primary_term,
            ))

        return spans

    @staticmethod
    def _merge_windows(
        windows: list[tuple[int, int, str]],
    ) -> list[tuple[int, int, str]]:
        """Merge overlapping (start, end, term) windows.

        Keeps the primary_term of the first (leftmost) window.
        """
        if not windows:
            return []

        sorted_wins = sorted(windows, key=lambda w: w[0])
        merged: list[tuple[int, int, str]] = [sorted_wins[0]]

        for start, end, term in sorted_wins[1:]:
            prev_start, prev_end, prev_term = merged[-1]
            if start <= prev_end:
                merged[-1] = (prev_start, max(prev_end, end), prev_term)
            else:
                merged.append((start, end, term))

        return merged

    @staticmethod
    def _highlight_terms(
        fragment: str,
        fragment_offset: int,
        full_text: str,
        matched_terms: Sequence[str],
    ) -> str:
        """Highlight matched terms in *fragment* with [term] preserving case."""
        norm_fragment = normalize_text(fragment)

        # Collect all (start_in_fragment, end_in_fragment) hits
        hits: list[tuple[int, int]] = []
        for term in matched_terms:
            norm_term = normalize_text(term)
            if not norm_term:
                continue
            search_start = 0
            while True:
                idx = norm_fragment.find(norm_term, search_start)
                if idx == -1:
                    break
                hits.append((idx, idx + len(norm_term)))
                search_start = idx + 1

        if not hits:
            return fragment

        # Sort by position, longer matches first for ties
        hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))

        # Remove overlapping hits (greedy left-to-right)
        filtered: list[tuple[int, int]] = []
        last_end = -1
        for start, end in hits:
            if start >= last_end:
                filtered.append((start, end))
                last_end = end

        # Insert brackets right-to-left to preserve offsets
        result = list(fragment)
        for start, end in reversed(filtered):
            result.insert(end, "]")
            result.insert(start, "[")

        return "".join(result)


# ── Singleton instances ──
_classifier = RulesClassifier()
_severity = SeverityScorer()
_evidence = EvidenceExtractor()


def process_document(text: str, title: str, query_type: str = "aras") -> dict:
    """Run full pipeline: classify → severity → evidence on a single document.

    Returns dict with keys: category, severity, confidence, evidence, evidence_spans, events, matched_keywords
    """
    cr = _classifier.classify(text, title, query_type)
    sr = _severity.score(text, title)

    # Combine matched keywords from classification + severity for evidence extraction
    all_terms = list(cr.matched_keywords) + [s.matched_term for s in sr.evidence_spans]
    evidence_span_objs = _evidence.extract(text, all_terms)

    return {
        "category": cr.label.replace("_", " ").title() if cr.label != "otro" else None,
        "severity": sr.severity,
        "confidence": round(max(cr.confidence, sr.confidence), 2),
        "evidence": [s.text for s in evidence_span_objs],
        "evidence_spans": evidence_span_objs,
        "events": cr.events,
        "matched_keywords": cr.matched_keywords,
    }
