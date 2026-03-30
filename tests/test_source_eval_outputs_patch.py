"""Tests for source evaluator output generation."""
import pytest
import json
import yaml
from pathlib import Path

from extractor.source_eval.outputs import save_catalog_patch, save_scorecard


@pytest.fixture
def sample_evaluations():
    """Sample evaluation results."""
    return [
        {
            "source_id": "new_rss_source",
            "url": "https://example.com",
            "type": "news",
            "rss_urls": ["https://example.com/feed"],
            "requires_playwright": False,
            "selectors": {},
            "recommended_type": "rss",
            "notes": "RSS detected",
        },
        {
            "source_id": "new_scrape_source",
            "url": "https://scrape.example.com",
            "type": "news",
            "rss_urls": [],
            "requires_playwright": True,
            "selectors": {"article_link_css": "h2 a", "content_css": "article"},
            "recommended_type": "scrape",
            "notes": "Requires JS",
        },
        {
            "source_id": "github_repo",
            "url": "https://github.com/org/repo",
            "type": "repo",
            "provider": "github",
            "recommended_type": "repo",
            "notes": "Mapped to provider: github",
        },
    ]


class TestSaveCatalogPatch:
    def test_creates_patch_file(self, sample_evaluations, tmp_path):
        path = save_catalog_patch(sample_evaluations, tmp_path)
        
        assert path.exists()
        assert path.name == "catalog_patch.yaml"
    
    def test_patch_contains_rss(self, sample_evaluations, tmp_path):
        path = save_catalog_patch(sample_evaluations, tmp_path)
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        patches = data["patches"]
        rss_patch = next(p for p in patches if p["source_id"] == "new_rss_source")
        
        assert rss_patch["type"] == "rss"
        assert "https://example.com/feed" in rss_patch["rss_urls"]
        assert rss_patch["profile_required"] is False
    
    def test_patch_contains_playwright(self, sample_evaluations, tmp_path):
        path = save_catalog_patch(sample_evaluations, tmp_path)
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        patches = data["patches"]
        scrape_patch = next(p for p in patches if p["source_id"] == "new_scrape_source")
        
        assert scrape_patch["requires_playwright"] is True
        assert "article_link_css" in scrape_patch["selectors"]


class TestSaveScorecard:
    def test_creates_scorecard(self, sample_evaluations, tmp_path):
        path = save_scorecard(sample_evaluations, tmp_path)
        
        assert path.exists()
        assert path.name == "source_scorecard.json"
    
    def test_scorecard_content(self, sample_evaluations, tmp_path):
        path = save_scorecard(sample_evaluations, tmp_path)
        
        with open(path) as f:
            data = json.load(f)
        
        assert len(data) == 3
        assert data[0]["source_id"] == "new_rss_source"
