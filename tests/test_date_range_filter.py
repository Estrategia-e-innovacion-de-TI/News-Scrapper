"""Tests for date range filtering in ARAS and Riesgos adhoc."""
import pytest

from extractor.adhoc.aras import _in_date_range, build_aras_candidates
from extractor.adhoc.riesgos import build_riesgos_candidates
from extractor.state import QueueItem, FetchMethod


class TestInDateRange:
    def test_no_published_at_included(self):
        assert _in_date_range(None, "2026-01-01", "2026-03-01") is True

    def test_no_range_all_included(self):
        assert _in_date_range("2026-02-15T10:00:00", None, None) is True

    def test_within_range(self):
        assert _in_date_range("2026-02-15T10:00:00", "2026-01-01", "2026-03-01") is True

    def test_before_range(self):
        assert _in_date_range("2025-12-01T10:00:00", "2026-01-01", "2026-03-01") is False

    def test_after_range(self):
        assert _in_date_range("2026-04-01T10:00:00", "2026-01-01", "2026-03-01") is False

    def test_on_boundary_from(self):
        assert _in_date_range("2026-01-01T00:00:00", "2026-01-01", "2026-03-01") is True

    def test_on_boundary_to(self):
        assert _in_date_range("2026-03-01T23:59:59", "2026-01-01", "2026-03-01") is True

    def test_invalid_date_included(self):
        assert _in_date_range("not-a-date", "2026-01-01", "2026-03-01") is True


@pytest.fixture
def dated_queue():
    """Queue items with various dates."""
    return [
        QueueItem(
            source_id="src1",
            url="https://example.com/in-range",
            source_url="https://example.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Bancolombia Q4 results",
            published_at="2026-02-15T10:00:00",
        ),
        QueueItem(
            source_id="src1",
            url="https://example.com/out-of-range",
            source_url="https://example.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Bancolombia annual report",
            published_at="2025-06-01T10:00:00",
        ),
        QueueItem(
            source_id="src1",
            url="https://example.com/no-date",
            source_url="https://example.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Bancolombia news update",
            published_at=None,
        ),
    ]


class TestArasDateFilter:
    def test_filters_out_of_range(self, dated_queue):
        result, counts = build_aras_candidates(
            dated_queue,
            company="Bancolombia",
            date_from="2026-01-01",
            date_to="2026-03-01",
        )
        urls = [q.url for q in result]
        assert "https://example.com/in-range" in urls
        assert "https://example.com/out-of-range" not in urls

    def test_includes_no_date(self, dated_queue):
        result, counts = build_aras_candidates(
            dated_queue,
            company="Bancolombia",
            date_from="2026-01-01",
            date_to="2026-03-01",
        )
        urls = [q.url for q in result]
        assert "https://example.com/no-date" in urls

    def test_no_date_range_includes_all(self, dated_queue):
        result, counts = build_aras_candidates(
            dated_queue,
            company="Bancolombia",
        )
        assert len(result) == 3


class TestRiesgosDateFilter:
    def test_filters_out_of_range(self, dated_queue):
        # Modify titles for riesgos terms
        dated_queue[0].title = "Fraude detectado en banco"
        dated_queue[1].title = "Fraude histórico reportado"
        dated_queue[2].title = "Fraude en investigación"

        result = build_riesgos_candidates(
            dated_queue,
            terms_str="fraude",
            date_from="2026-01-01",
            date_to="2026-03-01",
        )
        urls = [q.url for q in result]
        assert "https://example.com/in-range" in urls
        assert "https://example.com/out-of-range" not in urls
        assert "https://example.com/no-date" in urls
