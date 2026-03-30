"""Tests for ARAS ad-hoc company query."""
import pytest

from extractor.adhoc.aras import build_aras_candidates, company_to_terms
from extractor.state import QueueItem, FetchMethod


@pytest.fixture
def sample_queue():
    """Sample queue items simulating RSS discovery."""
    return [
        QueueItem(
            source_id="eltiempo",
            url="https://eltiempo.com/art1",
            source_url="https://eltiempo.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Bancolombia reporta resultados del Q4",
            published_at="2026-02-15T10:00:00",
        ),
        QueueItem(
            source_id="eltiempo",
            url="https://eltiempo.com/art2",
            source_url="https://eltiempo.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Economía colombiana crece 3%",
            published_at="2026-02-14T10:00:00",
        ),
        QueueItem(
            source_id="elcolombiano",
            url="https://elcolombiano.com/art1",
            source_url="https://elcolombiano.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Fraude detectado en Bancolombia",
            published_at="2026-02-13T10:00:00",
        ),
        QueueItem(
            source_id="elcolombiano",
            url="https://elcolombiano.com/art2",
            source_url="https://elcolombiano.com/rss",
            fetch_method=FetchMethod.RSS,
            title="Noticias del sector agrícola",
            published_at="2026-02-12T10:00:00",
        ),
    ]


class TestCompanyToTerms:
    def test_single_word(self):
        terms = company_to_terms("Bancolombia")
        assert "Bancolombia" in terms
    
    def test_multi_word(self):
        terms = company_to_terms("Grupo Aval")
        assert "Grupo Aval" in terms
        assert "grupo-aval" in terms


class TestBuildArasCandidates:
    def test_filters_by_company(self, sample_queue):
        result, counts = build_aras_candidates(sample_queue, "Bancolombia", topk_per_source=5)
        
        assert len(result) == 2
        urls = [q.url for q in result]
        assert "https://eltiempo.com/art1" in urls
        assert "https://elcolombiano.com/art1" in urls
    
    def test_excludes_unrelated(self, sample_queue):
        result, counts = build_aras_candidates(sample_queue, "Bancolombia", topk_per_source=5)
        
        urls = [q.url for q in result]
        assert "https://eltiempo.com/art2" not in urls
        assert "https://elcolombiano.com/art2" not in urls
    
    def test_respects_topk(self, sample_queue):
        result, counts = build_aras_candidates(sample_queue, "Bancolombia", topk_per_source=1)
        
        # Should get at most 1 per source
        sources = [q.source_id for q in result]
        from collections import Counter
        counts_per_source = Counter(sources)
        for count in counts_per_source.values():
            assert count <= 1
    
    def test_no_matches(self, sample_queue):
        result, counts = build_aras_candidates(sample_queue, "Microsoft", topk_per_source=5)
        assert len(result) == 0
