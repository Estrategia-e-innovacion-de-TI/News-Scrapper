"""Source tiering classification based on run report metrics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Thresholds for prod exclusion
MIN_AVG_TEXT_LEN = 700
MAX_AVG_TEXT_LEN = 50000


def load_run_report(path: str | Path) -> dict[str, Any]:
    """Load run report JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Run report not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_metric(source: dict, key: str, default: Any = 0) -> Any:
    """Safely get metric with default."""
    return source.get(key, default)


def classify_sources(report: dict[str, Any]) -> dict[str, Any]:
    """
    Classify sources into tiers based on run report metrics.
    
    Returns:
        {
            "tier0": [source_ids...],
            "tier1": [source_ids...],
            "tier2": [source_ids...],
            "reasons": {source_id: [reasons...]}
        }
    """
    by_source = report.get("by_source", {})
    
    tier0 = []
    tier1 = []
    tier2 = []
    reasons: dict[str, list[str]] = {}
    
    for source_id, metrics in by_source.items():
        source_reasons = []
        
        discovered = _get_metric(metrics, "discovered", 0)
        fetched_ok = _get_metric(metrics, "fetched_ok", 0)
        text_ok = _get_metric(metrics, "text_ok", 0)
        errors = _get_metric(metrics, "errors", 0)
        errors_by_type = _get_metric(metrics, "errors_by_type", {})
        requires_playwright = _get_metric(metrics, "requires_playwright", False)
        avg_text_len = _get_metric(metrics, "avg_text_len", 0.0)
        
        # Tier2 conditions (problematic)
        is_tier2 = False
        
        if errors > 0:
            error_types = list(errors_by_type.keys()) if errors_by_type else ["unknown"]
            for et in error_types:
                source_reasons.append(f"tier2_errors:{et}")
            is_tier2 = True
        
        if discovered == 0:
            source_reasons.append("tier2_discovered_zero")
            is_tier2 = True
        
        if discovered > 0 and fetched_ok == 0:
            source_reasons.append("tier2_fetched_zero")
            is_tier2 = True
        
        if is_tier2:
            tier2.append(source_id)
            reasons[source_id] = source_reasons
            continue
        
        # Tier0 conditions (prod-ready)
        is_tier0 = text_ok > 0 and errors == 0
        
        # Check for risk flags that demote to Tier1
        has_risk_flags = False
        
        if requires_playwright:
            source_reasons.append("tier1_requires_playwright")
            has_risk_flags = True
        
        if avg_text_len > 0 and avg_text_len < MIN_AVG_TEXT_LEN:
            source_reasons.append("tier1_low_avg_text")
            has_risk_flags = True
        
        if avg_text_len > MAX_AVG_TEXT_LEN:
            source_reasons.append("tier1_oversized_avg_text")
            has_risk_flags = True
        
        if is_tier0 and not has_risk_flags:
            tier0.append(source_id)
            source_reasons.append("tier0_ok")
        else:
            tier1.append(source_id)
            if not source_reasons:
                source_reasons.append("tier1_default")
        
        reasons[source_id] = source_reasons
    
    return {
        "tier0": sorted(tier0),
        "tier1": sorted(tier1),
        "tier2": sorted(tier2),
        "reasons": reasons,
    }


def build_prod_set(report: dict[str, Any], mode: str = "B") -> dict[str, Any]:
    """
    Build production source set based on mode.
    
    Mode B rules:
    - Include all Tier0
    - Include Tier1 only if: text_ok > 0 AND errors == 0
    - Exclude if: avg_text_len < 700 OR avg_text_len > 50000
    - Separate into http_lane and browser_lane
    
    Returns:
        {
            "http_lane": [source_ids...],
            "browser_lane": [source_ids...],
            "excluded": [{"source_id": ..., "reason": ...}],
        }
    """
    tiers = classify_sources(report)
    by_source = report.get("by_source", {})
    
    http_lane = []
    browser_lane = []
    excluded = []
    
    # Candidates: Tier0 + Tier1
    candidates = set(tiers["tier0"]) | set(tiers["tier1"])
    
    for source_id in candidates:
        metrics = by_source.get(source_id, {})
        
        text_ok = _get_metric(metrics, "text_ok", 0)
        errors = _get_metric(metrics, "errors", 0)
        avg_text_len = _get_metric(metrics, "avg_text_len", 0.0)
        requires_playwright = _get_metric(metrics, "requires_playwright", False)
        
        # Tier1 must pass additional checks
        if source_id in tiers["tier1"]:
            if not (text_ok > 0 and errors == 0):
                excluded.append({
                    "source_id": source_id,
                    "reason": "tier1_not_qualified",
                })
                continue
        
        # Exclusion checks for all candidates
        if avg_text_len > 0 and avg_text_len < MIN_AVG_TEXT_LEN:
            excluded.append({
                "source_id": source_id,
                "reason": "thin_content",
            })
            continue
        
        if avg_text_len > MAX_AVG_TEXT_LEN:
            excluded.append({
                "source_id": source_id,
                "reason": "oversized_boilerplate_risk",
            })
            continue
        
        # Assign to lane
        if requires_playwright:
            browser_lane.append(source_id)
        else:
            http_lane.append(source_id)
    
    return {
        "http_lane": sorted(http_lane),
        "browser_lane": sorted(browser_lane),
        "excluded": excluded,
    }


def export_tiers(tiers: dict[str, Any], out_path: str | Path) -> Path:
    """Export tiers classification to JSON."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(tiers, f, indent=2, ensure_ascii=False)
    
    return out_path


def export_prod_plan(
    prod_set: dict[str, Any],
    mode: str,
    out_path: str | Path,
    notes: str = "",
) -> Path:
    """Export production plan to JSON."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    plan = {
        "prod_mode": mode,
        "http_lane": prod_set["http_lane"],
        "browser_lane": prod_set["browser_lane"],
        "excluded": prod_set["excluded"],
        "notes": notes or f"Generated with mode {mode}",
    }
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    return out_path
