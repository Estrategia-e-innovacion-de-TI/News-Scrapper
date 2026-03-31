"""Pipeline REST endpoints — run extraction and check status.

POST /api/pipeline/run  — accepts PipelineParams, runs pipeline in background, returns {run_id, status}
GET  /api/pipeline/status/{run_id} — returns RunMetrics from pipeline_runs table

Validates: Requirements 19.1-19.6
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.dtos import PipelineRunRequest, PipelineRunResponse
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_models import PipelineRun
from newsradar_api.shared_kernel.ingestion import run_local_ingestion

logger = logging.getLogger(__name__)
router = APIRouter()


class PipelineExecuteRequest(PipelineRunRequest):
    run_id: str | None = Field(None, description="Optional run id supplied by SMCP or worker orchestration")


async def _run_pipeline_background(run_id: str, params: PipelineRunRequest) -> None:
    """Execute the pipeline in background and update pipeline_runs table."""
    try:
        from newsradar_api.infrastructure.driven_adapters.database import async_session

        result = await run_local_ingestion(
            run_id=run_id,
            focus=params.focus,
            adhoc=params.adhoc,
            catalog_path=params.catalog_path,
            days=params.days,
            max_items_per_source=params.max_items_per_source,
            company=params.company,
            terms=params.terms,
            date_from=params.date_from.isoformat() if params.date_from else None,
            date_to=params.date_to.isoformat() if params.date_to else None,
            classifier_mode=params.classifier_mode,
            dry_run=params.dry_run,
            nit=params.nit,
            terms_preset=params.terms_preset,
        )

        # Update pipeline_runs record with results
        async with async_session() as session:
            stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
            result = await session.execute(stmt)
            run_record = result.scalar_one_or_none()
            if run_record:
                now = datetime.now(timezone.utc)
                run_record.finished_at = now
                run_record.duration_seconds = (
                    now - run_record.started_at
                ).total_seconds()
                run_record.params_json = {
                    **(run_record.params_json or {}),
                    "execution_id": result.get("execution_id"),
                }
                await session.commit()

        logger.info("Pipeline run %s completed", run_id)
    except Exception:
        logger.exception("Pipeline run %s failed", run_id)
        # Mark as failed in DB
        try:
            from newsradar_api.infrastructure.driven_adapters.database import async_session

            async with async_session() as session:
                stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
                result = await session.execute(stmt)
                run_record = result.scalar_one_or_none()
                if run_record:
                    run_record.finished_at = datetime.now(timezone.utc)
                    run_record.total_errors = -1  # signal failure
                    await session.commit()
        except Exception:
            logger.exception("Failed to update pipeline_runs on error")


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> PipelineRunResponse:
    """Start a pipeline run in the background.

    Creates a pipeline_runs record and launches the extraction asynchronously.
    """
    run_id = str(uuid.uuid4())[:8]
    logger.info("POST /api/pipeline/run — run_id=%s, focus=%s", run_id, request.focus)

    # Persist initial run record
    run_record = PipelineRun(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        params_json=request.model_dump(mode="json"),
    )
    session.add(run_record)
    await session.commit()

    # Launch pipeline in background
    background_tasks.add_task(_run_pipeline_background, run_id, request)

    return PipelineRunResponse(run_id=run_id, status="started")


@router.post("/execute", include_in_schema=False)
async def execute_pipeline(
    request: PipelineExecuteRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Internal synchronous execution endpoint consumed by SMCP."""
    run_id = request.run_id or str(uuid.uuid4())[:8]

    stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        session.add(
            PipelineRun(
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                params_json=request.model_dump(mode="json"),
            )
        )
        await session.commit()

    result = await run_local_ingestion(
        run_id=run_id,
        focus=request.focus,
        adhoc=request.adhoc,
        catalog_path=request.catalog_path,
        days=request.days,
        max_items_per_source=request.max_items_per_source,
        company=request.company,
        terms=request.terms,
        date_from=request.date_from.isoformat() if request.date_from else None,
        date_to=request.date_to.isoformat() if request.date_to else None,
        classifier_mode=request.classifier_mode,
        dry_run=request.dry_run,
        nit=request.nit,
        terms_preset=request.terms_preset,
    )
    return result


@router.get("/status/{run_id}")
async def get_pipeline_status(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return RunMetrics for a pipeline run from the pipeline_runs table."""
    stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
    result = await session.execute(stmt)
    run_record = result.scalar_one_or_none()

    if not run_record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Determine status
    if run_record.finished_at is None:
        status = "running"
    elif run_record.total_errors == -1:
        status = "failed"
    else:
        status = "completed"

    return {
        "run_id": run_record.run_id,
        "status": status,
        "started_at": run_record.started_at.isoformat() if run_record.started_at else None,
        "finished_at": run_record.finished_at.isoformat() if run_record.finished_at else None,
        "duration_seconds": run_record.duration_seconds,
        "total_sources": run_record.total_sources or 0,
        "total_discovered": run_record.total_discovered or 0,
        "total_fetched": run_record.total_fetched or 0,
        "total_ok": run_record.total_ok or 0,
        "total_errors": run_record.total_errors or 0,
        "total_dupes": run_record.total_dupes or 0,
        "params": run_record.params_json,
    }
