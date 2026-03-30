"""Tests for catalog filtering."""
import pytest
import tempfile
import yaml
from pathlib import Path

from extractor.ops.catalog_filter import write_filtered_catalog, write_catalog_prod


@pytest.fixture
def sample_catalog():
    """Sample catalog for testing."""
    return {
        "defaults": {
            "timeout_seconds": 25,
            "rate_limit_rps": 1.0,
        },
        "sources": [
            {"source_id": "source_a", "name": "Source A", "type": "rss"},
            {"source_id": "source_b", "name": "Source B", "type": "scrape"},
            {"source_id": "source_c", "name": "Source C", "type": "rss"},
            {"source_id": "source_d", "name": "Source D", "type": "pdf"},
        ],
    }


@pytest.fixture
def sample_prod_set():
    """Sample prod set for testing."""
    return {
        "http_lane": ["source_a", "source_c"],
        "browser_lane": ["source_b"],
        "excluded": [{"source_id": "source_d", "reason": "thin_content"}],
    }


class TestWriteFilteredCatalog:
    """Tests for write_filtered_catalog function."""
    
    def test_filters_sources(self, sample_catalog):
        """Should only include allowed sources."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            out_path = Path(f.name)
        
        try:
            write_filtered_catalog(sample_catalog, ["source_a", "source_c"], out_path)
            
            with open(out_path) as f:
                result = yaml.safe_load(f)
            
            source_ids = [s["source_id"] for s in result["sources"]]
            assert source_ids == ["source_a", "source_c"]
        finally:
            out_path.unlink(missing_ok=True)
    
    def test_preserves_defaults(self, sample_catalog):
        """Should preserve defaults section."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            out_path = Path(f.name)
        
        try:
            write_filtered_catalog(sample_catalog, ["source_a"], out_path)
            
            with open(out_path) as f:
                result = yaml.safe_load(f)
            
            assert result["defaults"] == sample_catalog["defaults"]
        finally:
            out_path.unlink(missing_ok=True)
    
    def test_preserves_source_content(self, sample_catalog):
        """Should preserve full source content, not just IDs."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            out_path = Path(f.name)
        
        try:
            write_filtered_catalog(sample_catalog, ["source_b"], out_path)
            
            with open(out_path) as f:
                result = yaml.safe_load(f)
            
            assert len(result["sources"]) == 1
            assert result["sources"][0]["name"] == "Source B"
            assert result["sources"][0]["type"] == "scrape"
        finally:
            out_path.unlink(missing_ok=True)
    
    def test_empty_allowed_list(self, sample_catalog):
        """Should handle empty allowed list."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            out_path = Path(f.name)
        
        try:
            write_filtered_catalog(sample_catalog, [], out_path)
            
            with open(out_path) as f:
                result = yaml.safe_load(f)
            
            assert result["sources"] == []
        finally:
            out_path.unlink(missing_ok=True)


class TestWriteCatalogProd:
    """Tests for write_catalog_prod function."""
    
    def test_includes_both_lanes(self, sample_catalog, sample_prod_set):
        """Should include sources from both http and browser lanes."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            out_path = Path(f.name)
        
        try:
            write_catalog_prod(sample_catalog, sample_prod_set, out_path)
            
            with open(out_path) as f:
                result = yaml.safe_load(f)
            
            source_ids = {s["source_id"] for s in result["sources"]}
            assert source_ids == {"source_a", "source_b", "source_c"}
        finally:
            out_path.unlink(missing_ok=True)
    
    def test_excludes_excluded_sources(self, sample_catalog, sample_prod_set):
        """Should not include excluded sources."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            out_path = Path(f.name)
        
        try:
            write_catalog_prod(sample_catalog, sample_prod_set, out_path)
            
            with open(out_path) as f:
                result = yaml.safe_load(f)
            
            source_ids = {s["source_id"] for s in result["sources"]}
            assert "source_d" not in source_ids
        finally:
            out_path.unlink(missing_ok=True)
