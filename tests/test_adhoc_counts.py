"""Tests for matched_candidates / selected_candidates counts in ARAS adhoc."""
import pytest

from extractor.adhoc.aras import build_aras_candidates
from extractor.state import QueueItem, FetchMethod


@pytest.fixture
def many_items():
    """10 items from 2 sources, all matching 'Bancolombia'."""
    items = []
    for i in range(5):
        items.append(QueueItem(
            source_id="src_a",
            url=f"https://a.com/art{i}",
            source_url="https://a.com/rss",
            fetch_method=FetchMethod.RSS,
            title=f"Bancolombia news item {i}",
            published_at="2026-02-15T10:00:00",
        ))
    for i in range(5):
        items.append(QueueItem(
            source_id="src_b",
            url=f"https://b.com/art{i}",
            source_url="https://b.com/rss",
            fetch_method=FetchMethod.RSS,
            title=f"Bancolombia update {i}",
            published_at="2026-02-15T10:00:00",
        ))
    return items


class TestAdhocCounts:
    def test_counts_by_source_returned(self, many_items):
        queue, counts = build_aras_candidates(
            many_items, company="Bancolombia", topk_per_source=3, max_total=100,
        )
        assert "src_a" in counts
        assert "src_b" in counts

    def test_matched_vs_selected(self, many_items):
        """matched_candidates = all that matched; selected = after topk."""
        queue, counts = build_aras_candidates(
            many_items, company="Bancolombia", topk_per_source=2, max_total=100,
        )
        # Each source has 5 matching items, but topk_per_source=2
        matched_a, selected_a = counts["src_a"]
        matched_b, selected_b = counts["src_b"]
        assert matched_a == 5
        assert selected_a == 2
        assert matched_b == 5
        assert selected_b == 2

    def test_global_max_total_limits(self, many_items):
        """max_total limits the final queue length."""
        queue, counts = build_aras_candidates(
            many_items, company="Bancolombia", topk_per_source=5, max_total=3,
        )
        assert len(queue) == 3

    def test_no_matches_empty_counts(self, many_items):
        queue, counts = build_aras_candidates(
            many_items, company="Microsoft", topk_per_source=5, max_total=100,
        )
        assert len(queue) == 0
        assert counts == {}
