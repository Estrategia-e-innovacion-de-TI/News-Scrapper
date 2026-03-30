"""Capability: export_powerbi_json — PowerBIExporter for Power BI JSON output.

Generates ``powerbi_data.json`` with schema:
{meta, clusters, trend_timeline, hype_indicators, top_items}.
Validates output against POWERBI_SCHEMA before writing.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from .clustering import ClusteringOutput
from .registry import CapabilityDef, register_capability

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

POWERBI_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["meta", "clusters", "trend_timeline", "hype_indicators", "top_items"],
    "properties": {
        "meta": {
            "type": "object",
            "required": ["generated_at", "period", "modes"],
            "properties": {
                "generated_at": {"type": "string", "format": "date-time"},
                "period": {"type": "string"},
                "modes": {"type": "array", "items": {"type": "string"}},
            },
        },
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["cluster_id", "label", "centroid_keywords", "item_count", "items"],
                "properties": {
                    "cluster_id": {"type": "string"},
                    "label": {"type": "string"},
                    "centroid_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 4,
                    },
                    "item_count": {"type": "integer"},
                    "items": {"type": "array"},
                },
            },
        },
        "trend_timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["date", "topic", "count", "avg_score"],
                "properties": {
                    "date": {"type": "string"},
                    "topic": {"type": "string"},
                    "count": {"type": "integer"},
                    "avg_score": {"type": "number"},
                },
            },
        },
        "hype_indicators": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["topic", "momentum", "maturity_stage"],
                "properties": {
                    "topic": {"type": "string"},
                    "momentum": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "maturity_stage": {"type": "string"},
                },
            },
        },
        "top_items": {
            "type": "array",
            "maxItems": 20,
        },
    },
}


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------


class PowerBIExporter:
    """Export clustering results to ``powerbi_data.json``."""

    def export(
        self,
        clustering_output: ClusteringOutput,
        out_dir: str | Path,
        period: str = "",
        modes: list[str] | None = None,
    ) -> Path:
        """Export clustering results to powerbi_data.json.

        Returns path to the generated file.
        """
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        data = self._build_payload(clustering_output, period, modes)

        # Validate against schema
        errors = self._validate(data)
        if errors:
            for err in errors:
                logger.error("POWERBI_SCHEMA validation error: %s", err)
            data["_validation_errors"] = [str(e) for e in errors]

        out_path = out_dir / "powerbi_data.json"
        out_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return out_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        co: ClusteringOutput,
        period: str,
        modes: list[str] | None,
    ) -> dict[str, Any]:
        meta = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": period,
            "modes": modes or [],
        }

        clusters = [
            {
                "cluster_id": c.cluster_id,
                "label": c.label,
                "centroid_keywords": c.centroid_keywords[:4],
                "item_count": c.item_count,
                "items": c.items,
            }
            for c in co.clusters
        ]

        trend_timeline = [
            {
                "date": t.date,
                "topic": t.topic,
                "count": t.count,
                "avg_score": t.avg_score,
            }
            for t in co.trend_timeline
        ]

        hype_indicators = [
            {
                "topic": h.topic,
                "momentum": h.momentum,
                "maturity_stage": h.maturity_stage,
            }
            for h in co.hype_indicators
        ]

        top_items = self._compute_top_items(co)

        return {
            "meta": meta,
            "clusters": clusters,
            "trend_timeline": trend_timeline,
            "hype_indicators": hype_indicators,
            "top_items": top_items,
        }

    @staticmethod
    def _compute_top_items(co: ClusteringOutput) -> list[dict[str, Any]]:
        """Collect all items from all clusters, sort by score desc, take top 20."""
        all_items: list[dict[str, Any]] = []
        for cluster in co.clusters:
            for item in cluster.items:
                enriched = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "mode": item.get("mode", ""),
                    "score": item.get("score", 0) or item.get("relevance_score", 0) or 0,
                    "cluster_id": cluster.cluster_id,
                }
                all_items.append(enriched)

        all_items.sort(key=lambda x: x["score"], reverse=True)
        return all_items[:20]

    @staticmethod
    def _validate(data: dict[str, Any]) -> list[jsonschema.ValidationError]:
        """Validate *data* against POWERBI_SCHEMA. Return list of errors."""
        validator = jsonschema.Draft7Validator(POWERBI_SCHEMA)
        return list(validator.iter_errors(data))


# ---------------------------------------------------------------------------
# Module-level convenience + capability registration
# ---------------------------------------------------------------------------

_default_exporter = PowerBIExporter()


def export_powerbi_json(
    clustering_output: ClusteringOutput,
    out_dir: str | Path,
    period: str = "",
    modes: list[str] | None = None,
) -> Path:
    """Module-level convenience wrapper around :class:`PowerBIExporter`."""
    return _default_exporter.export(clustering_output, out_dir, period, modes)


register_capability(
    CapabilityDef(
        name="export_powerbi_json",
        purpose="Export clustering results to Power BI JSON format",
        inputs_schema={
            "clustering_output": "ClusteringOutput",
            "out_dir": "str | Path",
            "period": "str",
            "modes": "list[str] | None",
        },
        outputs_schema={"path": "Path to generated powerbi_data.json"},
        callable=export_powerbi_json,
        tags=["export", "powerbi", "json"],
    )
)
