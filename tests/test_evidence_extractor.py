"""Unit tests for EvidenceExtractor.

Validates Requirements 2.3, 2.4, 2.5:
  - Extract up to 3 text fragments of ±150 chars around matched terms
  - Merge overlapping spans into a single span
  - Format: "...fragmento con [término] resaltado..."
"""
from __future__ import annotations

import pytest

from extractor.capabilities.evidence import EvidenceExtractor
from extractor.state import EvidenceSpan


@pytest.fixture
def extractor() -> EvidenceExtractor:
    return EvidenceExtractor()


# ── Basic extraction ──────────────────────────────────────────────────


class TestBasicExtraction:
    def test_single_term_found(self, extractor: EvidenceExtractor):
        text = "A" * 200 + "fraude" + "B" * 200
        spans = extractor.extract(text, ["fraude"])
        assert len(spans) == 1
        assert "[fraude]" in spans[0].text

    def test_term_not_found_returns_empty(self, extractor: EvidenceExtractor):
        text = "Este es un texto largo sin términos relevantes. " * 10
        spans = extractor.extract(text, ["ransomware"])
        assert spans == []

    def test_empty_text_returns_empty(self, extractor: EvidenceExtractor):
        spans = extractor.extract("", ["fraude"])
        assert spans == []

    def test_empty_terms_returns_empty(self, extractor: EvidenceExtractor):
        spans = extractor.extract("texto con fraude", [])
        assert spans == []

    def test_returns_evidence_span_objects(self, extractor: EvidenceExtractor):
        text = "X" * 200 + "multa" + "Y" * 200
        spans = extractor.extract(text, ["multa"])
        assert len(spans) == 1
        assert isinstance(spans[0], EvidenceSpan)
        assert spans[0].matched_term == "multa"
        assert spans[0].start_offset >= 0
        assert spans[0].end_offset <= len(text)


# ── Highlighting ──────────────────────────────────────────────────────


class TestHighlighting:
    def test_term_enclosed_in_brackets(self, extractor: EvidenceExtractor):
        text = "X" * 200 + "sancion grave" + "Y" * 200
        spans = extractor.extract(text, ["sancion"])
        assert len(spans) == 1
        assert "[sancion]" in spans[0].text

    def test_multiple_terms_highlighted(self, extractor: EvidenceExtractor):
        text = "X" * 50 + "fraude y multa detectados" + "Y" * 50
        spans = extractor.extract(text, ["fraude", "multa"])
        # Both terms are close enough to be in one merged span
        combined_text = " ".join(s.text for s in spans)
        assert "[fraude]" in combined_text
        assert "[multa]" in combined_text

    def test_case_insensitive_highlighting(self, extractor: EvidenceExtractor):
        text = "X" * 200 + "FRAUDE detectado" + "Y" * 200
        spans = extractor.extract(text, ["fraude"])
        assert len(spans) == 1
        # The original casing is preserved in the fragment, but brackets are added
        assert "[FRAUDE]" in spans[0].text


# ── Ellipsis markers ─────────────────────────────────────────────────


class TestEllipsis:
    def test_ellipsis_prefix_when_not_at_start(self, extractor: EvidenceExtractor):
        text = "A" * 200 + "fraude" + "B" * 200
        spans = extractor.extract(text, ["fraude"])
        assert spans[0].text.startswith("...")

    def test_ellipsis_suffix_when_not_at_end(self, extractor: EvidenceExtractor):
        text = "A" * 200 + "fraude" + "B" * 200
        spans = extractor.extract(text, ["fraude"])
        assert spans[0].text.endswith("...")

    def test_no_ellipsis_at_document_start(self, extractor: EvidenceExtractor):
        text = "fraude" + "B" * 200
        spans = extractor.extract(text, ["fraude"])
        assert not spans[0].text.startswith("...")

    def test_no_ellipsis_at_document_end(self, extractor: EvidenceExtractor):
        text = "A" * 200 + "fraude"
        spans = extractor.extract(text, ["fraude"])
        assert not spans[0].text.endswith("...")

    def test_short_text_no_ellipsis(self, extractor: EvidenceExtractor):
        text = "fraude detectado"
        spans = extractor.extract(text, ["fraude"])
        assert len(spans) == 1
        assert not spans[0].text.startswith("...")
        assert not spans[0].text.endswith("...")


# ── Max spans limit ──────────────────────────────────────────────────


class TestMaxSpans:
    def test_max_three_spans_default(self, extractor: EvidenceExtractor):
        # Place 5 distinct terms far apart so they don't merge
        parts = []
        terms = ["fraude", "multa", "sancion", "demanda", "soborno"]
        for t in terms:
            parts.append("X" * 400 + t + "Y" * 400)
        text = " ".join(parts)
        spans = extractor.extract(text, terms)
        assert len(spans) <= 3

    def test_custom_max_spans(self, extractor: EvidenceExtractor):
        parts = []
        terms = ["fraude", "multa", "sancion", "demanda"]
        for t in terms:
            parts.append("X" * 400 + t + "Y" * 400)
        text = " ".join(parts)
        spans = extractor.extract(text, terms, max_spans=2)
        assert len(spans) <= 2

    def test_max_spans_zero_returns_empty(self, extractor: EvidenceExtractor):
        text = "X" * 200 + "fraude" + "Y" * 200
        spans = extractor.extract(text, ["fraude"], max_spans=0)
        assert spans == []


# ── Overlapping span merge ───────────────────────────────────────────


class TestOverlappingMerge:
    def test_adjacent_terms_merged(self, extractor: EvidenceExtractor):
        # Two terms close together should produce a single merged span
        text = "X" * 100 + "fraude y multa en la empresa" + "Y" * 100
        spans = extractor.extract(text, ["fraude", "multa"])
        assert len(spans) == 1
        assert "[fraude]" in spans[0].text
        assert "[multa]" in spans[0].text

    def test_non_overlapping_terms_separate(self, extractor: EvidenceExtractor):
        # Two terms far apart should produce separate spans
        text = "X" * 200 + "fraude" + "Y" * 500 + "multa" + "Z" * 200
        spans = extractor.extract(text, ["fraude", "multa"])
        assert len(spans) == 2

    def test_no_overlapping_offsets_in_result(self, extractor: EvidenceExtractor):
        """After merging, no two spans should have overlapping offset ranges."""
        text = "X" * 200 + "fraude" + "Y" * 500 + "multa" + "Z" * 200
        spans = extractor.extract(text, ["fraude", "multa"])
        for i in range(len(spans) - 1):
            assert spans[i].end_offset <= spans[i + 1].start_offset


# ── Window size ──────────────────────────────────────────────────────


class TestWindowSize:
    def test_custom_window_size(self, extractor: EvidenceExtractor):
        text = "A" * 500 + "fraude" + "B" * 500
        spans = extractor.extract(text, ["fraude"], window=50)
        # The span should be roughly 50 + len("fraude") + 50 = ~106 chars
        # (plus brackets and ellipsis)
        raw_len = spans[0].end_offset - spans[0].start_offset
        assert raw_len <= 50 + len("fraude") + 50


# ── Accent / normalization handling ──────────────────────────────────


class TestNormalization:
    def test_accent_insensitive_match(self, extractor: EvidenceExtractor):
        text = "X" * 200 + "sanción ambiental grave" + "Y" * 200
        spans = extractor.extract(text, ["sancion"])
        assert len(spans) == 1
        # The original accented text is preserved in the fragment
        assert "[sanción]" in spans[0].text

    def test_case_insensitive_match(self, extractor: EvidenceExtractor):
        text = "X" * 200 + "MULTA impuesta" + "Y" * 200
        spans = extractor.extract(text, ["multa"])
        assert len(spans) == 1
        assert "[MULTA]" in spans[0].text
