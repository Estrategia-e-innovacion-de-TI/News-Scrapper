"""Canonical tech-watch endpoints."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domains.tech_watch.application import service
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.worker.jobs import run_tech_watch_job

router = APIRouter()


class TechWatchRunRequest(BaseModel):
    catalog_path: str = Field("catalog.yaml")
    days: int = Field(7, ge=1, le=365)
    max_items_per_source: int = Field(20, ge=1, le=100)
    classifier_mode: str = Field("rules")


@router.post("/run")
async def run_tech_watch(
    request: TechWatchRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    params = request.model_dump(mode="json")
    run_id = await service.create_run(session, {**params, "focus": "vigilancia_news", "adhoc": False})
    background_tasks.add_task(run_tech_watch_job, run_id=run_id, **params)
    return {"run_id": run_id, "status": "started", "business_flow": "tech_watch"}


@router.get("/executions")
async def executions(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = await service.list_executions(session)
    return [
        {
            "id": str(row.id),
            "run_key": row.run_key,
            "status": row.status,
            "started_at": row.started_at.isoformat(),
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            "metrics": row.metrics_json or {},
        }
        for row in rows
    ]


@router.get("/documents")
async def documents(
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = await service.list_documents(session, limit=limit)
    return [
        {
            "id": str(row.id),
            "title": row.title,
            "source_id": row.source_id,
            "source_type": row.source_type,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "relevance_score": row.relevance_score,
            "category": row.category,
            "url": row.url,
        }
        for row in rows
    ]


@router.get("/topics")
async def topics() -> list[dict]:
    return service.list_topics()
