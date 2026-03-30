"""Unit tests for PowerBIExporter capability."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from extractor.capabilities.clustering import (
    ClusteringOutput,
    ClusterResult,
    HypeIndicator,
    TrendEntry,
)
from extractor.capabilities.powerbi_export import (
    POWERBI_SCHEMA,
    PowerBIExporter,
    export_powerbi_json,
)
from extractor.capabilities.registry import get_capability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(
    *,
    title: str = "Item title",
    url: str = "https://example.com/1",
    mode: str = "news",
    score: float = 50.0,
    published_at: str = "2025-01-15",
) -> dict:
    return {
        "title": title,
        "url": url,
        "mode": mode,
        "score": score,
        "published_at": published_at,
    }


def _make_cluster(
    cluster_id: str = "c1",
    label: str = "topic A",
    keywords: list[str] | None = None,
    items: list[dict] | None = None,
) -> ClusterResult:
    items = items or [_make_item()]
    return ClusterResult(
        cluster_id=cluster_id,
        label=label,
        centroid_keywords=keywords or ["kw1", "kw2", "kw3", "kw4"],
        item_count=len(items),
        items=items,
    )


def _make_clustering_output(
    n_clusters: int = 2,
    items_per_cluster: int = 3,
) -> ClusteringOutput:
    clusters = []
    for i in range(n_clusters):
        items = [
            _make_item(
                title=f"Item {i}-{j}",
                url=f"https://example.com/{i}/{j}",
                score=float(100 - i * 10 - j),
            )
            for j in range(items_per_cluster)
        ]
        clusters.append(
            _make_cluster(
                cluster_id=f"c{i}",
                label=f"topic {i}",
                items=items,
            )
        )
    return ClusteringOutput(
        clusters=clusters,
        trend_timeline=[
            TrendEntry(date="2025-01", topic="topic 0", count=3, avg_score=75.0),
            TrendEntry(date="2025-02", topic="topic 1", count=2, avg_score=60.0),
        ],
        hype_indicators=[
            HypeIndicator(topic="topic 0", momentum=0.8, maturity_stage="innovation_trigger"),
            HypeIndicator(topic="topic 1", momentum=0.3, maturity_stage="slope_of_enlightenment"),
        ],
    )


def _empty_clustering_output() -> ClusteringOutput:
    return ClusteringOutput(
        clusters=[],
        trend_timeline=[],
        hype_indicators=[],
    )


# ---------------------------------------------------------------------------
# Test: generates valid JSON file
# ---------------------------------------------------------------------------

class TestGeneratesValidJSON:
    def test_file_created(self, tmp_path: Path):
        co = _make_clustering_output()
        path = export_powerbi_json(co, tmp_path, period="2025-Q1", modes=["news"])
        assert path.exists()
        assert path.name == "powerbi_data.json"

    def test_file_is_valid_json(self, tmp_path: Path):
        co = _make_clustering_output()
        path = export_powerbi_json(co, tmp_path, period="2025-Q1", modes=["news"])
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_all_top_level_keys_present(self, tmp_path: Path):
        co = _make_clustering_output()
        path = export_powerbi_json(co, tmp_path, period="2025-Q1", modes=["news"])
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("meta", "clusters", "trend_timeline", "hype_indicators", "top_items"):
            assert key in data


# ---------------------------------------------------------------------------
# Test: JSON conforms to POWERBI_SCHEMA
# ---------------------------------------------------------------------------

class TestSchemaConformance:
    def test_valid_output_passes_schema(self, tmp_path: Path):
        co = _make_clustering_output()
        path = export_powerbi_json(co, tmp_path, period="2025-Q1", modes=["news"])
        data = json.loads(path.read_text(encoding="utf-8"))
        # Should not raise
        jsonschema.validate(data, POWERBI_SCHEMA)

    def test_meta_fields(self, tmp_path: Path):
        co = _make_clustering_output()
        path = export_powerbi_json(co, tmp_path, period="2025-Q4", modes=["news", "papers"])
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data["meta"]
        assert "generated_at" in meta
        assert meta["period"] == "2025-Q4"
        assert meta["modes"] == ["news", "papers"]

    def test_cluster_structure(self, tmp_path: Path):
        co = _make_clustering_output()
        path = export_powerbi_json(co, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        for cluster in data["clusters"]:
            assert "cluster_id" in cluster
            assert "label" in cluster
            assert "centroid_keywords" in cluster
            assert len(cluster["centroid_keywords"]) <= 4
            assert "item_count" in cluster
            assert "items" in cluster


# ---------------------------------------------------------------------------
# Test: top_items at most 20, sorted by score descending
# ---------------------------------------------------------------------------

class TestTopItems:
    def test_top_items_max_20(self, tmp_path: Path):
        # Create enough items to exceed 20
        co = _make_clustering_output(n_clusters=5, items_per_cluster=10)
        path = export_powerbi_json(co, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["top_items"]) <= 20

    def test_top_items_sorted_by_score_desc(self, tmp_path: Path):
        co = _make_clustering_output(n_clusters=3, items_per_cluster=5)
        path = export_powerbi_json(co, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        scores = [item["score"] for item in data["top_items"]]
        assert scores == sorted(scores, reverse=True)

    def test_top_items_have_cluster_id(self, tmp_path: Path):
        co = _make_clustering_output()
        path = export_powerbi_json(co, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data["top_items"]:
            assert "cluster_id" in item
            assert "title" in item
            assert "url" in item
            assert "mode" in item
            assert "score" in item


# ---------------------------------------------------------------------------
# Test: round-trip JSON
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_json_round_trip(self, tmp_path: Path):
        co = _make_clustering_output()
        path = export_powerbi_json(co, tmp_path, period="2025-Q1", modes=["news"])
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert json.loads(json.dumps(data)) == data


# ---------------------------------------------------------------------------
# Test: validation failure adds _validation_errors key
# ---------------------------------------------------------------------------

class TestValidationFailure:
    def test_invalid_data_gets_errors_key(self, tmp_path: Path):
        exporter = PowerBIExporter()
        # Create output with invalid momentum (>1.0) to trigger validation error
        co = ClusteringOutput(
            clusters=[],
            trend_timeline=[],
            hype_indicators=[
                HypeIndicator(topic="bad", momentum=1.5, maturity_stage="innovation_trigger"),
            ],
        )
        path = exporter.export(co, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "_validation_errors" in data
        assert len(data["_validation_errors"]) > 0


# ---------------------------------------------------------------------------
# Test: empty clustering output generates valid JSON
# ---------------------------------------------------------------------------

class TestEmptyOutput:
    def test_empty_clustering_output(self, tmp_path: Path):
        co = _empty_clustering_output()
        path = export_powerbi_json(co, tmp_path, period="2025-Q1", modes=["news"])
        data = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(data, POWERBI_SCHEMA)
        assert data["clusters"] == []
        assert data["trend_timeline"] == []
        assert data["hype_indicators"] == []
        assert data["top_items"] == []


# ---------------------------------------------------------------------------
# Test: output directory is created if missing
# ---------------------------------------------------------------------------

class TestDirectoryCreation:
    def test_creates_nested_dirs(self, tmp_path: Path):
        nested = tmp_path / "a" / "b" / "c"
        assert not nested.exists()
        co = _make_clustering_output()
        path = export_powerbi_json(co, nested)
        assert path.exists()
        assert nested.exists()


# ---------------------------------------------------------------------------
# Test: capability is registered
# ---------------------------------------------------------------------------

class TestCapabilityRegistration:
    def test_export_powerbi_json_registered(self):
        cap = get_capability("export_powerbi_json")
        assert cap is not None
        assert cap.name == "export_powerbi_json"
        assert cap.callable is export_powerbi_json
