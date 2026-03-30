"""Bridge to the extractor SubscriptionManager.

Provides a thin adapter so the API layer can access query_group
validation and listing without importing extractor internals directly.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_manager: Any = None


def get_subscription_manager() -> Any:
    """Return a shared SubscriptionManager instance.

    Lazily imports from ``extractor.capabilities.subscription`` so the
    dependency is optional at import time.
    """
    global _manager
    if _manager is None:
        from extractor.capabilities.subscription import SubscriptionManager
        _manager = SubscriptionManager()
    return _manager
