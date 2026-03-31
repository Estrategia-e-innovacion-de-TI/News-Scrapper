"""Use case: Manage vigilancia subscriptions and grouped monitoring results."""
from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Awaitable, Callable

from newsradar_api.domain.model.dtos import (
    SubscribeRequest,
    SubscribeResponse,
    TopicItem,
    TopicsResponse,
)

logger = logging.getLogger(__name__)

SearchRunner = Callable[..., Awaitable[tuple[list[Any], Any]]]


def _as_mapping(value: Any) -> dict[str, Any]:
    """Convert Pydantic models, dataclasses, or plain objects to dicts."""
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    return dict(vars(value))


class ManageSubscriptionsUseCase:
    """Manage user subscriptions and vigilancia result clustering."""

    def __init__(
        self,
        db_adapter: Any,
        subscription_manager: Any = None,
        cluster_engine: Any = None,
        search_runner: SearchRunner | None = None,
    ) -> None:
        self._db = db_adapter
        self._sub_mgr = subscription_manager
        self._cluster_engine = cluster_engine
        self._search_runner = search_runner

    async def subscribe(self, request: SubscribeRequest) -> SubscribeResponse:
        """Subscribe a user after validating the requested topic groups."""
        requested = self._validate_requested_groups(request.query_groups)

        await self._db.save_subscription(
            email=request.email,
            name=request.name,
            query_groups=requested,
        )

        logger.info("Subscribed %s to groups: %s", request.email, requested)
        return SubscribeResponse(
            status="ok",
            email=request.email,
            subscribed_groups=requested,
        )

    async def list_topics(self) -> TopicsResponse:
        """List all available topic groups for subscription."""
        if self._sub_mgr is not None:
            groups = self._sub_mgr.get_all_groups()
            terms_by_group = self._sub_mgr.get_terms_for_groups(groups)
            return TopicsResponse(
                topics=[
                    TopicItem(
                        group_id=group_id,
                        display_name=group_id.replace("_", " ").title(),
                        term_count=len(terms_by_group.get(group_id, [])),
                    )
                    for group_id in groups
                ],
            )

        if hasattr(self._db, "get_topics"):
            topics = await self._db.get_topics()
            return TopicsResponse(
                topics=[
                    TopicItem(
                        group_id=topic.group_id,
                        display_name=topic.display_name,
                        term_count=topic.term_count,
                    )
                    for topic in topics
                ],
            )

        logger.warning("No SubscriptionManager configured - returning empty topics")
        return TopicsResponse(topics=[])

    async def search_results(
        self,
        query_groups: list[str],
        mode: str,
        since_days: int = 30,
        max_per_term: int = 20,
        out_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """Run vigilancia search for query_groups and cluster the results."""
        if self._sub_mgr is None:
            raise RuntimeError("SubscriptionManager is required for vigilancia search")

        accepted_groups = self._validate_requested_groups(query_groups)
        terms_by_group = self._sub_mgr.get_terms_for_groups(accepted_groups)
        search_terms = self._merge_terms(terms_by_group)
        if not search_terms:
            return {
                "query_groups": accepted_groups,
                "mode": mode,
                "terms_by_group": terms_by_group,
                "total_results": 0,
                "results": [],
                "clusters": [],
                "trend_timeline": [],
                "hype_indicators": [],
                "report": {
                    "mode": mode,
                    "terms_count": 0,
                    "total_candidates": 0,
                },
            }

        filters = self._sub_mgr.get_filters_for_mode(mode)
        output_dir = Path(out_dir) if out_dir else Path(
            mkdtemp(prefix="newsradar_vigilancia_"),
        )

        candidates, report = await self._get_search_runner()(
            mode=mode,
            out_dir=output_dir,
            terms=search_terms,
            filters=filters,
            since_days=since_days,
            max_per_term=max_per_term,
        )

        serialized_results = [
            self._serialize_result(candidate, terms_by_group)
            for candidate in candidates
        ]

        return {
            "query_groups": accepted_groups,
            "mode": mode,
            "terms_by_group": terms_by_group,
            "total_results": len(serialized_results),
            "results": serialized_results,
            **self._cluster_results(serialized_results),
            "report": _as_mapping(report),
        }

    def _validate_requested_groups(self, query_groups: list[str]) -> list[str]:
        requested = list(dict.fromkeys(query_groups))
        if self._sub_mgr is None:
            if not requested:
                raise ValueError("No valid query_groups provided")
            return requested

        accepted, rejected = self._sub_mgr.validate_groups(requested)
        if rejected:
            valid_groups = self._sub_mgr.get_all_groups()
            raise ValueError(
                f"Grupos inexistentes: {rejected}. Grupos validos disponibles: {valid_groups}",
            )
        if not accepted:
            raise ValueError("No valid query_groups provided")
        return accepted

    def _get_search_runner(self) -> SearchRunner:
        if self._search_runner is None:
            from newsradar_api.infrastructure.connectors.search_orchestrator import (
                run_search,
            )

            self._search_runner = run_search
        return self._search_runner

    def _cluster_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        if self._cluster_engine is None:
            return {
                "clusters": [],
                "trend_timeline": [],
                "hype_indicators": [],
            }

        cluster_input = [
            {
                "title": item.get("title", ""),
                "excerpt": item.get("snippet", ""),
                "url": item.get("url", ""),
                "mode": item.get("mode", ""),
                "score": item.get("score", 0.0),
                "published_at": item.get("published_at"),
            }
            for item in results
        ]
        clustering_output = self._cluster_engine.cluster(cluster_input)
        return asdict(clustering_output)

    @staticmethod
    def _merge_terms(terms_by_group: dict[str, list[str]]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for terms in terms_by_group.values():
            for term in terms:
                if term not in seen:
                    seen.add(term)
                    merged.append(term)
        return merged

    @staticmethod
    def _serialize_result(
        candidate: Any,
        terms_by_group: dict[str, list[str]],
    ) -> dict[str, Any]:
        raw = _as_mapping(candidate)
        term = raw.get("term", "")
        matched_groups = [
            group_id
            for group_id, group_terms in terms_by_group.items()
            if term in group_terms
        ]
        return {
            "title": raw.get("title", ""),
            "url": raw.get("url", ""),
            "mode": raw.get("mode", ""),
            "term": term,
            "snippet": raw.get("snippet", ""),
            "published_at": raw.get("published_at"),
            "source_provider": raw.get("source_provider", ""),
            "score": float(raw.get("score", 0.0) or 0.0),
            "extra": raw.get("extra", {}),
            "matched_groups": matched_groups,
        }
