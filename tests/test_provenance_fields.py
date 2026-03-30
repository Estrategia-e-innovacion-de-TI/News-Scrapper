"""Tests for provenance fields in Document model."""
import pytest

from extractor.state import Document


class TestDocumentProvenance:
    def test_default_origin(self):
        doc = Document(
            run_id="test",
            source_id="src1",
            pipeline_class="news",
            focus=["general"],
            title="Test",
            url="https://example.com",
            fetched_at="2026-03-16T00:00:00",
            text="content",
            excerpt="content",
            raw_len=100,
            text_len=7,
            hash="abc123",
            fetch_method="http",
            source_url="https://example.com/rss",
        )
        assert doc.origin == "catalog"
        assert doc.query_type is None
        assert doc.query_terms == []
        assert doc.query_range == {}

    def test_adhoc_provenance(self):
        doc = Document(
            run_id="test",
            source_id="src1",
            pipeline_class="news",
            focus=["aras"],
            title="Test",
            url="https://example.com",
            fetched_at="2026-03-16T00:00:00",
            text="content",
            excerpt="content",
            raw_len=100,
            text_len=7,
            hash="abc123",
            fetch_method="http",
            source_url="https://example.com/rss",
            origin="adhoc_query",
            query_type="aras",
            query_terms=["Bancolombia"],
            query_range={"from": "2026-01-01", "to": "2026-03-01"},
        )
        assert doc.origin == "adhoc_query"
        assert doc.query_type == "aras"
        assert doc.query_terms == ["Bancolombia"]
        assert doc.query_range["from"] == "2026-01-01"

    def test_text_capped_field(self):
        doc = Document(
            run_id="test",
            source_id="src1",
            pipeline_class="news",
            focus=[],
            title="Test",
            url="https://example.com",
            fetched_at="2026-03-16T00:00:00",
            text="content",
            excerpt="content",
            raw_len=100,
            text_len=7,
            text_capped=True,
            hash="abc123",
            fetch_method="http",
            source_url="https://example.com/rss",
        )
        assert doc.text_capped is True

    def test_search_ingest_origin(self):
        doc = Document(
            run_id="test",
            source_id="arxiv",
            pipeline_class="papers",
            focus=["vigilancia"],
            title="Paper",
            url="https://arxiv.org/abs/123",
            fetched_at="2026-03-16T00:00:00",
            text="content",
            excerpt="content",
            raw_len=100,
            text_len=7,
            hash="abc123",
            fetch_method="http",
            source_url="https://arxiv.org",
            origin="search_ingest",
        )
        assert doc.origin == "search_ingest"
