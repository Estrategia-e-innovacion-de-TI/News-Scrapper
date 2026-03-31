"""Health and jobs status endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from newsradar_api.infrastructure.driven_adapters.database import async_session
from newsradar_api.worker.jobs import list_job_statuses

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/jobs/status")
async def jobs_status() -> list[dict]:
    rows = await list_job_statuses()
    return [
        {
            "job_name": row.job_name,
            "job_group": row.job_group,
            "schedule": row.schedule,
            "last_status": row.last_status,
            "last_started_at": row.last_started_at.isoformat() if row.last_started_at else None,
            "last_finished_at": row.last_finished_at.isoformat() if row.last_finished_at else None,
            "last_error": row.last_error,
            "last_execution_id": str(row.last_execution_id) if row.last_execution_id else None,
        }
        for row in rows
    ]
