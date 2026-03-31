"""Application services for tech-watch runs and queries."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.usecase.subscription_manager import SubscriptionManager
from newsradar_api.infrastructure.driven_adapters.db_models import Document, Execution, PipelineRun
from newsradar_api.worker.jobs import run_tech_watch_job


async def create_run(session: AsyncSession, params: dict) -> str:
    run_id = str(uuid.uuid4())[:8]
    session.add(
        PipelineRun(
            run_id=run_id,
            started_at=datetime.now(timezone.utc),
            params_json=params,
        )
    )
    await session.commit()
    return run_id


async def execute_run(session: AsyncSession, params: dict) -> str:
    run_id = await create_run(session, params)
    await run_tech_watch_job(run_id=run_id, **params)
    return run_id


async def list_executions(session: AsyncSession) -> list[Execution]:
    stmt = (
        select(Execution)
        .where(Execution.business_flow == "tech_watch")
        .order_by(Execution.started_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_documents(session: AsyncSession, limit: int = 100) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.business_flow == "tech_watch")
        .order_by(Document.published_at.desc().nullslast(), Document.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


def list_topics() -> list[dict]:
    manager = SubscriptionManager()
    groups = manager.get_all_groups()
    terms = manager.get_terms_for_groups(groups)
    return [
        {
            "group_id": group,
            "display_name": group.replace("_", " ").title(),
            "term_count": len(terms.get(group, [])),
        }
        for group in groups
    ]
