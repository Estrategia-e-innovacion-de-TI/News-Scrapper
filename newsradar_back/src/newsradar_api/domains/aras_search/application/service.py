"""Application services for ARAS/Riesgos ad-hoc audit retrieval."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.infrastructure.driven_adapters.db_models import ExportAudit, SearchAudit


async def history(session: AsyncSession) -> list[SearchAudit]:
    stmt = select(SearchAudit).order_by(SearchAudit.requested_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def get_search(session: AsyncSession, search_id: str) -> SearchAudit | None:
    stmt = select(SearchAudit).where(SearchAudit.id == search_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_export(session: AsyncSession, export_id: str) -> ExportAudit | None:
    stmt = select(ExportAudit).where(ExportAudit.id == export_id)
    return (await session.execute(stmt)).scalar_one_or_none()
