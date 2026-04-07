"""Background job helpers for batch flows and analytical snapshots."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from newsradar_api.infrastructure.driven_adapters.database import async_session
from newsradar_api.infrastructure.driven_adapters.db_models import JobStatus, ReportSnapshot
from newsradar_api.shared_kernel.ingestion import run_ingestion_with_fallback
from newsradar_api.shared_kernel.snapshots.report_builder import (
    build_riskmap_payload,
    build_trendmap_payload,
    load_documents_for_flow,
    persist_snapshot,
)


async def _set_job_status(
    job_name: str,
    job_group: str,
    *,
    schedule: str | None = None,
    status: str,
    execution_id: Any | None = None,
    error: str | None = None,
) -> None:
    async with async_session() as session:
        stmt = select(JobStatus).where(JobStatus.job_name == job_name)
        row = (await session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if row is None:
            row = JobStatus(job_name=job_name, job_group=job_group, schedule=schedule)
            session.add(row)
        row.schedule = schedule
        row.last_status = status
        row.last_error = error
        row.last_execution_id = execution_id
        if status == "running":
            row.last_started_at = now
        else:
            row.last_finished_at = now
        await session.commit()


async def list_job_statuses() -> list[JobStatus]:
    async with async_session() as session:
        result = await session.execute(select(JobStatus).order_by(JobStatus.job_group, JobStatus.job_name))
        return list(result.scalars().all())


async def generate_trendmap_snapshot_job(
    window_months: int = 6,
    source_execution_id: Any | None = None,
    *,
    force: bool = False,
) -> ReportSnapshot:
    await _set_job_status(
        "trendmap_generate",
        "trend_mapping",
        schedule="on_demand",
        status="running",
        execution_id=source_execution_id,
    )
    try:
        async with async_session() as session:
            documents = await load_documents_for_flow(session, "tech_watch", window_months)
            payload = build_trendmap_payload(documents, window_months)
            snapshot = await persist_snapshot(
                session,
                "trend_mapping",
                "tech_watch",
                window_months,
                payload,
                source_execution_id=source_execution_id,
                force=force,
            )
        await _set_job_status(
            "trendmap_generate",
            "trend_mapping",
            schedule="on_demand",
            status="completed",
            execution_id=source_execution_id,
        )
        return snapshot
    except Exception as exc:
        await _set_job_status(
            "trendmap_generate",
            "trend_mapping",
            schedule="on_demand",
            status="failed",
            execution_id=source_execution_id,
            error=str(exc),
        )
        raise


async def generate_riskmap_snapshot_job(
    window_months: int = 6,
    source_execution_id: Any | None = None,
    *,
    force: bool = False,
) -> ReportSnapshot:
    await _set_job_status(
        "riskmap_generate",
        "risk_mapping",
        schedule="on_demand",
        status="running",
        execution_id=source_execution_id,
    )
    try:
        async with async_session() as session:
            documents = await load_documents_for_flow(session, "risk_mapping", window_months)
            payload = build_riskmap_payload(documents, window_months)
            snapshot = await persist_snapshot(
                session,
                "risk_mapping",
                "risk_mapping",
                window_months,
                payload,
                source_execution_id=source_execution_id,
                force=force,
            )
        await _set_job_status(
            "riskmap_generate",
            "risk_mapping",
            schedule="on_demand",
            status="completed",
            execution_id=source_execution_id,
        )
        return snapshot
    except Exception as exc:
        await _set_job_status(
            "riskmap_generate",
            "risk_mapping",
            schedule="on_demand",
            status="failed",
            execution_id=source_execution_id,
            error=str(exc),
        )
        raise


async def run_tech_watch_job(**params: Any) -> dict[str, Any]:
    run_id = params.pop("run_id")
    await _set_job_status("tech_watch_ingest", "tech_watch", schedule="weekly", status="running")
    try:
        result = await run_ingestion_with_fallback(run_id, "vigilancia_news", adhoc=False, **params)
        await _set_job_status(
            "tech_watch_ingest",
            "tech_watch",
            schedule="weekly",
            status="completed",
            execution_id=result.get("execution_id"),
        )
        return {"run_id": result.get("run_id", run_id), "execution_id": result.get("execution_id")}
    except Exception as exc:
        await _set_job_status(
            "tech_watch_ingest",
            "tech_watch",
            schedule="weekly",
            status="failed",
            error=str(exc),
        )
        raise


async def run_risk_mapping_job(**params: Any) -> dict[str, Any]:
    run_id = params.pop("run_id")
    window_months = int(params.pop("window_months", 6))
    force_snapshot = bool(params.pop("force_snapshot", False))
    generate_snapshot_after_ingest = bool(params.pop("generate_snapshot_after_ingest", False))
    await _set_job_status("risk_mapping_ingest", "risk_mapping", schedule="weekly", status="running")
    try:
        result = await run_ingestion_with_fallback(run_id, "riesgos_news", adhoc=False, **params)
        await _set_job_status(
            "risk_mapping_ingest",
            "risk_mapping",
            schedule="weekly",
            status="completed",
            execution_id=result.get("execution_id"),
        )
        response = {
            "run_id": result.get("run_id", run_id),
            "execution_id": result.get("execution_id"),
        }
        if generate_snapshot_after_ingest:
            snapshot = await generate_riskmap_snapshot_job(
                window_months=window_months,
                source_execution_id=result.get("execution_id"),
                force=force_snapshot,
            )
            response["snapshot_id"] = str(snapshot.id)
        return response
    except Exception as exc:
        await _set_job_status(
            "risk_mapping_ingest",
            "risk_mapping",
            schedule="weekly",
            status="failed",
            error=str(exc),
        )
        raise
