"""Catalog loader and validator.

Ported from ``news_radar_mvp/extractor/catalog.py``.
Loads the YAML catalog, merges defaults, parses sources into
:class:`SourceConfig` objects, and filters them by focus / source_id.

Validates: Requirements 5.1-5.4
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from newsradar_api.domain.model.pipeline_models import SourceConfig

logger = logging.getLogger(__name__)

__all__ = [
    "CATALOG_DEFAULTS",
    "load_catalog",
    "merge_defaults",
    "parse_source",
    "load_sources",
    "filter_sources",
]

# Hardcoded defaults matching the original MVP.
CATALOG_DEFAULTS: dict[str, Any] = {
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

# Map CLI focus values → catalog focus tags (Req 5.3).
_FOCUS_MAP: dict[str, list[str]] = {
    "aras_news": ["aras_latam"],
    "riesgos_news": ["riesgos_latam"],
    "vigilancia_news": ["vigilancia_global"],
}


# ── Public API ────────────────────────────────────────────────────────


def load_catalog(path: str | Path) -> dict[str, Any]:
    """Load and parse a catalog YAML file.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the file is empty or unparseable.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not data:
        raise ValueError("Empty catalog file")

    return data


def merge_defaults(catalog: dict[str, Any]) -> dict[str, Any]:
    """Merge file-level defaults with hardcoded defaults.

    Hardcoded values act as the base; keys present in the catalog's
    ``defaults`` section override them.
    """
    defaults = CATALOG_DEFAULTS.copy()
    if "defaults" in catalog:
        defaults.update(catalog["defaults"])
    return defaults


def parse_source(
    source_data: dict[str, Any],
    defaults: dict[str, Any],
) -> SourceConfig:
    """Parse a single source entry into a :class:`SourceConfig`.

    Parameters
    ----------
    source_data:
        Raw dict from the ``sources`` list in the catalog YAML.
    defaults:
        Merged defaults (hardcoded + file-level).
    """
    extraction = source_data.get("extraction", {})
    selectors = extraction.get("selectors", {})

    requires_playwright = (
        extraction.get("requires_playwright", False)
        or extraction.get("use_playwright", False)
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
        languages=source_data.get(
            "languages",
            defaults.get("allow_languages", ["es", "en"]),
        ),
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


def load_sources(
    catalog_path: str | Path,
) -> tuple[dict[str, Any], list[SourceConfig]]:
    """Load catalog and return *(defaults, parsed_sources)*.

    Sources that fail to parse emit a warning and are skipped (Req 5.4).
    """
    catalog = load_catalog(catalog_path)
    defaults = merge_defaults(catalog)

    sources: list[SourceConfig] = []
    for source_data in catalog.get("sources", []):
        try:
            sources.append(parse_source(source_data, defaults))
        except Exception as exc:
            sid = source_data.get("source_id", "unknown")
            logger.warning("Failed to parse source %s: %s", sid, exc)

    return defaults, sources


def filter_sources(
    sources: list[SourceConfig],
    only_source: str | None = None,
    include_disabled: bool = False,
    focus: str | None = None,
) -> list[SourceConfig]:
    """Filter sources by *only_source*, enabled state, and *focus*.

    The *focus* parameter is a CLI value (e.g. ``"aras_news"``) that is
    mapped to catalog tags via :data:`_FOCUS_MAP`.
    """
    allowed_tags = _FOCUS_MAP.get(focus, []) if focus else []

    filtered: list[SourceConfig] = []
    for source in sources:
        # Skip disabled unless explicitly included.
        if not source.enabled and not include_disabled:
            continue

        # Filter by specific source_id.
        if only_source and source.source_id != only_source:
            continue

        # Filter by focus tags.
        if allowed_tags and source.focus:
            if not any(tag in source.focus for tag in allowed_tags):
                continue

        filtered.append(source)

    return filtered
