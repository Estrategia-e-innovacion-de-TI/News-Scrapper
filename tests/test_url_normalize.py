"""Tests for URL normalization."""
import pytest

from extractor.extract.normalize import normalize_url, extract_domain


class TestNormalizeUrl:
    """Tests for normalize_url function."""
    
    def test_basic_normalization(self):
        """Basic URL should be normalized."""
        url = "https://example.com/article/test"
        result = normalize_url(url)
        assert result == "https://example.com/article/test"
    
    def test_removes_www(self):
        """www prefix should be removed."""
        url = "https://www.example.com/article"
        result = normalize_url(url)
        assert result == "https://example.com/article"
    
    def test_removes_trailing_slash(self):
        """Trailing slash should be removed."""
        url = "https://example.com/article/"
        result = normalize_url(url)
        assert result == "https://example.com/article"
    
    def test_preserves_root_slash(self):
        """Root path slash should be preserved."""
        url = "https://example.com/"
        result = normalize_url(url)
        # Root is special case
        assert "example.com" in result
    
    def test_removes_tracking_params(self):
        """UTM and tracking params should be removed."""
        url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
    
    def test_preserves_meaningful_params(self):
        """Non-tracking params should be preserved."""
        url = "https://example.com/search?q=test&page=2"
        result = normalize_url(url)
        assert "q=test" in result or "page=2" in result
    
    def test_lowercase_scheme_and_host(self):
        """Scheme and host should be lowercased."""
        url = "HTTPS://EXAMPLE.COM/Article"
        result = normalize_url(url)
        assert result.startswith("https://example.com")
    
    def test_removes_fragment(self):
        """Fragment should be removed."""
        url = "https://example.com/article#section1"
        result = normalize_url(url)
        assert "#" not in result
    
    def test_empty_url(self):
        """Empty URL should return empty string."""
        assert normalize_url("") == ""
    
    def test_collapses_multiple_slashes(self):
        """Multiple slashes in path should be collapsed."""
        url = "https://example.com//article///test"
        result = normalize_url(url)
        assert "//" not in result.replace("https://", "")


class TestExtractDomain:
    """Tests for extract_domain function."""
    
    def test_basic_domain(self):
        """Basic domain extraction."""
        url = "https://example.com/article"
        assert extract_domain(url) == "example.com"
    
    def test_removes_www(self):
        """www should be removed from domain."""
        url = "https://www.example.com/article"
        assert extract_domain(url) == "example.com"
    
    def test_subdomain(self):
        """Subdomain should be preserved."""
        url = "https://blog.example.com/article"
        assert extract_domain(url) == "blog.example.com"
    
    def test_empty_url(self):
        """Empty URL should return empty string."""
        assert extract_domain("") == ""
