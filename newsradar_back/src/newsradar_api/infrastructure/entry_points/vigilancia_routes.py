"""Vigilancia REST endpoints with validated subscriptions and clustering."""
from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.dtos import SubscribeRequest, SubscribeResponse, TopicItem
from newsradar_api.domain.usecase.manage_subscriptions import ManageSubscriptionsUseCase
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter

logger = logging.getLogger(__name__)
router = APIRouter()

_subscription_manager = None
_cluster_engine = None


def _get_subscription_manager():
    global _subscription_manager
    if _subscription_manager is None:
        from newsradar_api.domain.usecase.subscription_manager import SubscriptionManager

        _subscription_manager = SubscriptionManager()
    return _subscription_manager


def _get_cluster_engine():
    global _cluster_engine
    if _cluster_engine is None:
        from newsradar_api.domain.usecase.cluster_engine import ClusterEngine

        _cluster_engine = ClusterEngine()
    return _cluster_engine


def _build_use_case(session: AsyncSession) -> ManageSubscriptionsUseCase:
    return ManageSubscriptionsUseCase(
        DBAdapter(session),
        subscription_manager=_get_subscription_manager(),
        cluster_engine=_get_cluster_engine(),
    )


class VigilanciaSearchRequest(BaseModel):
    """Request body for POST /api/vigilancia/search."""

    query_groups: list[str] = Field(..., description="Topic groups to search")
    mode: Literal["papers", "repos", "patents"] = Field(
        "papers",
        description="Search provider mode",
    )
    since_days: int = Field(30, ge=1, le=3650)
    max_per_term: int = Field(20, ge=1, le=100)


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    request: SubscribeRequest,
    session: AsyncSession = Depends(get_session),
) -> SubscribeResponse:
    logger.info("POST /api/vigilancia/subscribe - email=%s", request.email)
    use_case = _build_use_case(session)
    try:
        return await use_case.subscribe(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/topics", response_model=list[TopicItem])
async def list_topics(session: AsyncSession = Depends(get_session)) -> list[TopicItem]:
    use_case = _build_use_case(session)
    response = await use_case.list_topics()
    return response.topics


@router.post("/search")
async def search_vigilancia(
    request: VigilanciaSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    logger.info(
        "POST /api/vigilancia/search - groups=%s mode=%s",
        request.query_groups,
        request.mode,
    )
    use_case = _build_use_case(session)
    try:
        return await use_case.search_results(
            query_groups=request.query_groups,
            mode=request.mode,
            since_days=request.since_days,
            max_per_term=request.max_per_term,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
