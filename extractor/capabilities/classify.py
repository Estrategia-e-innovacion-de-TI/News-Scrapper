"""Capability: document classification by ARAS category or risk type.

RulesClassifier uses keyword dictionaries loaded from YAML to assign
exactly one label per document. For ``query_type="riesgos"`` it also
detects Materialized_Events.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..adhoc.match import normalize_text
from ..enums import get_valid_categories, Materialized_Events
from .registry import CapabilityDef, register_capability

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ClassifyResult:
    """Result of classification."""
    label: str
    confidence: float
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Keyword dictionaries — ARAS categories
# ---------------------------------------------------------------------------

ARAS_KEYWORDS: dict[str, list[str]] = {
    "lavado_activos": [
        "lavado de activos", "lavado de dinero", "blanqueo", "money laundering",
        "lavado", "activos ilicitos", "legitimacion de capitales",
        "antilavado", "anti-lavado", "laft",
    ],
    "financiamiento_terrorismo": [
        "financiamiento del terrorismo", "financiacion del terrorismo",
        "terrorism financing", "terrorist financing",
        "financiamiento terrorismo", "financiacion terrorismo",
    ],
    "fraude": [
        "fraude", "estafa", "timo", "fraud", "defraudacion",
        "fraude financiero", "fraude electronico", "fraude bancario",
        "falsificacion", "suplantacion", "ponzi", "esquema piramidal",
    ],
    "corrupcion": [
        "corrupcion", "soborno", "cohecho", "corruption", "bribery",
        "peculado", "enriquecimiento ilicito", "trafico de influencias",
        "nepotismo",
    ],
    "sanciones": [
        "sanciones", "sancion", "lista ofac", "ofac", "lista clinton",
        "sanctions", "sanctioned", "embargo", "lista restrictiva",
        "lista vinculantes",
    ],
    "pep": [
        "persona expuesta politicamente", "pep", "politically exposed",
        "funcionario publico", "cargo publico", "persona politicamente expuesta",
    ],
    "ambiental": [
        "ambiental", "medio ambiente", "environmental", "ecologico",
        "ecosistema", "biodiversidad", "cambio climatico", "sostenibilidad",
    ],
    "social": [
        "social", "derechos humanos", "human rights", "comunidad",
        "responsabilidad social", "impacto social",
    ],
    "licencias_permisos_ambientales": [
        "licencia ambiental", "permiso ambiental", "autorizacion ambiental",
        "licencia de operacion ambiental", "estudio de impacto ambiental",
        "eia", "plan de manejo ambiental",
    ],
    "procesos_sancionatorios_ambientales": [
        "proceso sancionatorio ambiental", "sancion ambiental",
        "multa ambiental", "infraccion ambiental", "sancion asa",
        "sancion ministerio de ambiente",
    ],
    "conflictos_comunidades": [
        "conflicto con comunidades", "conflicto comunitario",
        "oposicion comunitaria", "consulta previa", "consulta popular",
        "conflicto social",
    ],
    "protestas_bloqueos": [
        "protesta", "bloqueo", "manifestacion", "paro", "huelga",
        "bloqueo de vias", "marcha", "movilizacion social",
    ],
    "trabajo_infantil_forzoso": [
        "trabajo infantil", "trabajo forzoso", "child labor",
        "forced labor", "explotacion laboral", "contratacion ilegal",
        "trabajo de menores",
    ],
    "traslape_areas_protegidas": [
        "traslape", "area protegida", "parque natural", "reserva natural",
        "zona de reserva", "area de conservacion",
    ],
    "impactos_ambientales_sociales": [
        "impacto ambiental", "impacto social", "impacto ambiental y social",
        "evaluacion de impacto", "pasivo ambiental",
    ],
    "desplazamiento_involuntario": [
        "desplazamiento involuntario", "desplazamiento forzado",
        "reasentamiento", "reubicacion forzada", "desplazamiento",
    ],
    "accidentes_laborales": [
        "accidente laboral", "accidente de trabajo", "incidente laboral",
        "fatalidad laboral", "siniestro laboral", "accidente ocupacional",
    ],
    "contaminacion": [
        "contaminacion", "contaminante", "pollution", "vertido",
        "vertido sin permiso", "contaminacion a rio", "contaminacion del agua",
        "contaminacion del aire", "residuos toxicos",
    ],
    "deforestacion": [
        "deforestacion", "tala ilegal", "tala indiscriminada",
        "deforestation", "perdida de bosque", "arrasamiento",
    ],
    "derrame": [
        "derrame", "derrame de petroleo", "derrame de crudo",
        "oil spill", "derrame quimico", "fuga de sustancias",
    ],
    "incendio": [
        "incendio", "incendio forestal", "fire", "wildfire",
        "conflagracion", "quema",
    ],
    "hallazgo_arqueologico": [
        "hallazgo arqueologico", "sitio arqueologico", "patrimonio cultural",
        "restos arqueologicos", "archaeological",
    ],
    "comunidad_indigena": [
        "comunidad indigena", "pueblo indigena", "indigenous",
        "resguardo indigena", "territorio indigena", "etnia",
        "comunidad etnica",
    ],
}

# ---------------------------------------------------------------------------
# Keyword dictionaries — Risk types
# ---------------------------------------------------------------------------

RISK_KEYWORDS: dict[str, list[str]] = {
    "cibernetico": [
        "ciberataque", "ransomware", "phishing", "malware", "ddos",
        "data leak", "breach", "ciberseguridad", "vulnerabilidad",
        "hacking", "cyber", "cibernetico", "ataque informatico",
    ],
    "operacional": [
        "operacional", "interrupcion", "falla sistemica", "outage",
        "caida de servicio", "error operativo", "incidente operacional",
        "falla operativa", "retraso de actividades productivas",
        "suspension de actividades",
    ],
    "fraude": [
        "fraude", "estafa", "lavado", "ponzi", "esquema piramidal",
        "falsificacion", "suplantacion", "timo", "defraudacion",
    ],
    "asg": [
        "asg", "esg", "ambiental social gobernanza",
        "environmental social governance", "sostenibilidad",
        "responsabilidad social empresarial", "gobernanza corporativa",
    ],
    "ia": [
        "inteligencia artificial", "machine learning",
        "deep learning", "artificial intelligence",
        "modelo de lenguaje", "algoritmo de ia",
        "riesgo de ia", "regulacion de ia",
    ],
    "talento": [
        "talento", "rotacion de personal", "fuga de talento",
        "escasez de talento", "retencion de talento", "capital humano",
        "talent", "workforce",
    ],
    "regulatorio": [
        "regulatorio", "regulacion", "normativa", "cumplimiento",
        "compliance", "regulatory", "ley", "decreto", "resolucion",
        "superintendencia",
    ],
    "ambiental": [
        "ambiental", "medio ambiente", "contaminacion", "derrame",
        "deforestacion", "cambio climatico", "biodiversidad",
        "environmental", "ecologico",
    ],
    "social": [
        "social", "derechos humanos", "comunidad", "protesta",
        "conflicto social", "desplazamiento", "human rights",
    ],
    "laboral": [
        "laboral", "accidente laboral", "conflicto laboral",
        "huelga", "sindicato", "condiciones laborales",
        "trabajo infantil", "trabajo forzoso", "fatalidad",
    ],
}

# ---------------------------------------------------------------------------
# Materialized events keywords
# ---------------------------------------------------------------------------

EVENT_KEYWORDS: dict[str, list[str]] = {
    "multa": ["multa", "multa economica", "sancion pecuniaria", "fine"],
    "perdida": ["perdida", "perdida economica", "perdida financiera", "loss"],
    "outage": ["outage", "caida de servicio", "interrupcion de servicio", "caida del sistema"],
    "breach": ["breach", "brecha de seguridad", "filtracion de datos", "data breach", "data leak"],
    "near_miss": ["near miss", "casi accidente", "incidente sin lesion", "near-miss"],
    "sancion": ["sancion", "sancion administrativa", "sancion regulatoria", "penalty"],
    "demanda": ["demanda", "demanda judicial", "lawsuit", "litigio", "proceso judicial"],
    "suspension_actividades": [
        "suspension de actividades", "cierre de operaciones",
        "suspension de operaciones", "cese de actividades",
    ],
    "suspension_licencia": [
        "suspension de licencia", "revocacion de licencia",
        "cancelacion de licencia", "suspension de permiso",
    ],
    "fatalidad": ["fatalidad", "muerte", "fallecimiento", "deceso", "fatality", "fatal"],
    "bloqueo": ["bloqueo", "bloqueo de vias", "bloqueo de acceso", "blockade"],
    "derrame": ["derrame", "derrame de petroleo", "derrame quimico", "oil spill"],
    "incendio": ["incendio", "incendio forestal", "fire", "conflagracion"],
    "inundacion": ["inundacion", "inundaciones", "flood", "desbordamiento"],
    "denuncia": ["denuncia", "denuncia ambiental", "denuncia laboral", "denuncia penal"],
    "conflicto_laboral": [
        "conflicto laboral", "huelga", "paro laboral",
        "disputa laboral", "labor dispute",
    ],
}

# ---------------------------------------------------------------------------
# RulesClassifier
# ---------------------------------------------------------------------------


class RulesClassifier:
    """Keyword-based document classifier.

    Assigns exactly one label from ARAS_Categories or Risk_Types based on
    keyword matching against normalized text.  For ``query_type="riesgos"``
    it also detects Materialized_Events.
    """

    def __init__(self) -> None:
        # Pre-normalize all keyword dictionaries once
        self._aras_kw: dict[str, list[str]] = {
            cat: [normalize_text(kw) for kw in kws]
            for cat, kws in ARAS_KEYWORDS.items()
        }
        self._risk_kw: dict[str, list[str]] = {
            cat: [normalize_text(kw) for kw in kws]
            for cat, kws in RISK_KEYWORDS.items()
        }
        self._event_kw: dict[str, list[str]] = {
            evt: [normalize_text(kw) for kw in kws]
            for evt, kws in EVENT_KEYWORDS.items()
        }

    # ---- public API -------------------------------------------------------

    def classify(
        self,
        text: str,
        title: str = "",
        query_type: str = "aras",
        categories: list[str] | None = None,
    ) -> ClassifyResult:
        """Classify *text* (+ *title*) into a single category.

        Parameters
        ----------
        text:
            Document body text.
        title:
            Document title (weighted higher).
        query_type:
            ``"aras"`` or ``"riesgos"``.
        categories:
            Optional allowlist of categories to consider.

        Returns
        -------
        ClassifyResult
            With ``label``, ``confidence``, and ``metadata`` containing
            ``reason``, ``matched_keywords``, and (for riesgos) ``events``.
        """
        norm_body = normalize_text(text or "")
        norm_title = normalize_text(title or "")
        combined = f"{norm_title} {norm_body}"

        valid_cats = get_valid_categories(query_type)

        if query_type == "aras":
            return self._classify_aras(combined, valid_cats, categories)
        elif query_type == "riesgos":
            return self._classify_riesgos(combined, valid_cats, categories)
        else:
            return ClassifyResult(
                label="otro",
                confidence=0.0,
                metadata={
                    "reason": f"unknown query_type: {query_type}",
                    "matched_keywords": [],
                },
            )

    # ---- private helpers --------------------------------------------------

    def _match_keywords(
        self,
        text: str,
        keyword_dict: dict[str, list[str]],
        valid_cats: set[str],
        allowed: list[str] | None,
    ) -> dict[str, list[str]]:
        """Return {category: [matched_keywords]} for every category with ≥1 hit."""
        hits: dict[str, list[str]] = {}
        for cat, kws in keyword_dict.items():
            if cat not in valid_cats:
                continue
            if allowed and cat not in allowed:
                continue
            matched = [kw for kw in kws if kw in text]
            if matched:
                hits[cat] = matched
        return hits

    def _best_category(
        self, hits: dict[str, list[str]]
    ) -> tuple[str, list[str]]:
        """Pick the category with the most keyword matches."""
        if not hits:
            return "otro", []
        best_cat = max(hits, key=lambda c: len(hits[c]))
        # Collect all matched keywords across all categories for metadata
        all_matched: list[str] = []
        for kws in hits.values():
            all_matched.extend(kws)
        return best_cat, list(dict.fromkeys(all_matched))  # dedupe, preserve order

    def _compute_confidence(self, hits: dict[str, list[str]], best_cat: str) -> float:
        """Confidence based on number of keyword matches for the best category.

        Scale: 1 match → 0.3, 2 → 0.5, 3 → 0.7, 4 → 0.8, 5+ → 0.9.
        Capped at 1.0.
        """
        if best_cat == "otro" or best_cat not in hits:
            return 0.0
        n = len(hits[best_cat])
        if n == 0:
            return 0.0
        if n == 1:
            return 0.3
        if n == 2:
            return 0.5
        if n == 3:
            return 0.7
        if n == 4:
            return 0.8
        return min(0.9 + (n - 5) * 0.02, 1.0)

    def _classify_aras(
        self,
        text: str,
        valid_cats: set[str],
        allowed: list[str] | None,
    ) -> ClassifyResult:
        hits = self._match_keywords(text, self._aras_kw, valid_cats, allowed)
        best_cat, all_matched = self._best_category(hits)
        confidence = self._compute_confidence(hits, best_cat)

        reason = (
            f"matched {len(hits.get(best_cat, []))} keywords for '{best_cat}'"
            if best_cat != "otro"
            else "no keywords matched any ARAS category"
        )

        return ClassifyResult(
            label=best_cat,
            confidence=confidence,
            metadata={
                "reason": reason,
                "matched_keywords": all_matched,
            },
        )

    def _classify_riesgos(
        self,
        text: str,
        valid_cats: set[str],
        allowed: list[str] | None,
    ) -> ClassifyResult:
        hits = self._match_keywords(text, self._risk_kw, valid_cats, allowed)
        best_cat, all_matched = self._best_category(hits)
        confidence = self._compute_confidence(hits, best_cat)

        # Detect materialized events
        events = self._detect_events(text)

        reason = (
            f"matched {len(hits.get(best_cat, []))} keywords for '{best_cat}'"
            if best_cat != "otro"
            else "no keywords matched any risk type"
        )

        return ClassifyResult(
            label=best_cat,
            confidence=confidence,
            metadata={
                "reason": reason,
                "matched_keywords": all_matched,
                "events": events,
            },
        )

    def _detect_events(self, text: str) -> list[str]:
        """Detect materialized events present in *text*."""
        detected: list[str] = []
        valid_events = {e.value for e in Materialized_Events}
        for evt, kws in self._event_kw.items():
            if evt not in valid_events:
                continue
            if any(kw in text for kw in kws):
                detected.append(evt)
        return detected


# ---------------------------------------------------------------------------
# Module-level singleton & wrapper function
# ---------------------------------------------------------------------------

_classifier = RulesClassifier()


def classify_document(
    text: str,
    title: str = "",
    query_type: str = "aras",
    categories: list[str] | None = None,
) -> ClassifyResult:
    """Classify a document into a category using keyword rules.

    Parameters
    ----------
    text:
        Document body text.
    title:
        Document title.
    query_type:
        ``"aras"`` or ``"riesgos"``.
    categories:
        Optional allowlist of categories.

    Returns
    -------
    ClassifyResult
    """
    return _classifier.classify(text, title, query_type, categories)


# ---------------------------------------------------------------------------
# Register capability
# ---------------------------------------------------------------------------

_cap = CapabilityDef(
    name="classify_document",
    purpose="Classify document into ARAS category or risk type using keyword rules",
    inputs_schema={
        "text": "str",
        "title": "str",
        "query_type": "str",
        "categories": "list[str] | None",
    },
    outputs_schema={"label": "str", "confidence": "float", "metadata": "dict"},
    callable=classify_document,
    tags=["classification", "nlp", "rules"],
)
register_capability(_cap)

__all__ = ["classify_document", "ClassifyResult", "RulesClassifier"]
