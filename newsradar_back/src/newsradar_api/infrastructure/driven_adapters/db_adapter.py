"""Database adapter — persists vigilancia subscriptions.

Manages CRUD operations for user subscriptions to topic groups.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DBAdapter:
    """Database adapter for subscription persistence.

    Parameters
    ----------
    db_url : str
        Database connection URL.
    """

    def __init__(self, db_url: str = "sqlite:///subscriptions.db") -> None:
        self._db_url = db_url

    async def save_subscription(
        self, email: str, name: str, query_groups: list[str]
    ) -> bool:
        """Persist a user subscription.

        Parameters
        ----------
        email : str
            Subscriber email.
        name : str
            Subscriber display name.
        query_groups : list[str]
            Topic groups to subscribe to.

        Returns
        -------
        bool
            True if saved successfully.
        """
        # TODO: Implement subscription persistence
        raise NotImplementedError("TODO: implement subscription save")

    async def get_subscriptions(self, email: Optional[str] = None) -> list[dict]:
        """Retrieve subscriptions, optionally filtered by email.

        Parameters
        ----------
        email : str | None
            Filter by subscriber email. None returns all.

        Returns
        -------
        list[dict]
            List of subscription records.
        """
        # TODO: Implement subscription retrieval
        raise NotImplementedError("TODO: implement subscription retrieval")
