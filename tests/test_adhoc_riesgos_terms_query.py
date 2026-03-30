"""Tests for Riesgos ad-hoc terms query."""
import pytest

from extractor.adhoc.riesgos import build_riesgos_candidates, parse_terms
from extractor.state import QueueItem, FetchMethod


@pytest.fixture
def sample_queue():
    """Sample queue items."""
    return [
        QueueItem(
            source_id="securityweek",
            url="https://securityweek.com/art1",
            source_url="https://securityweek.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Ransomware attack hits major bank",
        ),
        QueueItem(
            source_id="securityweek",
            url="https://securityweek.com/art2",
            source_url="https://securityweek.com/rss",
            fetch_method=FetchMethod.RSS,
            title="New JavaScript framework released",
        ),
        QueueItem(
            source_id="darkreading",
            url="https://darkreading.com/art1",
            source_url="https://darkreading.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Fraude bancario: near miss en operaciones",
        ),
        QueueItem(
            source_id="darkreading",
            url="https://darkreading.com/art2",
            source_url="https://darkreading.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Cloud computing trends 2026",
        ),
    ]


class TestParseTerms:
    def test_basic(self):
        assert parse_terms("fraude,ransomware") == ["fraude", "ransomware"]
    
    def test_with_spaces(self):
        result = parse_terms("fraude, near miss, ransomware")
        assert result == ["fraude", "near miss", "ransomware"]
    
    def test_empty(self):
        assert parse_terms("") == []


class TestBuildRiesgosCandidates:
    def test_filters_by_terms(self, sample_queue):
        result = build_riesgos_candidates(
            sample_queue,
            "fraude,ransomware,near miss",
            topk_per_source=5,
        )
        
        urls = [q.url for q in result]
        assert "https://securityweek.com/art1" in urls  # ransomware
        assert "https://darkreading.com/art1" in urls  # fraude, near miss
    
    def test_excludes_unrelated(self, sample_queue):
        result = build_riesgos_candidates(
            sample_queue,
            "fraude,ransomware",
            topk_per_source=5,
        )
        
        urls = [q.url for q in result]
        assert "https://securityweek.com/art2" not in urls
        assert "https://darkreading.com/art2" not in urls
    
    def test_no_matches(self, sample_queue):
        result = build_riesgos_candidates(
            sample_queue,
            "quantum computing,blockchain",
            topk_per_source=5,
        )
        assert len(result) == 0
