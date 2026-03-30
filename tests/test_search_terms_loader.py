"""Tests for search terms loader."""
import pytest
import tempfile
from pathlib import Path

import yaml

from extractor.search.loader import load_terms, get_terms_for_mode, get_filters_for_mode


@pytest.fixture
def terms_file(tmp_path):
    """Create a temporary terms YAML file."""
    data = {
        "papers": {
            "terms": ["machine learning risk", "fraud detection"],
            "filters": {"require_keywords_any": ["risk", "fraud"]},
        },
        "repos": {
            "terms": ["langgraph", "news-extraction"],
            "filters": {"min_stars": 50, "updated_within_days": 90},
        },
        "patents": {
            "terms": ["fraud detection AI"],
            "filters": {"date_window_months": 6},
        },
    }
    
    path = tmp_path / "terms.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
    
    return path


class TestLoadTerms:
    def test_loads_file(self, terms_file):
        data = load_terms(terms_file)
        assert "papers" in data
        assert "repos" in data
        assert "patents" in data
    
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_terms("/nonexistent/path.yaml")


class TestGetTermsForMode:
    def test_papers(self, terms_file):
        data = load_terms(terms_file)
        terms = get_terms_for_mode(data, "papers")
        assert "machine learning risk" in terms
        assert len(terms) == 2
    
    def test_repos(self, terms_file):
        data = load_terms(terms_file)
        terms = get_terms_for_mode(data, "repos")
        assert "langgraph" in terms
    
    def test_unknown_mode(self, terms_file):
        data = load_terms(terms_file)
        terms = get_terms_for_mode(data, "unknown")
        assert terms == []


class TestGetFiltersForMode:
    def test_repos_filters(self, terms_file):
        data = load_terms(terms_file)
        filters = get_filters_for_mode(data, "repos")
        assert filters["min_stars"] == 50
        assert filters["updated_within_days"] == 90
    
    def test_papers_filters(self, terms_file):
        data = load_terms(terms_file)
        filters = get_filters_for_mode(data, "papers")
        assert "require_keywords_any" in filters
