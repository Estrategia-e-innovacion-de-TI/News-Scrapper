"""Catalog REST endpoints — list and filter news sources.

GET /api/catalog/sources — list sources with optional filters

Validates: Requirements 5.3
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from newsradar_api.shared_kernel.config.paths import resolve_catalog_path

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/sources")
async def list_sources(
    focus: str | None = Query(None, description="Focus filter: aras_latam | riesgos_latam | vigilancia_global"),
    enabled: bool | None = Query(None, description="Filter by enabled state"),
) -> dict:
    """List catalog sources with optional focus and enabled filters.

    Validates: Requirement 5.3
    """
    try:
        from newsradar_api.infrastructure.connectors.catalog_loader import (
            load_sources,
            filter_sources,
        )

        catalog_path = resolve_catalog_path()

        defaults, sources = load_sources(str(catalog_path))

        # Apply filters
        include_disabled = enabled is None or not enabled
        filtered = filter_sources(
            sources,
            include_disabled=include_disabled if enabled is None else not enabled,
            focus=focus,
        )

        # If enabled filter is explicitly set, apply it
        if enabled is not None:
            filtered = [s for s in filtered if s.enabled == enabled]

        return {
            "total": len(filtered),
            "sources": [
                {
                    "source_id": s.source_id,
                    "name": s.name,
                    "enabled": s.enabled,
                    "type": s.type,
                    "base_url": s.base_url,
                    "languages": s.languages,
                    "geo": s.geo,
                    "focus": s.focus,
                    "quality_hint": s.quality_hint,
                    "requires_playwright": s.requires_playwright,
                }
                for s in filtered
            ],
        }
    except FileNotFoundError:
        return {"total": 0, "sources": [], "warning": "Catalog file not found"}
    except Exception as exc:
        logger.exception("Failed to load catalog")
        return {"total": 0, "sources": [], "error": str(exc)}
