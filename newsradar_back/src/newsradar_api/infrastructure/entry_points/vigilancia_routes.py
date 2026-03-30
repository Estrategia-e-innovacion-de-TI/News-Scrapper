"""Vigilancia REST endpoints.

POST /api/vigilancia/subscribe — Subscribe to topic groups.
GET  /api/vigilancia/topics    — List available topic groups.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from newsradar_api.domain.model.dtos import (
    SubscribeRequest,
    SubscribeResponse,
    TopicsResponse,
)
from newsradar_api.domain.usecase.manage_subscriptions import (
    ManageSubscriptionsUseCase,
)
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Dependency injection ──────────────────────────────────────────────

_use_case: ManageSubscriptionsUseCase | None = None


def get_use_case() -> ManageSubscriptionsUseCase:
    """Return the shared ManageSubscriptionsUseCase instance."""
    global _use_case
    if _use_case is None:
        # Lazy-init with default adapters.
        # SubscriptionManager is optional — if extractor package is
        # available we wire it; otherwise topics come from DB only.
        sub_mgr = None
        try:
            from newsradar_api.infrastructure.driven_adapters.subscription_bridge import (
                get_subscription_manager,
            )
            sub_mgr = get_subscription_manager()
        except Exception:
            logger.debug("SubscriptionManager bridge not available — topics from DB only")

        _use_case = ManageSubscriptionsUseCase(
            db_adapter=DBAdapter(),
            subscription_manager=sub_mgr,
        )
    return _use_case


# ── Routes ────────────────────────────────────────────────────────────


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    request: SubscribeRequest,
    uc: ManageSubscriptionsUseCase = Depends(get_use_case),
) -> SubscribeResponse:
    """Subscribe a user to vigilancia topic groups."""
    logger.info(
        "POST /api/vigilancia/subscribe — email=%s, groups=%s",
        request.email, request.query_groups,
    )
    return await uc.subscribe(request)


@router.get("/topics", response_model=TopicsResponse)
async def list_topics(
    uc: ManageSubscriptionsUseCase = Depends(get_use_case),
) -> TopicsResponse:
    """List all available topic groups for subscription."""
    logger.info("GET /api/vigilancia/topics")
    return await uc.list_topics()
