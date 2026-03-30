"""Subscription management adapter.

Manages user-topic subscriptions from subscribers.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Subscriber:
    """A subscriber with email, name, and query group interests."""
    email: str
    name: str
    query_groups: list[str] = field(default_factory=list)


class SubscriptionManager:
    """Manages subscriptions from subscribers.yaml.

    Validates query_groups against terms_vigilancia.yaml.
    Provides lookup methods for subscribers and groups.

    Implements: subscription management capability.
    """

    def __init__(
        self,
        subscribers_path: str = "subscribers.yaml",
        terms_path: str = "terms_vigilancia.yaml",
    ) -> None:
        self._subscribers_path = subscribers_path
        self._terms_path = terms_path

    def get_subscribers_for_group(self, group: str) -> list[Subscriber]:
        """Return all subscribers interested in a given query_group.

        TODO: Port implementation from extractor/capabilities/subscriptions.py
        """
        raise NotImplementedError("TODO: port SubscriptionManager from extractor")

    def get_groups_for_subscriber(self, email: str) -> list[str]:
        """Return all query_groups for a given subscriber.

        TODO: Port implementation from extractor/capabilities/subscriptions.py
        """
        raise NotImplementedError("TODO: port SubscriptionManager from extractor")
