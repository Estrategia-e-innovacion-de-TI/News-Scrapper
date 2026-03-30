"""Catalog loader and validator."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from .state import SourceConfig


CATALOG_DEFAULTS = {
    "timeout_seconds": 25,
    "max_retries": 2,
    "retry_backoff_seconds": 1.7,
    "rate_limit_rps": 1.0,
    "max_items_per_source": 30,
    "min_text_chars": 800,
    "allow_languages": ["es", "en", "pt"],
    "store_raw_html": False,
    "debug_store_samples_per_source": 3,
}


def load_catalog(path: str | Path) -> dict[str, Any]:
    """Load and parse catalog YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not data:
        raise ValueError("Empty catalog file")
    
    return data


def merge_defaults(catalog: dict[str, Any]) -> dict[str, Any]:
    """Merge catalog defaults with hardcoded defaults."""
    defaults = CATALOG_DEFAULTS.copy()
    if "defaults" in catalog:
        defaults.update(catalog["defaults"])
    return defaults


def parse_source(source_data: dict[str, Any], defaults: dict[str, Any]) -> SourceConfig:
    """Parse a single source entry into SourceConfig."""
    # Extract extraction config
    extraction = source_data.get("extraction", {})
    selectors = extraction.get("selectors", {})
    
    # Determine requires_playwright
    requires_playwright = (
        extraction.get("requires_playwright", False) or
        extraction.get("use_playwright", False)
    )
    
    return SourceConfig(
        source_id=source_data.get("source_id", "unknown"),
        name=source_data.get("name", ""),
        enabled=source_data.get("enabled", True),
        availability=source_data.get("availability", "unknown"),
        focus=source_data.get("focus", []),
        pipeline_class=source_data.get("pipeline_class", "news"),
        type=source_data.get("type", "scrape"),
        base_url=source_data.get("base_url", ""),
        rss_urls=source_data.get("rss_urls", []),
        listing_urls=source_data.get("listing_urls", []),
        pdf_urls=source_data.get("pdf_urls", []),
        languages=source_data.get("languages", defaults.get("allow_languages", ["es", "en"])),
        geo=source_data.get("geo", []),
        topics=source_data.get("topics", []),
        requires_playwright=requires_playwright,
        selectors=selectors,
        profile_required=source_data.get("profile_required", False),
        quality_hint=source_data.get("quality_hint", "ok"),
        notes=source_data.get("notes", ""),
        timeout_seconds=defaults.get("timeout_seconds", 25),
        max_retries=defaults.get("max_retries", 2),
        rate_limit_rps=defaults.get("rate_limit_rps", 1.0),
        min_text_chars=defaults.get("min_text_chars", 800),
    )


def load_sources(catalog_path: str | Path) -> tuple[dict[str, Any], list[SourceConfig]]:
    """Load catalog and return defaults + parsed sources."""
    catalog = load_catalog(catalog_path)
    defaults = merge_defaults(catalog)
    
    sources = []
    for source_data in catalog.get("sources", []):
        try:
            source = parse_source(source_data, defaults)
            sources.append(source)
        except Exception as e:
            print(f"Warning: Failed to parse source {source_data.get('source_id', 'unknown')}: {e}")
    
    return defaults, sources


def filter_sources(
    sources: list[SourceConfig],
    only_source: str | None = None,
    include_disabled: bool = False,
    focus: str | None = None,
) -> list[SourceConfig]:
    """Filter sources based on criteria."""
    # Map CLI focus values to catalog focus tags
    _FOCUS_MAP: dict[str, list[str]] = {
        "aras_news": ["aras_latam"],
        "riesgos_news": ["riesgos_latam"],
        "vigilancia_news": ["vigilancia_global"],
    }
    allowed_tags = _FOCUS_MAP.get(focus, []) if focus else []

    filtered = []
    
    for source in sources:
        # Skip disabled unless explicitly included
        if not source.enabled and not include_disabled:
            continue
        
        # Filter by source_id if specified
        if only_source and source.source_id != only_source:
            continue
        
        # Filter by focus if specified
        if allowed_tags and source.focus:
            if not any(tag in source.focus for tag in allowed_tags):
                continue
        
        filtered.append(source)
    
    return filtered
