"""Application services for trend mapping snapshots."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.infrastructure.driven_adapters.db_models import ReportSnapshot
from newsradar_api.worker.jobs import generate_trendmap_snapshot_job


async def latest_snapshot(session: AsyncSession) -> ReportSnapshot | None:
    stmt = (
        select(ReportSnapshot)
        .where(ReportSnapshot.report_type == "trend_mapping")
        .order_by(ReportSnapshot.generated_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def snapshot_history(session: AsyncSession) -> list[ReportSnapshot]:
    stmt = (
        select(ReportSnapshot)
        .where(ReportSnapshot.report_type == "trend_mapping")
        .order_by(ReportSnapshot.generated_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_snapshot(session: AsyncSession, snapshot_id: str) -> ReportSnapshot | None:
    stmt = select(ReportSnapshot).where(
        ReportSnapshot.report_type == "trend_mapping",
        ReportSnapshot.id == snapshot_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def generate_snapshot(window_months: int = 6, *, force: bool = False) -> ReportSnapshot:
    return await generate_trendmap_snapshot_job(window_months=window_months, force=force)
