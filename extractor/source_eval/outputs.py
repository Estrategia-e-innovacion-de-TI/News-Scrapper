"""Output generation for source evaluation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def save_catalog_patch(
    evaluations: list[dict[str, Any]],
    out_dir: str | Path,
) -> Path:
    """Save catalog patch YAML from evaluations."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    patches = []
    for ev in evaluations:
        patch = {
            "source_id": ev["source_id"],
            "type": ev.get("recommended_type", "scrape"),
            "profile_required": False,
        }
        
        if ev.get("rss_urls"):
            patch["rss_urls"] = ev["rss_urls"]
            patch["type"] = "rss"
        
        if ev.get("requires_playwright"):
            patch["requires_playwright"] = True
        
        if ev.get("selectors"):
            patch["selectors"] = ev["selectors"]
        
        if ev.get("notes"):
            patch["notes"] = ev["notes"]
        
        patches.append(patch)
    
    path = out_dir / "catalog_patch.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump({"patches": patches}, f, default_flow_style=False, allow_unicode=True)
    
    return path


def save_scorecard(
    evaluations: list[dict[str, Any]],
    out_dir: str | Path,
) -> Path:
    """Save source scorecard JSON."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    path = out_dir / "source_scorecard.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(evaluations, f, indent=2, ensure_ascii=False)
    
    return path
