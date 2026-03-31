"""Application services for subscriptions and deliveries."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.infrastructure.driven_adapters.db_models import Subscription, SubscriptionDelivery


async def list_deliveries(session: AsyncSession) -> list[SubscriptionDelivery]:
    stmt = select(SubscriptionDelivery).order_by(SubscriptionDelivery.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def update_subscription(
    session: AsyncSession,
    subscription_id: str,
    *,
    active: bool | None = None,
    query_groups: list[str] | None = None,
) -> Subscription | None:
    stmt = select(Subscription).where(Subscription.id == subscription_id)
    sub = (await session.execute(stmt)).scalar_one_or_none()
    if sub is None:
        return None
    if active is not None:
        sub.active = active
    if query_groups is not None:
        sub.query_groups = query_groups
    await session.commit()
    await session.refresh(sub)
    return sub
