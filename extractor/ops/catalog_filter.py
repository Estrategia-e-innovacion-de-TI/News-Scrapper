"""Catalog filtering and production catalog generation."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from ..catalog import load_catalog


def write_filtered_catalog(
    original_catalog: dict[str, Any],
    allowed_source_ids: list[str],
    out_path: str | Path,
) -> Path:
    """
    Write a filtered catalog containing only allowed sources.
    
    Preserves original structure, only filters sources list.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    allowed_set = set(allowed_source_ids)
    
    # Deep copy to avoid modifying original
    filtered = {}
    
    # Copy all top-level keys except sources
    for key, value in original_catalog.items():
        if key != "sources":
            filtered[key] = value
    
    # Filter sources
    original_sources = original_catalog.get("sources", [])
    filtered_sources = [
        source for source in original_sources
        if source.get("source_id") in allowed_set
    ]
    
    filtered["sources"] = filtered_sources
    
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(filtered, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return out_path


def write_catalog_prod(
    original_catalog: dict[str, Any],
    prod_set: dict[str, Any],
    out_path: str | Path,
) -> Path:
    """
    Write production catalog with only allowed sources (Tier0 + qualified Tier1).
    
    Args:
        original_catalog: Full catalog dict
        prod_set: Result from build_prod_set() with http_lane and browser_lane
        out_path: Output path for catalog_prod.yaml
    """
    # Combine both lanes for allowed sources
    allowed = set(prod_set["http_lane"]) | set(prod_set["browser_lane"])
    
    return write_filtered_catalog(original_catalog, list(allowed), out_path)


def write_tier_catalogs(
    catalog_path: str | Path,
    tiers: dict[str, Any],
    out_dir: str | Path,
) -> dict[str, Path]:
    """
    Write separate catalog files for each tier.
    
    Returns dict mapping tier name to output path.
    """
    catalog = load_catalog(catalog_path)
    out_dir = Path(out_dir)
    
    outputs = {}
    
    for tier_name in ["tier0", "tier1", "tier2"]:
        source_ids = tiers.get(tier_name, [])
        out_path = out_dir / f"catalog_{tier_name}.yaml"
        write_filtered_catalog(catalog, source_ids, out_path)
        outputs[tier_name] = out_path
    
    return outputs
