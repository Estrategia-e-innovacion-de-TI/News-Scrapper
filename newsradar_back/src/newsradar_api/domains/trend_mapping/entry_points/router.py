"""Canonical trend mapping endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domains.trend_mapping.application import service
from newsradar_api.infrastructure.driven_adapters.database import get_session

router = APIRouter()


@router.get("/latest")
async def latest(session: AsyncSession = Depends(get_session)) -> dict:
    snapshot = await service.latest_snapshot(session)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No trend mapping snapshot found")
    return {"snapshot_id": str(snapshot.id), **snapshot.data_json}


@router.get("/history")
async def history(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = await service.snapshot_history(session)
    return [
        {
            "snapshot_id": str(row.id),
            "generated_at": row.generated_at.isoformat(),
            "window_months": row.window_months,
            "summary": row.summary_json or {},
        }
        for row in rows
    ]


@router.get("/{snapshot_id}")
async def get_snapshot(snapshot_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    snapshot = await service.get_snapshot(session, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Trend mapping snapshot not found")
    return {"snapshot_id": str(snapshot.id), **snapshot.data_json}
