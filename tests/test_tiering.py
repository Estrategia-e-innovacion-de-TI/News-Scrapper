"""Tests for tiering classification."""
import pytest
import tempfile
import json
from pathlib import Path

from extractor.ops.tiering import classify_sources, build_prod_set


@pytest.fixture
def sample_report():
    """Sample run report for testing."""
    return {
        "by_source": {
            # Tier0: text_ok > 0, errors == 0, no risk flags
            "source_tier0_ok": {
                "source_id": "source_tier0_ok",
                "discovered": 10,
                "fetched_ok": 8,
                "text_ok": 8,
                "errors": 0,
                "errors_by_type": {},
                "avg_text_len": 2500.0,
                "requires_playwright": False,
            },
            # Tier0 but with playwright (demoted to Tier1)
            "source_tier1_playwright": {
                "source_id": "source_tier1_playwright",
                "discovered": 5,
                "fetched_ok": 5,
                "text_ok": 5,
                "errors": 0,
                "errors_by_type": {},
                "avg_text_len": 3000.0,
                "requires_playwright": True,
            },
            # Tier1: low avg_text_len
            "source_tier1_thin": {
                "source_id": "source_tier1_thin",
                "discovered": 5,
                "fetched_ok": 5,
                "text_ok": 5,
                "errors": 0,
                "errors_by_type": {},
                "avg_text_len": 500.0,
                "requires_playwright": False,
            },
            # Tier1: oversized avg_text_len
            "source_tier1_oversized": {
                "source_id": "source_tier1_oversized",
                "discovered": 5,
                "fetched_ok": 5,
                "text_ok": 5,
                "errors": 0,
                "errors_by_type": {},
                "avg_text_len": 100000.0,
                "requires_playwright": False,
            },
            # Tier2: has errors
            "source_tier2_errors": {
                "source_id": "source_tier2_errors",
                "discovered": 10,
                "fetched_ok": 5,
                "text_ok": 3,
                "errors": 5,
                "errors_by_type": {"403": 5},
                "avg_text_len": 2000.0,
                "requires_playwright": False,
            },
            # Tier2: discovered zero
            "source_tier2_no_discover": {
                "source_id": "source_tier2_no_discover",
                "discovered": 0,
                "fetched_ok": 0,
                "text_ok": 0,
                "errors": 0,
                "errors_by_type": {},
                "avg_text_len": 0.0,
                "requires_playwright": False,
            },
            # Tier2: discovered but fetched zero
            "source_tier2_no_fetch": {
                "source_id": "source_tier2_no_fetch",
                "discovered": 10,
                "fetched_ok": 0,
                "text_ok": 0,
                "errors": 0,
                "errors_by_type": {},
                "avg_text_len": 0.0,
                "requires_playwright": False,
            },
        }
    }


class TestClassifySources:
    """Tests for classify_sources function."""
    
    def test_tier0_classification(self, sample_report):
        """Tier0 should contain sources with text_ok > 0, errors == 0, no risk flags."""
        result = classify_sources(sample_report)
        
        assert "source_tier0_ok" in result["tier0"]
        assert "tier0_ok" in result["reasons"]["source_tier0_ok"]
    
    def test_tier1_playwright_demotion(self, sample_report):
        """Sources requiring playwright should be demoted to Tier1."""
        result = classify_sources(sample_report)
        
        assert "source_tier1_playwright" in result["tier1"]
        assert "tier1_requires_playwright" in result["reasons"]["source_tier1_playwright"]
    
    def test_tier1_thin_content(self, sample_report):
        """Sources with low avg_text_len should be Tier1."""
        result = classify_sources(sample_report)
        
        assert "source_tier1_thin" in result["tier1"]
        assert "tier1_low_avg_text" in result["reasons"]["source_tier1_thin"]
    
    def test_tier1_oversized_content(self, sample_report):
        """Sources with oversized avg_text_len should be Tier1."""
        result = classify_sources(sample_report)
        
        assert "source_tier1_oversized" in result["tier1"]
        assert "tier1_oversized_avg_text" in result["reasons"]["source_tier1_oversized"]
    
    def test_tier2_errors(self, sample_report):
        """Sources with errors should be Tier2."""
        result = classify_sources(sample_report)
        
        assert "source_tier2_errors" in result["tier2"]
        assert "tier2_errors:403" in result["reasons"]["source_tier2_errors"]
    
    def test_tier2_discovered_zero(self, sample_report):
        """Sources with discovered == 0 should be Tier2."""
        result = classify_sources(sample_report)
        
        assert "source_tier2_no_discover" in result["tier2"]
        assert "tier2_discovered_zero" in result["reasons"]["source_tier2_no_discover"]
    
    def test_tier2_fetched_zero(self, sample_report):
        """Sources with discovered > 0 but fetched_ok == 0 should be Tier2."""
        result = classify_sources(sample_report)
        
        assert "source_tier2_no_fetch" in result["tier2"]
        assert "tier2_fetched_zero" in result["reasons"]["source_tier2_no_fetch"]
    
    def test_all_sources_classified(self, sample_report):
        """All sources should be classified into exactly one tier."""
        result = classify_sources(sample_report)
        
        all_classified = set(result["tier0"]) | set(result["tier1"]) | set(result["tier2"])
        all_sources = set(sample_report["by_source"].keys())
        
        assert all_classified == all_sources


class TestBuildProdSet:
    """Tests for build_prod_set function."""
    
    def test_mode_b_excludes_thin_content(self, sample_report):
        """Mode B should exclude sources with thin content."""
        result = build_prod_set(sample_report, mode="B")
        
        excluded_ids = [e["source_id"] for e in result["excluded"]]
        assert "source_tier1_thin" in excluded_ids
        
        thin_exclusion = next(e for e in result["excluded"] if e["source_id"] == "source_tier1_thin")
        assert thin_exclusion["reason"] == "thin_content"
    
    def test_mode_b_excludes_oversized(self, sample_report):
        """Mode B should exclude sources with oversized content."""
        result = build_prod_set(sample_report, mode="B")
        
        excluded_ids = [e["source_id"] for e in result["excluded"]]
        assert "source_tier1_oversized" in excluded_ids
        
        oversized_exclusion = next(e for e in result["excluded"] if e["source_id"] == "source_tier1_oversized")
        assert oversized_exclusion["reason"] == "oversized_boilerplate_risk"
    
    def test_mode_b_separates_lanes(self, sample_report):
        """Mode B should separate sources into http and browser lanes."""
        result = build_prod_set(sample_report, mode="B")
        
        # Tier0 OK should be in http_lane
        assert "source_tier0_ok" in result["http_lane"]
        
        # Playwright source should be in browser_lane
        assert "source_tier1_playwright" in result["browser_lane"]
    
    def test_mode_b_excludes_tier2(self, sample_report):
        """Mode B should not include Tier2 sources."""
        result = build_prod_set(sample_report, mode="B")
        
        all_included = set(result["http_lane"]) | set(result["browser_lane"])
        
        assert "source_tier2_errors" not in all_included
        assert "source_tier2_no_discover" not in all_included
        assert "source_tier2_no_fetch" not in all_included
    
    def test_no_overlap_between_lanes(self, sample_report):
        """http_lane and browser_lane should not overlap."""
        result = build_prod_set(sample_report, mode="B")
        
        http_set = set(result["http_lane"])
        browser_set = set(result["browser_lane"])
        
        assert http_set.isdisjoint(browser_set)
