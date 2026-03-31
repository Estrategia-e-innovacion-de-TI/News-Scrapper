"""Trend mapping endpoints with canonical snapshot persistence."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domains.trend_mapping.application import service as trendmap_service
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter
from newsradar_api.infrastructure.driven_adapters.db_models import TrendmapSnapshot

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_trendmap(
    snapshot_id: str | None = Query(None, description="Specific snapshot ID"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return the latest trend mapping snapshot in the legacy payload shape."""
    if snapshot_id:
        snapshot = await trendmap_service.get_snapshot(session, snapshot_id)
    else:
        snapshot = await trendmap_service.latest_snapshot(session)

    if not snapshot:
        stmt = select(TrendmapSnapshot).order_by(TrendmapSnapshot.generated_at.desc()).limit(1)
        snapshot = (await session.execute(stmt)).scalar_one_or_none()
        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail="No trendmap snapshot found. Generate one with POST /api/trendmap/generate",
            )

    payload = snapshot.data_json or {}
    return {
        "snapshot_id": str(snapshot.id),
        "generated_at": snapshot.generated_at.isoformat() if snapshot.generated_at else None,
        **payload,
    }


@router.post("/generate")
async def generate_trendmap(
    config: dict | None = None,
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Generate a trend mapping snapshot from persisted tech-watch history."""
    window_months = int((config or {}).get("window_months", 6))
    force = bool((config or {}).get("force", False))
    try:
        snapshot = await trendmap_service.generate_snapshot(window_months=window_months, force=force)
    except Exception as exc:
        logger.exception("Trendmap generation failed")
        raise HTTPException(status_code=500, detail=f"Trendmap generation failed: {exc}") from exc

    payload = snapshot.data_json or {}
    return {
        "snapshot_id": str(snapshot.id),
        "status": "completed",
        "total_clusters": len(payload.get("clusters", [])),
        "total_articles": len(payload.get("articles", [])),
    }


@router.get("/clusters")
async def get_clusters(session: AsyncSession = Depends(get_session)) -> dict:
    """Legacy endpoint: returns clusters from the latest snapshot-backed table."""
    db = DBAdapter(session)
    clusters = await db.get_clusters()
    return {
        "clusters": [
            {
                "cluster_id": c.cluster_id,
                "label": c.label,
                "category": c.category,
                "summary": c.summary,
                "keywords": c.keywords or [],
                "item_count": c.item_count,
                "impact_score": c.impact_score,
                "horizon_score": c.horizon_score,
                "hull_polygon": c.hull_polygon or [],
                "avg_score": c.avg_score,
                "x_embed": c.x_embed,
                "y_embed": c.y_embed,
                "relevance": c.relevance,
            }
            for c in clusters
        ]
    }


@router.get("/trends")
async def get_trends(session: AsyncSession = Depends(get_session)) -> dict:
    """Legacy endpoint kept for compatibility."""
    db = DBAdapter(session)
    trends = await db.get_trends()
    return {
        "trends": [
            {
                "trend": t.trend,
                "category": t.category,
                "direction": t.direction,
                "momentum": t.momentum,
                "maturity_stage": t.maturity_stage,
                "description": t.description,
                "impact_on_finance": t.impact_on_finance,
            }
            for t in trends
        ]
    }


@router.get("/meta")
async def get_meta(session: AsyncSession = Depends(get_session)) -> dict:
    """Legacy metadata endpoint."""
    db = DBAdapter(session)
    clusters = await db.get_clusters()
    trends = await db.get_trends()
    snapshot = await trendmap_service.latest_snapshot(session)
    last_updated = "N/A"
    if snapshot and snapshot.generated_at:
        last_updated = snapshot.generated_at.strftime("%Y-%m-%d")
    return {
        "last_updated": last_updated,
        "total_clusters": len(clusters),
        "total_trends": len(trends),
    }
