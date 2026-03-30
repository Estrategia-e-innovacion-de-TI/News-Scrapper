"""Evidence extraction adapter.

Extracts text fragments (±150 chars) around matched terms,
merges overlapping spans, and formats with [term] highlighting.
"""
from __future__ import annotations

from newsradar_server.domain.model.entities import EvidenceSpan


class EvidenceExtractor:
    """Extracts evidence spans from document text.

    Up to 3 fragments of ±150 chars around each matched term.
    Overlapping spans are merged. Format: "...fragmento con [término] resaltado..."

    Implements: part of ScoringService pipeline.
    """

    def extract(
        self, text: str, matched_terms: list[str], max_spans: int = 3
    ) -> list[EvidenceSpan]:
        """Extract evidence spans from text.

        TODO: Port implementation from extractor/capabilities/classify.py
        """
        raise NotImplementedError("TODO: port EvidenceExtractor from extractor")
