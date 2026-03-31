"""Subscription REST endpoints — manage vigilancia subscriptions.

GET    /api/subscriptions/     — list active subscriptions
POST   /api/subscriptions/     — create subscription (validates query_groups)
DELETE /api/subscriptions/{id} — deactivate subscription

Validates: Requirements 22.1-22.4
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.dtos import SubscriptionDTO
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_models import Subscription

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy singleton
_subscription_manager = None


def _get_manager():
    global _subscription_manager
    if _subscription_manager is None:
        from newsradar_api.domain.usecase.subscription_manager import SubscriptionManager
        _subscription_manager = SubscriptionManager()
    return _subscription_manager


class CreateSubscriptionRequest(BaseModel):
    """Request body for POST /api/subscriptions/."""
    email: str = Field(..., description="Subscriber email")
    query_groups: list[str] = Field(..., description="Topic groups to subscribe to")


@router.get("/")
async def list_subscriptions(
    session: AsyncSession = Depends(get_session),
) -> list[SubscriptionDTO]:
    """List all active subscriptions."""
    stmt = (
        select(Subscription)
        .where(Subscription.active == True)
        .order_by(Subscription.created_at.desc())
    )
    result = await session.execute(stmt)
    subs = result.scalars().all()

    return [
        SubscriptionDTO(
            id=str(s.id),
            email=s.subscriber_email,
            query_groups=s.query_groups or [],
            active=s.active,
        )
        for s in subs
    ]


@router.post("/", status_code=201)
async def create_subscription(
    request: CreateSubscriptionRequest,
    session: AsyncSession = Depends(get_session),
) -> SubscriptionDTO:
    """Create a new subscription, validating query_groups against terms_vigilancia.yaml.

    Validates: Requirements 22.1-22.3
    """
    manager = _get_manager()

    # Validate query_groups
    accepted, rejected = manager.validate_groups(request.query_groups)
    if rejected:
        valid_groups = manager.get_all_groups()
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Grupos inexistentes: {rejected}",
                "valid_groups": valid_groups,
            },
        )

    if not accepted:
        raise HTTPException(status_code=400, detail="No valid query_groups provided")

    # Create subscription
    sub = Subscription(
        subscriber_email=request.email,
        query_groups=accepted,
        active=True,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)

    return SubscriptionDTO(
        id=str(sub.id),
        email=sub.subscriber_email,
        query_groups=sub.query_groups or [],
        active=sub.active,
    )


@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Deactivate a subscription by ID."""
    stmt = select(Subscription).where(
        Subscription.id == subscription_id,
        Subscription.active == True,
    )
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub.active = False
    await session.commit()
