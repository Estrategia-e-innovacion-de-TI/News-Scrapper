"""Capability: severity scoring for classified documents.

SeverityScorer assigns exactly one Severity level {H, M, L} with a
confidence score 0.0–1.0 using a keyword-based heuristic in rules mode.

Heuristic:
  - H if ≥3 high-severity keywords match
  - M if ≥1 high-severity or ≥3 medium-severity keywords match
  - L otherwise
  - Documents <100 chars → L with confidence 0.1, zero evidence spans

In LLM mode the interface is the same but severity + evidence are expected
to come from the same invoke_model call as classification (handled by
LLMClassifier).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..adhoc.match import normalize_text
from ..state import EvidenceSpan
from .classify import ClassifyResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class SeverityResult:
    """Result of severity scoring."""

    severity: str  # "H", "M", or "L"
    confidence: float  # 0.0–1.0
    evidence_spans: list[EvidenceSpan] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Keyword lists
# ---------------------------------------------------------------------------

HIGH_SEVERITY_KEYWORDS: list[str] = [
    "multa",
    "sancion",
    "demanda",
    "fatalidad",
    "muerte",
    "fraude",
    "lavado",
    "terrorismo",
    "corrupcion",
    "soborno",
    "breach",
    "ransomware",
]

MEDIUM_SEVERITY_KEYWORDS: list[str] = [
    "investigacion",
    "denuncia",
    "protesta",
    "bloqueo",
    "accidente",
    "incidente",
    "contaminacion",
    "derrame",
    "incendio",
    "suspension",
]


# ---------------------------------------------------------------------------
# SeverityScorer
# ---------------------------------------------------------------------------


class SeverityScorer:
    """Assigns severity H/M/L to a classified document using keyword heuristics."""

    def __init__(self) -> None:
        # Pre-normalize keyword lists once
        self._high_keywords = [normalize_text(k) for k in HIGH_SEVERITY_KEYWORDS]
        self._medium_keywords = [normalize_text(k) for k in MEDIUM_SEVERITY_KEYWORDS]

    def score(
        self,
        text: str,
        title: str,
        classify_result: ClassifyResult | None = None,
    ) -> SeverityResult:
        """Score severity for a document.

        Parameters
        ----------
        text : str
            Full document text.
        title : str
            Document title.
        classify_result : ClassifyResult | None
            Classification result (unused in rules mode but kept for
            interface parity with LLM mode).

        Returns
        -------
        SeverityResult
            Severity level, confidence, and evidence spans.
        """
        combined = f"{title} {text}".strip()

        # Short-document guard
        if len(combined) < 100:
            return SeverityResult(severity="L", confidence=0.1, evidence_spans=[])

        norm = normalize_text(combined)

        high_matches = self._find_matches(norm, self._high_keywords, HIGH_SEVERITY_KEYWORDS)
        medium_matches = self._find_matches(norm, self._medium_keywords, MEDIUM_SEVERITY_KEYWORDS)

        high_count = len(high_matches)
        medium_count = len(medium_matches)

        severity, confidence = self._determine_severity(high_count, medium_count)

        # Build evidence spans from matched keywords
        all_matches = high_matches + medium_matches
        evidence_spans = self._build_evidence_spans(combined, all_matches)

        return SeverityResult(
            severity=severity,
            confidence=confidence,
            evidence_spans=evidence_spans,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_matches(
        normalized_text: str,
        normalized_keywords: list[str],
        original_keywords: list[str],
    ) -> list[str]:
        """Return original keywords whose normalized form appears in text."""
        matched: list[str] = []
        for norm_kw, orig_kw in zip(normalized_keywords, original_keywords):
            if norm_kw in normalized_text:
                matched.append(orig_kw)
        return matched

    @staticmethod
    def _determine_severity(high_count: int, medium_count: int) -> tuple[str, float]:
        """Apply the heuristic rules and compute confidence.

        Returns (severity, confidence).
        """
        if high_count >= 3:
            # Strong high-severity signal
            confidence = min(0.5 + high_count * 0.1, 1.0)
            return "H", confidence
        if high_count >= 1 or medium_count >= 3:
            # At least some severity signal
            total = high_count + medium_count
            confidence = min(0.3 + total * 0.08, 0.9)
            return "M", confidence
        # Low severity
        if medium_count > 0:
            confidence = 0.2 + medium_count * 0.05
            return "L", min(confidence, 0.5)
        return "L", 0.2

    @staticmethod
    def _build_evidence_spans(
        text: str,
        matched_keywords: list[str],
    ) -> list[EvidenceSpan]:
        """Build up to 3 evidence spans around matched keywords."""
        if not matched_keywords:
            return []

        norm_text = normalize_text(text)
        spans: list[EvidenceSpan] = []

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
            overlaps = False
            for existing in spans:
                if start < existing.end_offset and end > existing.start_offset:
                    overlaps = True
                    break
            if overlaps:
                continue

            fragment = text[start:end]
            spans.append(
                EvidenceSpan(
                    text=fragment,
                    start_offset=start,
                    end_offset=end,
                    matched_term=kw,
                )
            )

        return spans
