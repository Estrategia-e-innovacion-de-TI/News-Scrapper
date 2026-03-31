"""Database adapter — PostgreSQL persistence via SQLAlchemy async."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.infrastructure.driven_adapters.db_models import (
    Document, Cluster, Trend, Subscription, Topic,
    EvidenceSpan, PipelineRun, TrendmapSnapshot, SubscriptionTopic,
)

logger = logging.getLogger(__name__)


class DBAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Documents ──
    async def search_documents(
        self,
        search_type: str | None = None,
        company: str | None = None,
        nit: str | None = None,
        risk_category: str | None = None,
        terms: list[str] | None = None,
        terms_preset: str | None = None,
        date_from=None,
        date_to=None,
        run_id: str | None = None,
    ) -> list[Document]:
        stmt = select(Document)
        if run_id:
            stmt = stmt.where(Document.run_id == run_id)
        if search_type:
            stmt = stmt.where(Document.query_type == search_type)
        if company:
            term = f"%{company.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Document.title).like(term),
                    func.lower(Document.text).like(term),
                    func.lower(Document.url).like(term),
                )
            )
        if nit:
            nit_term = f"%{nit.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Document.title).like(nit_term),
                    func.lower(Document.text).like(nit_term),
                )
            )
        if risk_category:
            stmt = stmt.where(
                or_(Document.category == risk_category, Document.risk_type == risk_category)
            )
        if terms:
            patterns = [f"%{term.lower()}%" for term in terms if term]
            if patterns:
                stmt = stmt.where(
                    or_(
                        *[
                            or_(
                                func.lower(Document.title).like(pattern),
                                func.lower(Document.text).like(pattern),
                            )
                            for pattern in patterns
                        ]
                    )
                )
        if date_from:
            stmt = stmt.where(Document.published_at >= date_from)
        if date_to:
            stmt = stmt.where(Document.published_at <= date_to)
        stmt = stmt.order_by(Document.published_at.desc().nullslast()).limit(100)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Clusters ──
    async def get_clusters(self) -> list[Cluster]:
        result = await self._session.execute(
            select(Cluster).order_by(Cluster.impact_score.desc())
        )
        return list(result.scalars().all())

    # ── Trends ──
    async def get_trends(self) -> list[Trend]:
        result = await self._session.execute(select(Trend))
        return list(result.scalars().all())

    # ── Subscriptions ──
    async def save_subscription(
        self,
        email: str,
        query_groups: list[str],
        name: str | None = None,
    ) -> bool:
        sub = Subscription(
            subscriber_email=email,
            subscriber_name=name,
            query_groups=query_groups,
        )
        self._session.add(sub)
        await self._session.commit()
        await self._session.refresh(sub)
        for group in query_groups:
            self._session.add(SubscriptionTopic(subscription_id=sub.id, topic_key=group))
        await self._session.commit()
        return True

    async def get_subscriptions(self, email: str | None = None) -> list[dict]:
        stmt = select(Subscription).where(Subscription.active == True)
        if email:
            stmt = stmt.where(Subscription.subscriber_email == email)
        result = await self._session.execute(stmt)
        return [
            {
                "id": str(s.id),
                "email": s.subscriber_email,
                "query_groups": s.query_groups,
                "active": s.active,
            }
            for s in result.scalars().all()
        ]

    # ── Topics ──
    async def get_topics(self) -> list[Topic]:
        result = await self._session.execute(select(Topic).order_by(Topic.display_name))
        return list(result.scalars().all())
