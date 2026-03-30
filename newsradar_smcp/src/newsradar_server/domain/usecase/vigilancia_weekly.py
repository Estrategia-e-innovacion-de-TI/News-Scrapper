"""Use case: Vigilancia weekly run.

Executes the weekly vigilancia pipeline: fetch news for all query groups,
score by relevance (0..100), select top-10 per group with source diversity,
filter by subscriber subscriptions, and send newsletters.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class VigilanciaWeeklyUseCase:
    """Orchestrates the weekly vigilancia pipeline.

    Parameters
    ----------
    subscription_manager : Any
        SubscriptionManager adapter for subscriber/group lookups.
    notification_service : Any | None
        Optional service for sending per-subscriber newsletters.
    """

    def __init__(
        self,
        subscription_manager: Any = None,
        notification_service: Any = None,
    ) -> None:
        self._sub_mgr = subscription_manager
        self._notifier = notification_service

    def execute(self, *, config: Any = None) -> dict[str, Any]:
        """Run the weekly vigilancia pipeline.

        Steps
        -----
        1. Determine query_groups to process (all valid groups).
        2. For each group, fetch & score documents (delegated to pipeline).
        3. Filter documents per subscriber based on their query_groups.
        4. Send per-subscriber newsletter (if notifier available).

        Returns
        -------
        dict
            run_id, total_groups, total_subscribers, per_subscriber results.
        """
        run_id = str(uuid.uuid4())[:8]
        logger.info("Vigilancia weekly run: run_id=%s", run_id)

        # Step 1: Determine groups to process
        has_subscribers = (
            self._sub_mgr is not None
            and getattr(self._sub_mgr, "has_subscribers_file", False)
        )

        if self._sub_mgr is not None:
            all_groups = self._sub_mgr.get_all_groups()
        else:
            all_groups = []
            logger.warning("No SubscriptionManager — no groups to process")

        # Step 2: Fetch & score documents per group
        # TODO: Wire to extract_news pipeline for each group
        docs_by_group: dict[str, list[dict[str, Any]]] = {
            group: [] for group in all_groups
        }

        total_docs = sum(len(docs) for docs in docs_by_group.values())
        logger.info(
            "Fetched %d documents across %d groups",
            total_docs, len(all_groups),
        )

        # Step 3: Filter per subscriber
        per_subscriber: dict[str, dict[str, Any]] = {}

        if has_subscribers:
            subscribers = self._sub_mgr.subscribers
            for sub in subscribers:
                sub_groups = self._sub_mgr.get_groups_for_subscriber(sub.email)
                sub_docs: list[dict[str, Any]] = []
                for grp in sub_groups:
                    sub_docs.extend(docs_by_group.get(grp, []))

                per_subscriber[sub.email] = {
                    "name": sub.name,
                    "groups": sub_groups,
                    "documents": sub_docs,
                    "document_count": len(sub_docs),
                }

                # Step 4: Send newsletter
                if self._notifier is not None and sub_docs:
                    try:
                        self._notifier.send(
                            to=sub.email,
                            name=sub.name,
                            documents=sub_docs,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to send newsletter to %s", sub.email,
                        )
        else:
            # No subscribers file — report all groups unfiltered
            logger.warning(
                "No subscribers.yaml — processing all %d groups without filtering",
                len(all_groups),
            )
            per_subscriber["_unfiltered"] = {
                "name": "all",
                "groups": all_groups,
                "documents": [
                    doc
                    for docs in docs_by_group.values()
                    for doc in docs
                ],
                "document_count": total_docs,
            }

        return {
            "run_id": run_id,
            "total_groups": len(all_groups),
            "total_subscribers": len(per_subscriber),
            "total_documents": total_docs,
            "per_subscriber": per_subscriber,
        }


# Backward-compatible function alias
def vigilancia_weekly(*, config: Any = None) -> Any:
    """Run the weekly vigilancia pipeline (function wrapper).

    Delegates to VigilanciaWeeklyUseCase.execute().
    """
    use_case = VigilanciaWeeklyUseCase()
    return use_case.execute(config=config)
