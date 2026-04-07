"""Canonical risk mapping endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domains.risk_mapping.application import service
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_models import PipelineRun
from newsradar_api.worker.jobs import run_risk_mapping_job

router = APIRouter()


class RiskmapRunRequest(BaseModel):
    catalog_path: str = Field("catalog.yaml")
    days: int = Field(7, ge=1, le=365)
    max_items_per_source: int = Field(60, ge=1, le=200)
    classifier_mode: str = Field("llm")
    window_months: int = Field(6, ge=1, le=24)
    force_snapshot: bool = Field(False)
    generate_snapshot_after_ingest: bool = Field(False)


@router.post("/run")
async def run_riskmap(
    request: RiskmapRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    session.add(
        PipelineRun(
            run_id=run_id,
            started_at=datetime.now(timezone.utc),
            params_json={**request.model_dump(mode="json"), "focus": "riesgos_news", "adhoc": False},
        )
    )
    await session.commit()
    background_tasks.add_task(run_risk_mapping_job, run_id=run_id, **request.model_dump(mode="json"))
    return {"run_id": run_id, "status": "started", "business_flow": "risk_mapping"}


@router.post("/generate")
async def generate_riskmap_snapshot(
    config: dict | None = None,
    window_months: int = Query(6, ge=1, le=24),
    force: bool = Query(False),
) -> dict:
    if config:
        window_months = int(config.get("window_months", window_months))
        force = bool(config.get("force", force))
    snapshot = await service.generate_snapshot(window_months=window_months, force=force)
    return {"snapshot_id": str(snapshot.id), "status": "completed", **(snapshot.summary_json or {})}


@router.get("/latest")
async def latest(session: AsyncSession = Depends(get_session)) -> dict:
    snapshot = await service.latest_snapshot(session)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No risk mapping snapshot found")
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
        raise HTTPException(status_code=404, detail="Risk mapping snapshot not found")
    return {"snapshot_id": str(snapshot.id), **snapshot.data_json}
