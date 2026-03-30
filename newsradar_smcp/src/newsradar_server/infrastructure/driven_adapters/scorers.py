"""Scoring adapters — SeverityScorer and RelevanceScorer.

SeverityScorer: assigns H/M/L severity with confidence.
RelevanceScorer: calculates 0..100 relevance score with configurable rubric.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from newsradar_server.domain.model.entities import Document, EvidenceSpan


@dataclass
class SeverityResult:
    """Result of severity scoring."""
    severity: str  # H, M, L
    confidence: float  # 0.0–1.0
    evidence_spans: list[EvidenceSpan] = field(default_factory=list)


class SeverityScorer:
    """Assigns severity H/M/L to classified documents.

    Heuristic: H if ≥3 high-severity keywords, M if ≥1 high or ≥3 medium,
    L otherwise. Docs <100 chars → L with confidence 0.1.

    Implements: ScoringService.score_severity
    """

    def score(self, doc: Document, classify_result: Any) -> SeverityResult:
        """Score document severity.

        TODO: Port implementation from extractor/capabilities/classify.py
        """
        raise NotImplementedError("TODO: port SeverityScorer from extractor")


class RelevanceScorer:
    """Calculates relevance score 0..100 with configurable rubric.

    Formula: score = Σ(factor × weight) with 4 factors:
    keyword_density, recency, source_authority, topic_alignment.

    Implements: ScoringService.score_relevance
    """

    def __init__(self, rubric_path: str = "scoring_rubric.yaml") -> None:
        self._rubric_path = rubric_path
        # TODO: Load weights from YAML

    def score(
        self,
        doc: Document,
        query_terms: list[str],
        subscriber_groups: list[str] | None = None,
    ) -> int:
        """Calculate relevance score 0..100.

        TODO: Port implementation from extractor/capabilities/ranking.py
        """
        raise NotImplementedError("TODO: port RelevanceScorer from extractor")
