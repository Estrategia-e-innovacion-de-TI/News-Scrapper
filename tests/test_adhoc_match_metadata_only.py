"""Tests for metadata-only matching in ad-hoc mode."""
import pytest

from extractor.adhoc.match import (
    MatchResult,
    metadata_match,
    normalize_term,
    rank_candidates,
)


class TestNormalizeTerm:
    def test_lowercase(self):
        assert normalize_term("Bancolombia") == "bancolombia"
    
    def test_strip_accents(self):
        assert normalize_term("fraude electrónico") == "fraude electronico"
    
    def test_collapse_whitespace(self):
        assert normalize_term("  near   miss  ") == "near miss"


class TestMetadataMatch:
    def test_title_match_scores_higher(self):
        score, matched = metadata_match(
            title="Bancolombia reports Q4 earnings",
            snippet="Financial results for the quarter",
            terms=["bancolombia"],
        )
        assert score > 0
        assert "bancolombia" in matched
    
    def test_snippet_match(self):
        score, matched = metadata_match(
            title="Q4 Earnings Report",
            snippet="Bancolombia announced strong results",
            terms=["bancolombia"],
        )
        assert score > 0
        assert "bancolombia" in matched
    
    def test_url_slug_match(self):
        score, matched = metadata_match(
            title="Q4 Earnings Report",
            snippet="Strong results",
            terms=["bancolombia"],
            url="https://example.com/news/bancolombia-q4-results",
        )
        assert score > 0
        assert "bancolombia" in matched
    
    def test_no_match(self):
        score, matched = metadata_match(
            title="Weather forecast for tomorrow",
            snippet="Sunny skies expected",
            terms=["bancolombia", "fraude"],
        )
        assert score == 0.0
        assert matched == []
    
    def test_multiple_terms(self):
        score, matched = metadata_match(
            title="Fraude bancario en Bancolombia",
            snippet="Investigación de lavado de activos",
            terms=["fraude", "bancolombia", "lavado"],
        )
        assert len(matched) >= 2
        assert score > 0
    
    def test_accent_insensitive(self):
        score, matched = metadata_match(
            title="Investigación de fraude electrónico",
            snippet="",
            terms=["fraude electronico"],
        )
        assert score > 0
    
    def test_empty_terms(self):
        score, matched = metadata_match("Title", "Snippet", [])
        assert score == 0.0
        assert matched == []


class TestRankCandidates:
    def test_ranks_by_score(self):
        candidates = [
            MatchResult(url="a", source_id="s1", title="A", snippet="", published_at=None, score=0.3),
            MatchResult(url="b", source_id="s1", title="B", snippet="", published_at=None, score=0.8),
            MatchResult(url="c", source_id="s1", title="C", snippet="", published_at=None, score=0.5),
        ]
        ranked = rank_candidates(candidates, topk=2)
        assert len(ranked) == 2
        assert ranked[0].url == "b"
        assert ranked[1].url == "c"
    
    def test_excludes_zero_score(self):
        candidates = [
            MatchResult(url="a", source_id="s1", title="A", snippet="", published_at=None, score=0.0),
            MatchResult(url="b", source_id="s1", title="B", snippet="", published_at=None, score=0.5),
        ]
        ranked = rank_candidates(candidates, topk=5)
        assert len(ranked) == 1
        assert ranked[0].url == "b"
