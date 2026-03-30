"""Use case: Manage vigilancia subscriptions.

Handles subscribing users to topic groups and listing available topics.
"""
from __future__ import annotations

import logging
from typing import Any

from newsradar_api.domain.model.dtos import (
    SubscribeRequest,
    SubscribeResponse,
    TopicItem,
    TopicsResponse,
)

logger = logging.getLogger(__name__)


class ManageSubscriptionsUseCase:
    """Manage user subscriptions to vigilancia topic groups.

    Parameters
    ----------
    db_adapter : object
        Database adapter for subscription persistence (must expose
        ``save_subscription`` and ``get_subscriptions``).
    subscription_manager : object | None
        SubscriptionManager instance for query_group validation and
        listing available groups.
    """

    def __init__(
        self,
        db_adapter: Any,
        subscription_manager: Any = None,
    ) -> None:
        self._db = db_adapter
        self._sub_mgr = subscription_manager

    async def subscribe(self, request: SubscribeRequest) -> SubscribeResponse:
        """Subscribe a user to the specified topic groups.

        Validates requested groups against the SubscriptionManager's
        valid groups, persists via DB adapter, and returns confirmation.
        """
        # Filter to valid groups when a SubscriptionManager is available
        requested = request.query_groups
        if self._sub_mgr is not None:
            valid = self._sub_mgr.valid_groups
            if valid:
                accepted = [g for g in requested if g in valid]
                skipped = set(requested) - set(accepted)
                for g in skipped:
                    logger.warning(
                        "Subscription request for %s: unknown group '%s' — skipped",
                        request.email, g,
                    )
                requested = accepted

        # Persist via DB adapter
        await self._db.save_subscription(
            email=request.email,
            name=request.name,
            query_groups=requested,
        )

        logger.info(
            "Subscribed %s to groups: %s", request.email, requested,
        )
        return SubscribeResponse(
            status="ok",
            email=request.email,
            subscribed_groups=requested,
        )

    async def list_topics(self) -> TopicsResponse:
        """List all available topic groups for subscription.

        Reads valid groups from the SubscriptionManager (backed by
        terms_vigilancia.yaml).
        """
        if self._sub_mgr is None:
            logger.warning("No SubscriptionManager configured — returning empty topics")
            return TopicsResponse(topics=[])

        groups = self._sub_mgr.get_all_groups()
        topics = [
            TopicItem(
                group_id=g,
                display_name=g.replace("_", " ").title(),
                term_count=0,
            )
            for g in groups
        ]
        return TopicsResponse(topics=topics)
