"""Trendmap REST endpoints — PostgreSQL backed.

Enhanced with:
- GET /api/trendmap/ — returns full TrendmapResponse from trendmap_snapshots
- POST /api/trendmap/generate — runs TrendmapPipeline and saves snapshot
- Legacy endpoints /clusters, /trends, /meta maintained for compatibility

Validates: Requirements 14.8, 15.1
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.trendmap_models import TrendmapResponse
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter
from newsradar_api.infrastructure.driven_adapters.db_models import TrendmapSnapshot

logger = logging.getLogger(__name__)
router = APIRouter()


# ── New endpoints ─────────────────────────────────────────────────────


@router.get("/")
async def get_trendmap(
    snapshot_id: str | None = Query(None, description="Specific snapshot ID"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return full TrendmapResponse from the latest (or specified) snapshot.

    Validates: Requirements 14.8, 15.1
    """
    if snapshot_id:
        stmt = select(TrendmapSnapshot).where(
            TrendmapSnapshot.id == snapshot_id
        )
    else:
        stmt = (
            select(TrendmapSnapshot)
            .order_by(TrendmapSnapshot.generated_at.desc())
            .limit(1)
        )

    result = await session.execute(stmt)
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail="No trendmap snapshot found. Generate one with POST /api/trendmap/generate",
        )

    data = snapshot.data_json or {}
    return {
        "snapshot_id": str(snapshot.id),
        "generated_at": snapshot.generated_at.isoformat() if snapshot.generated_at else None,
        **data,
    }


@router.post("/generate")
async def generate_trendmap(
    config: dict | None = None,
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Execute TrendmapPipeline and save the resulting snapshot.

    Validates: Requirements 14.1-14.8
    """
    snapshot_id = str(uuid.uuid4())
    logger.info("POST /api/trendmap/generate — snapshot_id=%s", snapshot_id)

    try:
        from newsradar_api.infrastructure.pipeline.trendmap_pipeline import TrendmapPipeline

        pipeline = TrendmapPipeline()
        trendmap_data = pipeline.generate(config=config or {})

        # Save snapshot to DB
        snapshot = TrendmapSnapshot(
            id=snapshot_id,
            generated_at=datetime.now(timezone.utc),
            data_json=trendmap_data.model_dump(mode="json"),
            meta_json=trendmap_data.meta.model_dump(mode="json") if trendmap_data.meta else None,
        )
        session.add(snapshot)
        await session.commit()

        return {
            "snapshot_id": snapshot_id,
            "status": "completed",
            "total_clusters": len(trendmap_data.clusters),
            "total_articles": len(trendmap_data.articles),
        }
    except Exception as exc:
        logger.exception("Trendmap generation failed")
        raise HTTPException(status_code=500, detail=f"Trendmap generation failed: {exc}")


# ── Legacy compatibility endpoints ────────────────────────────────────


@router.get("/clusters")
async def get_clusters(session: AsyncSession = Depends(get_session)):
    """Legacy endpoint — returns clusters from DB clusters table."""
    db = DBAdapter(session)
    clusters = await db.get_clusters()
    return {"clusters": [
        {
            "cluster_id": c.cluster_id, "label": c.label, "category": c.category,
            "summary": c.summary, "keywords": c.keywords or [],
            "item_count": c.item_count, "impact_score": c.impact_score,
            "horizon_score": c.horizon_score, "hull_polygon": c.hull_polygon or [],
            "avg_score": c.avg_score, "x_embed": c.x_embed, "y_embed": c.y_embed,
            "relevance": c.relevance,
        }
        for c in clusters
    ]}


@router.get("/trends")
async def get_trends(session: AsyncSession = Depends(get_session)):
    """Legacy endpoint — returns trends from DB trends table."""
    db = DBAdapter(session)
    trends = await db.get_trends()
    return {"trends": [
        {
            "trend": t.trend, "category": t.category, "direction": t.direction,
            "momentum": t.momentum, "maturity_stage": t.maturity_stage,
            "description": t.description, "impact_on_finance": t.impact_on_finance,
        }
        for t in trends
    ]}


@router.get("/meta")
async def get_meta(session: AsyncSession = Depends(get_session)):
    """Legacy endpoint — returns basic metadata."""
    db = DBAdapter(session)
    clusters = await db.get_clusters()
    trends = await db.get_trends()

    # Also check for latest snapshot
    stmt = (
        select(TrendmapSnapshot)
        .order_by(TrendmapSnapshot.generated_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    snapshot = result.scalar_one_or_none()

    last_updated = "N/A"
    if snapshot and snapshot.generated_at:
        last_updated = snapshot.generated_at.strftime("%Y-%m-%d")

    return {
        "last_updated": last_updated,
        "total_clusters": len(clusters),
        "total_trends": len(trends),
    }
