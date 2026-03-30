"""Filters for search candidates based on YAML config."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .models import SearchCandidate


def apply_filters(
    candidates: list[SearchCandidate],
    filters: dict[str, Any],
    mode: str,
) -> list[SearchCandidate]:
    """Apply mode-specific filters to candidates."""
    if mode == "repos":
        return _filter_repos(candidates, filters)
    elif mode == "papers":
        return _filter_papers(candidates, filters)
    elif mode == "patents":
        return _filter_patents(candidates, filters)
    return candidates


def _filter_repos(
    candidates: list[SearchCandidate],
    filters: dict[str, Any],
) -> list[SearchCandidate]:
    """Filter repo candidates."""
    min_stars = filters.get("min_stars", 0)
    updated_within_days = filters.get("updated_within_days", 0)
    
    result = []
    for c in candidates:
        stars = c.extra.get("stars", 0)
        if min_stars and stars < min_stars:
            continue
        
        if updated_within_days and c.extra.get("updated_at"):
            try:
                updated = datetime.fromisoformat(c.extra["updated_at"].replace("Z", "+00:00"))
                cutoff = datetime.now(updated.tzinfo) - timedelta(days=updated_within_days)
                if updated < cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        
        result.append(c)
    return result


def _filter_papers(
    candidates: list[SearchCandidate],
    filters: dict[str, Any],
) -> list[SearchCandidate]:
    """Filter paper candidates."""
    require_any = filters.get("require_keywords_any", [])
    
    if not require_any:
        return candidates
    
    result = []
    require_lower = [k.lower() for k in require_any]
    
    for c in candidates:
        text = f"{c.title} {c.snippet}".lower()
        if any(kw in text for kw in require_lower):
            result.append(c)
    
    return result


def _filter_patents(
    candidates: list[SearchCandidate],
    filters: dict[str, Any],
) -> list[SearchCandidate]:
    """Filter patent candidates."""
    # date_window_months and preferred_assignees
    return candidates  # Basic pass-through for MVP
