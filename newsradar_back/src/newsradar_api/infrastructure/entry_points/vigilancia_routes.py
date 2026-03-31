"""Vigilancia REST endpoints — PostgreSQL backed."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.dtos import SubscribeRequest, SubscribeResponse, TopicItem, TopicsResponse
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    request: SubscribeRequest,
    session: AsyncSession = Depends(get_session),
) -> SubscribeResponse:
    logger.info("POST /api/vigilancia/subscribe — email=%s", request.email)
    db = DBAdapter(session)
    await db.save_subscription(
        email=request.email, name=request.name, query_groups=request.query_groups,
    )
    return SubscribeResponse(
        status="ok", email=request.email, subscribed_groups=request.query_groups,
    )


@router.get("/topics")
async def list_topics(session: AsyncSession = Depends(get_session)):
    db = DBAdapter(session)
    topics = await db.get_topics()
    return [
        TopicItem(group_id=t.group_id, display_name=t.display_name, term_count=t.term_count)
        for t in topics
    ]
