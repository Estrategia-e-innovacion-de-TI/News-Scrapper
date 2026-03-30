"""Tests for ClusterEngine — TF-IDF based thematic clustering."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta

# sklearn may not be installed; tests that need it are marked accordingly
sklearn_available = True
try:
    import sklearn  # noqa: F401
except ImportError:
    sklearn_available = False

from extractor.capabilities.clustering import (
    ClusterEngine,
    ClusteringOutput,
    ClusterResult,
    HypeIndicator,
    TrendEntry,
    VALID_MATURITY_STAGES,
    _get_text,
    _get_score,
    _get_published_month,
    _compute_trend_timeline,
    _compute_hype_indicators,
    _calculate_momentum,
    _determine_maturity_stage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(
    title: str = "Test Article",
    excerpt: str = "Some excerpt text",
    url: str = "https://example.com",
    mode: str = "rss",
    score: float = 50.0,
    published_at: str | None = None,
    source_id: str = "src_1",
) -> dict:
    if published_at is None:
        published_at = datetime.now().isoformat()
    return {
        "title": title,
        "excerpt": excerpt,
        "url": url,
        "mode": mode,
        "score": score,
        "published_at": published_at,
        "source_id": source_id,
    }


def _make_diverse_items(n: int, topic_prefix: str = "topic") -> list[dict]:
    """Create n items with diverse titles/excerpts for clustering."""
    base_date = datetime(2025, 1, 15)
    items = []
    topics = [
        ("cybersecurity ransomware attack malware phishing", "A major ransomware attack targeted financial institutions"),
        ("artificial intelligence machine learning deep learning neural", "New advances in deep learning models for NLP"),
        ("blockchain cryptocurrency bitcoin ethereum defi", "Cryptocurrency markets see new DeFi protocols"),
        ("cloud computing serverless kubernetes containers", "Cloud migration strategies using Kubernetes"),
        ("quantum computing qubits entanglement superposition", "Quantum computing breakthrough in error correction"),
        ("fintech digital banking payments mobile wallet", "Digital banking transformation accelerates"),
    ]
    for i in range(n):
        topic_idx = i % len(topics)
        title, excerpt = topics[topic_idx]
        # Add variation
        title = f"{title} article {i}"
        excerpt = f"{excerpt} details number {i} with extra context"
        items.append(_make_item(
            title=title,
            excerpt=excerpt,
            url=f"https://example.com/{i}",
            score=50.0 + (i % 30),
            published_at=(base_date + timedelta(days=i * 5)).isoformat(),
            source_id=f"src_{i % 4}",
        ))
    return items


# ---------------------------------------------------------------------------
# Test: Empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_list_returns_empty_output(self):
        engine = ClusterEngine()
        result = engine.cluster([])
        assert isinstance(result, ClusteringOutput)
        assert result.clusters == []
        assert result.trend_timeline == []
        assert result.hype_indicators == []


# ---------------------------------------------------------------------------
# Test: <6 items returns single "all_items" cluster
# ---------------------------------------------------------------------------

class TestFewItems:
    def test_single_item(self):
        engine = ClusterEngine()
        items = [_make_item()]
        result = engine.cluster(items)
        assert len(result.clusters) == 1
        assert result.clusters[0].cluster_id == "all_items"
        assert result.clusters[0].label == "all_items"
        assert result.clusters[0].item_count == 1

    def test_five_items_returns_single_cluster(self):
        engine = ClusterEngine()
        items = [_make_item(title=f"Article {i}") for i in range(5)]
        result = engine.cluster(items)
        assert len(result.clusters) == 1
        assert result.clusters[0].cluster_id == "all_items"
        assert result.clusters[0].item_count == 5

    def test_exactly_five_items(self):
        engine = ClusterEngine()
        items = [_make_item(title=f"Item {i}", excerpt=f"Text {i}") for i in range(5)]
        result = engine.cluster(items)
        assert len(result.clusters) == 1
        assert result.clusters[0].cluster_id == "all_items"

    def test_all_items_cluster_has_empty_keywords(self):
        engine = ClusterEngine()
        items = [_make_item() for _ in range(3)]
        result = engine.cluster(items)
        assert result.clusters[0].centroid_keywords == []


# ---------------------------------------------------------------------------
# Test: ≥6 items produces clusters (requires sklearn)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not sklearn_available, reason="scikit-learn not installed")
class TestMultipleClusters:
    def test_six_items_triggers_clustering(self):
        engine = ClusterEngine()
        items = _make_diverse_items(12)
        result = engine.cluster(items)
        assert isinstance(result, ClusteringOutput)
        assert len(result.clusters) >= 1
        # Total items across clusters should equal input
        total = sum(c.item_count for c in result.clusters)
        assert total == 12

    def test_many_items_produce_multiple_clusters(self):
        engine = ClusterEngine()
        items = _make_diverse_items(24)
        result = engine.cluster(items)
        assert len(result.clusters) >= 1
        total = sum(c.item_count for c in result.clusters)
        assert total == 24


# ---------------------------------------------------------------------------
# Test: Cluster labels have keywords
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not sklearn_available, reason="scikit-learn not installed")
class TestClusterLabels:
    def test_cluster_labels_have_keywords(self):
        engine = ClusterEngine()
        items = _make_diverse_items(18)
        result = engine.cluster(items)
        for cluster in result.clusters:
            assert isinstance(cluster.label, str)
            assert len(cluster.label) > 0
            # centroid_keywords should have at most 4 items
            assert len(cluster.centroid_keywords) <= 4

    def test_centroid_keywords_are_strings(self):
        engine = ClusterEngine()
        items = _make_diverse_items(12)
        result = engine.cluster(items)
        for cluster in result.clusters:
            for kw in cluster.centroid_keywords:
                assert isinstance(kw, str)


# ---------------------------------------------------------------------------
# Test: trend_timeline structure
# ---------------------------------------------------------------------------

class TestTrendTimeline:
    def test_trend_timeline_structure(self):
        items = [_make_item(
            title=f"Article {i}",
            score=float(50 + i),
            published_at=datetime(2025, 1 + (i % 3), 10).isoformat(),
        ) for i in range(5)]
        engine = ClusterEngine()
        result = engine.cluster(items)
        for entry in result.trend_timeline:
            assert isinstance(entry, TrendEntry)
            assert isinstance(entry.date, str)
            assert len(entry.date) == 7  # YYYY-MM
            assert isinstance(entry.topic, str)
            assert isinstance(entry.count, int)
            assert entry.count > 0
            assert isinstance(entry.avg_score, float)

    @pytest.mark.skipif(not sklearn_available, reason="scikit-learn not installed")
    def test_trend_timeline_with_clusters(self):
        engine = ClusterEngine()
        items = _make_diverse_items(12)
        result = engine.cluster(items)
        # Should have timeline entries
        assert isinstance(result.trend_timeline, list)
        for entry in result.trend_timeline:
            assert isinstance(entry.date, str)
            assert isinstance(entry.count, int)


# ---------------------------------------------------------------------------
# Test: hype_indicators validity
# ---------------------------------------------------------------------------

class TestHypeIndicators:
    def test_hype_indicators_valid_momentum(self):
        items = [_make_item(
            title=f"AI article {i}",
            published_at=datetime(2025, 1 + (i % 3), 10).isoformat(),
        ) for i in range(5)]
        engine = ClusterEngine()
        result = engine.cluster(items)
        for indicator in result.hype_indicators:
            assert isinstance(indicator, HypeIndicator)
            assert 0.0 <= indicator.momentum <= 1.0
            assert indicator.maturity_stage in VALID_MATURITY_STAGES

    @pytest.mark.skipif(not sklearn_available, reason="scikit-learn not installed")
    def test_hype_indicators_with_clusters(self):
        engine = ClusterEngine()
        items = _make_diverse_items(18)
        result = engine.cluster(items)
        for indicator in result.hype_indicators:
            assert 0.0 <= indicator.momentum <= 1.0
            assert indicator.maturity_stage in VALID_MATURITY_STAGES

    def test_hype_indicator_topics_match_clusters(self):
        items = [_make_item(published_at=datetime(2025, 1, 10).isoformat()) for _ in range(3)]
        engine = ClusterEngine()
        result = engine.cluster(items)
        cluster_labels = {c.label for c in result.clusters}
        indicator_topics = {h.topic for h in result.hype_indicators}
        assert indicator_topics == cluster_labels


# ---------------------------------------------------------------------------
# Test: Clusters with <3 items get merged (requires sklearn)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not sklearn_available, reason="scikit-learn not installed")
class TestSmallClusterMerge:
    def test_no_cluster_below_min_size(self):
        """After merging, no cluster (except unclustered) should have <3 items."""
        engine = ClusterEngine()
        items = _make_diverse_items(18)
        result = engine.cluster(items)
        for cluster in result.clusters:
            if cluster.cluster_id != "unclustered":
                assert cluster.item_count >= 3, (
                    f"Cluster {cluster.cluster_id!r} has {cluster.item_count} items (<3)"
                )


# ---------------------------------------------------------------------------
# Test: Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_get_text_title_and_excerpt(self):
        item = {"title": "Hello", "excerpt": "World"}
        assert _get_text(item) == "Hello World"

    def test_get_text_title_only(self):
        item = {"title": "Hello"}
        assert _get_text(item) == "Hello"

    def test_get_text_uses_text_fallback(self):
        item = {"title": "Hello", "text": "Fallback"}
        assert _get_text(item) == "Hello Fallback"

    def test_get_score_default(self):
        assert _get_score({}) == 0.0

    def test_get_score_from_score(self):
        assert _get_score({"score": 75}) == 75.0

    def test_get_score_from_relevance_score(self):
        assert _get_score({"relevance_score": 80}) == 80.0

    def test_get_published_month(self):
        assert _get_published_month({"published_at": "2025-03-15T10:00:00"}) == "2025-03"

    def test_get_published_month_none(self):
        assert _get_published_month({}) is None

    def test_get_published_month_invalid(self):
        assert _get_published_month({"published_at": "not-a-date"}) is None


class TestMomentumCalculation:
    def test_no_data(self):
        assert _calculate_momentum({}, []) == 0.5

    def test_single_month(self):
        assert _calculate_momentum({"2025-01": 5}, ["2025-01"]) == 0.5

    def test_increasing_trend(self):
        months = {"2025-01": 2, "2025-02": 4, "2025-03": 8}
        momentum = _calculate_momentum(months, ["2025-01", "2025-02", "2025-03"])
        assert 0.5 < momentum <= 1.0

    def test_decreasing_trend(self):
        months = {"2025-01": 8, "2025-02": 4, "2025-03": 2}
        momentum = _calculate_momentum(months, ["2025-01", "2025-02", "2025-03"])
        assert 0.0 <= momentum < 0.5

    def test_flat_trend(self):
        months = {"2025-01": 5, "2025-02": 5, "2025-03": 5}
        momentum = _calculate_momentum(months, ["2025-01", "2025-02", "2025-03"])
        assert momentum == 0.5


class TestMaturityStage:
    def test_low_count_is_innovation_trigger(self):
        assert _determine_maturity_stage(0.5, 1) == "innovation_trigger"

    def test_high_momentum_is_peak(self):
        assert _determine_maturity_stage(0.8, 5) == "peak_of_inflated_expectations"

    def test_low_momentum_is_trough(self):
        assert _determine_maturity_stage(0.1, 5) == "trough_of_disillusionment"

    def test_all_stages_are_valid(self):
        for momentum in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            for count in [1, 3, 10, 20, 50]:
                stage = _determine_maturity_stage(momentum, count)
                assert stage in VALID_MATURITY_STAGES


# ---------------------------------------------------------------------------
# Test: Capability registration
# ---------------------------------------------------------------------------

class TestCapabilityRegistration:
    def test_cluster_engine_registered(self):
        from extractor.capabilities.registry import get_capability
        cap = get_capability("cluster_engine")
        assert cap is not None
        assert cap.name == "cluster_engine"
        assert callable(cap.callable)
