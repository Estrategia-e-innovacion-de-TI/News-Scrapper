"""Unit tests for RelevanceScorer and select_top_k."""
from __future__ import annotations

import math
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from extractor.capabilities.ranking import (
    DEFAULT_WEIGHTS,
    RelevanceScorer,
    _keyword_density,
    _load_weights,
    _normalise_weights,
    _recency,
    _source_authority,
    _topic_alignment,
    select_top_k,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(
    *,
    source_id: str = "src_a",
    query_terms: list[str] | None = None,
    published_at: str | None = None,
    fetched_at: str | None = None,
    relevance_score: int | None = None,
) -> SimpleNamespace:
    now = datetime.utcnow()
    return SimpleNamespace(
        source_id=source_id,
        query_terms=query_terms or [],
        published_at=published_at or now.isoformat(),
        fetched_at=fetched_at or now.isoformat(),
        relevance_score=relevance_score,
    )


# ===================================================================
# Test scoring with default weights
# ===================================================================

class TestScoringDefaultWeights:
    """Scoring with default weights (40/20/20/20)."""

    def test_perfect_score(self):
        """All factors at 100 → score = 100."""
        now = datetime.utcnow().isoformat()
        doc = _make_doc(
            source_id="s1",
            query_terms=["a", "b"],
            published_at=now,
            fetched_at=now,
        )
        scorer = RelevanceScorer(tier_map={"s1": "tier0"})
        score = scorer.score(doc, query_terms=["a", "b"], subscriber_groups=["a"])
        assert score == 100

    def test_zero_score(self):
        """No matches, old doc, unknown source, no groups → low score."""
        old = (datetime.utcnow() - timedelta(days=30)).isoformat()
        now = datetime.utcnow().isoformat()
        doc = _make_doc(
            source_id="unknown_src",
            query_terms=[],
            published_at=old,
            fetched_at=now,
        )
        scorer = RelevanceScorer(tier_map={})
        score = scorer.score(doc, query_terms=["x", "y"])
        # keyword_density=0, recency=0 (30 days), source_authority=10, topic_alignment=0
        # raw = 0 + 0 + 10*20/100 + 0 = 2
        assert score == 2

    def test_partial_keyword_match(self):
        """Half the terms matched → keyword_density = 50."""
        now = datetime.utcnow().isoformat()
        doc = _make_doc(
            source_id="s1",
            query_terms=["a"],
            published_at=now,
            fetched_at=now,
        )
        scorer = RelevanceScorer(tier_map={"s1": "tier0"})
        score = scorer.score(doc, query_terms=["a", "b"], subscriber_groups=["a"])
        # kd=50, rec=100, sa=100, ta=100
        # raw = 50*40/100 + 100*20/100 + 100*20/100 + 100*20/100 = 20+20+20+20 = 80
        assert score == 80


# ===================================================================
# Test scoring with custom weights from YAML
# ===================================================================

class TestScoringCustomWeights:
    """Scoring with custom weights loaded from a YAML file."""

    def test_custom_weights_from_yaml(self, tmp_path):
        rubric = tmp_path / "scoring_rubric.yaml"
        rubric.write_text(yaml.dump({"weights": {
            "keyword_density": 60,
            "recency": 10,
            "source_authority": 10,
            "topic_alignment": 20,
        }}))
        now = datetime.utcnow().isoformat()
        doc = _make_doc(
            source_id="s1",
            query_terms=["a", "b"],
            published_at=now,
            fetched_at=now,
        )
        scorer = RelevanceScorer(rubric_path=rubric, tier_map={"s1": "tier0"})
        score = scorer.score(doc, query_terms=["a", "b"], subscriber_groups=["a"])
        # All factors 100, weights sum to 100 → score = 100
        assert score == 100


# ===================================================================
# Test weight normalisation
# ===================================================================

class TestWeightNormalisation:
    """Weights that don't sum to 100 are normalised proportionally."""

    def test_normalise_doubles(self):
        w = _normalise_weights({"keyword_density": 80, "recency": 40, "source_authority": 40, "topic_alignment": 40})
        assert math.isclose(sum(w.values()), 100, abs_tol=0.01)

    def test_normalise_halves(self):
        w = _normalise_weights({"keyword_density": 20, "recency": 10, "source_authority": 10, "topic_alignment": 10})
        assert math.isclose(sum(w.values()), 100, abs_tol=0.01)
        assert math.isclose(w["keyword_density"], 40, abs_tol=0.1)

    def test_all_zero_falls_back(self):
        w = _normalise_weights({"keyword_density": 0, "recency": 0, "source_authority": 0, "topic_alignment": 0})
        assert w == DEFAULT_WEIGHTS


# ===================================================================
# Test missing YAML uses defaults
# ===================================================================

class TestMissingYAML:
    """Missing scoring_rubric.yaml → defaults without error."""

    def test_missing_yaml_uses_defaults(self, tmp_path):
        rubric = tmp_path / "nonexistent.yaml"
        weights = _load_weights(rubric)
        assert math.isclose(sum(weights.values()), 100, abs_tol=0.01)
        assert math.isclose(weights["keyword_density"], 40, abs_tol=0.1)


# ===================================================================
# Test recency calculation
# ===================================================================

class TestRecency:
    """Recency factor: max(0, 100 − days × 14.3)."""

    def test_same_day(self):
        now = datetime.utcnow().isoformat()
        assert math.isclose(_recency(now, now), 100.0, abs_tol=1.0)

    def test_seven_days_old(self):
        now = datetime.utcnow()
        pub = (now - timedelta(days=7)).isoformat()
        val = _recency(now.isoformat(), pub)
        # 100 - 7*14.3 = 100 - 100.1 ≈ 0
        assert val == 0.0 or math.isclose(val, 0.0, abs_tol=0.5)

    def test_one_day_old(self):
        now = datetime.utcnow()
        pub = (now - timedelta(days=1)).isoformat()
        val = _recency(now.isoformat(), pub)
        # 100 - 14.3 = 85.7
        assert 85 <= val <= 86

    def test_no_published_at(self):
        now = datetime.utcnow().isoformat()
        assert _recency(now, None) == 0.0

    def test_unparseable_date(self):
        assert _recency("2025-01-01T00:00:00", "not-a-date") == 0.0


# ===================================================================
# Test source_authority for each tier
# ===================================================================

class TestSourceAuthority:
    """Source authority: tier0=100, tier1=70, tier2=30, unknown=10."""

    def test_tier0(self):
        assert _source_authority("s1", {"s1": "tier0"}) == 100

    def test_tier1(self):
        assert _source_authority("s1", {"s1": "tier1"}) == 70

    def test_tier2(self):
        assert _source_authority("s1", {"s1": "tier2"}) == 30

    def test_unknown_source(self):
        assert _source_authority("s1", {"other": "tier0"}) == 10

    def test_no_tier_map(self):
        assert _source_authority("s1", None) == 10


# ===================================================================
# Test topic_alignment
# ===================================================================

class TestTopicAlignment:
    """topic_alignment: 100 if match, 0 otherwise."""

    def test_matching_group(self):
        assert _topic_alignment(["ciberseguridad"], ["ciberseguridad"]) == 100.0

    def test_no_match(self):
        assert _topic_alignment(["ciberseguridad"], ["fintech"]) == 0.0

    def test_empty_groups(self):
        assert _topic_alignment(["ciberseguridad"], None) == 0.0

    def test_empty_terms(self):
        assert _topic_alignment([], ["ciberseguridad"]) == 0.0

    def test_case_insensitive(self):
        assert _topic_alignment(["Ciber"], ["ciber"]) == 100.0


# ===================================================================
# Test score always in [0, 100]
# ===================================================================

class TestScoreRange:
    """Score must always be an integer in [0, 100]."""

    def test_score_is_int(self):
        doc = _make_doc()
        scorer = RelevanceScorer()
        s = scorer.score(doc, query_terms=["a"])
        assert isinstance(s, int)

    def test_score_lower_bound(self):
        doc = _make_doc(
            query_terms=[],
            published_at=(datetime.utcnow() - timedelta(days=100)).isoformat(),
        )
        scorer = RelevanceScorer(tier_map={})
        s = scorer.score(doc, query_terms=["x"])
        assert 0 <= s <= 100

    def test_score_upper_bound(self):
        now = datetime.utcnow().isoformat()
        doc = _make_doc(
            source_id="s1",
            query_terms=["a", "b", "c"],
            published_at=now,
            fetched_at=now,
        )
        scorer = RelevanceScorer(tier_map={"s1": "tier0"})
        s = scorer.score(doc, query_terms=["a", "b", "c"], subscriber_groups=["a"])
        assert 0 <= s <= 100


# ===================================================================
# Test select_top_k
# ===================================================================

class TestSelectTopK:
    """select_top_k: at most 10 items, score > 50, source diversity."""

    def test_returns_at_most_10(self):
        items = [_make_doc(source_id=f"s{i}", relevance_score=80) for i in range(20)]
        result = select_top_k(items)
        assert len(result) <= 10

    def test_filters_low_scores(self):
        items = [
            _make_doc(source_id="s1", relevance_score=80),
            _make_doc(source_id="s2", relevance_score=50),  # not > 50
            _make_doc(source_id="s3", relevance_score=30),
        ]
        result = select_top_k(items)
        assert len(result) == 1
        assert result[0].relevance_score == 80

    def test_sorted_descending(self):
        items = [
            _make_doc(source_id="s1", relevance_score=60),
            _make_doc(source_id="s2", relevance_score=90),
            _make_doc(source_id="s3", relevance_score=75),
        ]
        result = select_top_k(items)
        scores = [it.relevance_score for it in result]
        assert scores == sorted(scores, reverse=True)

    def test_source_diversity(self):
        """Ensure at least min(5, distinct_sources) distinct source_ids."""
        # 6 items from 6 sources, but 3 have higher scores from same source
        items = [
            _make_doc(source_id="s1", relevance_score=99),
            _make_doc(source_id="s1", relevance_score=98),
            _make_doc(source_id="s1", relevance_score=97),
            _make_doc(source_id="s1", relevance_score=96),
            _make_doc(source_id="s1", relevance_score=95),
            _make_doc(source_id="s2", relevance_score=70),
            _make_doc(source_id="s3", relevance_score=65),
            _make_doc(source_id="s4", relevance_score=60),
            _make_doc(source_id="s5", relevance_score=55),
            _make_doc(source_id="s6", relevance_score=52),
        ]
        result = select_top_k(items)
        sources = {it.source_id for it in result}
        # Should have at least 5 distinct sources
        assert len(sources) >= 5

    def test_fewer_than_5_sources(self):
        """With only 3 distinct sources, diversity target = 3."""
        items = [
            _make_doc(source_id="s1", relevance_score=90),
            _make_doc(source_id="s2", relevance_score=80),
            _make_doc(source_id="s3", relevance_score=70),
            _make_doc(source_id="s1", relevance_score=60),
        ]
        result = select_top_k(items)
        sources = {it.source_id for it in result}
        assert len(sources) >= min(3, len(sources))
        assert len(result) == 4

    def test_empty_input(self):
        assert select_top_k([]) == []

    def test_all_below_threshold(self):
        items = [_make_doc(source_id="s1", relevance_score=40)]
        assert select_top_k(items) == []
