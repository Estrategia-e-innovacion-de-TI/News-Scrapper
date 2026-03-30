"""Tests for deduplication logic."""
import pytest

from extractor.extract.dedupe import Deduplicator, compute_content_hash


class TestComputeContentHash:
    """Tests for compute_content_hash function."""
    
    def test_same_content_same_hash(self):
        """Same title and text should produce same hash."""
        h1 = compute_content_hash("Test Title", "This is the article text content.")
        h2 = compute_content_hash("Test Title", "This is the article text content.")
        assert h1 == h2
    
    def test_different_title_different_hash(self):
        """Different titles should produce different hashes."""
        h1 = compute_content_hash("Title One", "Same text content here.")
        h2 = compute_content_hash("Title Two", "Same text content here.")
        assert h1 != h2
    
    def test_different_text_different_hash(self):
        """Different text should produce different hashes."""
        h1 = compute_content_hash("Same Title", "Text version one.")
        h2 = compute_content_hash("Same Title", "Text version two.")
        assert h1 != h2
    
    def test_normalization_whitespace(self):
        """Whitespace differences should not affect hash."""
        h1 = compute_content_hash("Test Title", "Some text content")
        h2 = compute_content_hash("Test  Title", "Some  text  content")
        assert h1 == h2
    
    def test_normalization_case_title(self):
        """Title case differences should not affect hash (title is normalized)."""
        h1 = compute_content_hash("TEST TITLE", "same text")
        h2 = compute_content_hash("test title", "same text")
        assert h1 == h2
    
    def test_empty_inputs(self):
        """Empty inputs should produce consistent hash."""
        h1 = compute_content_hash("", "")
        h2 = compute_content_hash("", "")
        assert h1 == h2
    
    def test_truncation(self):
        """Long text should be truncated for hashing."""
        long_text = "x" * 5000
        h1 = compute_content_hash("Title", long_text)
        h2 = compute_content_hash("Title", long_text[:2000])
        # Should be same since we truncate to 2000 chars
        assert h1 == h2


class TestDeduplicator:
    """Tests for Deduplicator class."""
    
    def test_add_new_item(self):
        """Adding new item should return True."""
        dedup = Deduplicator()
        result = dedup.add("hash123")
        assert result is True
        assert dedup.count == 1
    
    def test_add_duplicate_item(self):
        """Adding duplicate should return False."""
        dedup = Deduplicator()
        dedup.add("hash123")
        result = dedup.add("hash123")
        assert result is False
        assert dedup.count == 1
    
    def test_is_duplicate(self):
        """is_duplicate should correctly identify seen hashes."""
        dedup = Deduplicator()
        dedup.add("hash123")
        
        assert dedup.is_duplicate("hash123") is True
        assert dedup.is_duplicate("hash456") is False
    
    def test_check_and_add(self):
        """check_and_add should compute hash and track."""
        dedup = Deduplicator()
        
        hash1, is_new1 = dedup.check_and_add("Title", "Text content")
        assert is_new1 is True
        assert len(hash1) == 64  # SHA256 hex
        
        hash2, is_new2 = dedup.check_and_add("Title", "Text content")
        assert is_new2 is False
        assert hash1 == hash2
    
    def test_clear(self):
        """clear should reset the deduplicator."""
        dedup = Deduplicator()
        dedup.add("hash1")
        dedup.add("hash2")
        assert dedup.count == 2
        
        dedup.clear()
        assert dedup.count == 0
        assert dedup.is_duplicate("hash1") is False
