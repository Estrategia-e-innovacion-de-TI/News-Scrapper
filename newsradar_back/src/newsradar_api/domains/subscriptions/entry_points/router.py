"""Additional canonical subscription endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domains.subscriptions.application import service
from newsradar_api.infrastructure.driven_adapters.database import get_session

router = APIRouter()


class UpdateSubscriptionRequest(BaseModel):
    active: bool | None = None
    query_groups: list[str] | None = None


@router.put("/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    request: UpdateSubscriptionRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    sub = await service.update_subscription(
        session,
        subscription_id,
        active=request.active,
        query_groups=request.query_groups,
    )
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {
        "id": str(sub.id),
        "email": sub.subscriber_email,
        "query_groups": sub.query_groups,
        "active": sub.active,
    }


@router.get("/deliveries")
async def deliveries(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = await service.list_deliveries(session)
    return [
        {
            "id": str(row.id),
            "subscription_id": str(row.subscription_id),
            "execution_id": str(row.execution_id) if row.execution_id else None,
            "status": row.status,
            "subject": row.subject,
            "delivered_at": row.delivered_at.isoformat() if row.delivered_at else None,
            "content": row.content_json or {},
        }
        for row in rows
    ]
