"""SubscriptionManager — manages per-user topic subscriptions for vigilancia.

Loads subscribers from ``subscribers.yaml`` and validates their query_groups
against the top-level keys in ``terms_vigilancia.yaml``.

Registered in CapabilityRegistry as ``subscription_manager``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .registry import CapabilityDef, register_capability

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Subscriber:
    """A single subscriber entry."""

    email: str
    name: str
    query_groups: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# SubscriptionManager
# ---------------------------------------------------------------------------


class SubscriptionManager:
    """Load and query subscriber ↔ query_group relationships.

    Parameters
    ----------
    subscribers_path
        Path to ``subscribers.yaml``.  When *None* the file is looked up at
        ``<repo_root>/subscribers.yaml`` (sibling of ``terms_vigilancia.yaml``).
    terms_path
        Path to ``terms_vigilancia.yaml`` used to validate query_groups.
    """

    def __init__(
        self,
        subscribers_path: str | Path | None = None,
        terms_path: str | Path | None = None,
    ) -> None:
        self._subscribers: list[Subscriber] = []
        self._valid_groups: set[str] = set()
        # Whether subscribers.yaml was found
        self._has_subscribers_file: bool = False

        # Resolve default paths relative to repo root
        repo_root = Path(__file__).resolve().parents[2]
        self._subscribers_path = Path(subscribers_path) if subscribers_path else repo_root / "subscribers.yaml"
        self._terms_path = Path(terms_path) if terms_path else repo_root / "terms_vigilancia.yaml"

        self._load_valid_groups()
        self._load_subscribers()

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------

    def _load_valid_groups(self) -> None:
        """Load top-level keys from terms_vigilancia.yaml as valid groups."""
        try:
            with open(self._terms_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if isinstance(data, dict):
                self._valid_groups = set(data.keys())
            else:
                logger.warning("terms_vigilancia.yaml is not a mapping — no valid groups loaded")
        except FileNotFoundError:
            logger.warning("terms_vigilancia.yaml not found at %s — no group validation", self._terms_path)
        except Exception:
            logger.warning("Failed to load terms_vigilancia.yaml", exc_info=True)

    def _load_subscribers(self) -> None:
        """Load and validate subscribers from YAML."""
        try:
            with open(self._subscribers_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except FileNotFoundError:
            logger.warning(
                "subscribers.yaml not found at %s — all query_groups will be processed without filtering",
                self._subscribers_path,
            )
            self._has_subscribers_file = False
            return
        except Exception:
            logger.warning("Failed to load subscribers.yaml", exc_info=True)
            self._has_subscribers_file = False
            return

        self._has_subscribers_file = True

        raw_list: list[dict[str, Any]] = []
        if isinstance(data, dict):
            raw_list = data.get("subscribers", []) or []
        elif isinstance(data, list):
            raw_list = data
        else:
            logger.warning("subscribers.yaml has unexpected format — expected mapping or list")
            return

        for entry in raw_list:
            if not isinstance(entry, dict):
                continue
            email = entry.get("email", "")
            name = entry.get("name", "")
            raw_groups: list[str] = entry.get("query_groups", []) or []

            # Validate each group against terms_vigilancia.yaml
            valid: list[str] = []
            for grp in raw_groups:
                if self._valid_groups and grp not in self._valid_groups:
                    logger.warning(
                        "Subscriber %s references unknown query_group '%s' — skipping group",
                        email,
                        grp,
                    )
                else:
                    valid.append(grp)

            self._subscribers.append(Subscriber(email=email, name=name, query_groups=valid))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def has_subscribers_file(self) -> bool:
        """Whether a subscribers.yaml was found and loaded."""
        return self._has_subscribers_file

    @property
    def subscribers(self) -> list[Subscriber]:
        """All loaded subscribers."""
        return list(self._subscribers)

    @property
    def valid_groups(self) -> set[str]:
        """Set of valid query_group names from terms_vigilancia.yaml."""
        return set(self._valid_groups)

    def get_subscribers_for_group(self, group: str) -> list[Subscriber]:
        """Return all subscribers interested in *group*."""
        return [s for s in self._subscribers if group in s.query_groups]

    def get_groups_for_subscriber(self, email: str) -> list[str]:
        """Return all query_groups for the subscriber identified by *email*."""
        for s in self._subscribers:
            if s.email == email:
                return list(s.query_groups)
        return []

    def get_all_groups(self) -> list[str]:
        """Return all valid query_groups (for unfiltered processing)."""
        return sorted(self._valid_groups)


# ---------------------------------------------------------------------------
# Capability registration
# ---------------------------------------------------------------------------

def _manage_subscriptions(
    subscribers_path: str | None = None,
    terms_path: str | None = None,
    **_kwargs: Any,
) -> SubscriptionManager:
    """Thin wrapper for capability registry."""
    return SubscriptionManager(
        subscribers_path=subscribers_path,
        terms_path=terms_path,
    )


_cap_subscription = CapabilityDef(
    name="subscription_manager",
    purpose="Manage per-user topic subscriptions for vigilancia weekly pipeline",
    inputs_schema={
        "subscribers_path": "str | None — path to subscribers.yaml",
        "terms_path": "str | None — path to terms_vigilancia.yaml",
    },
    outputs_schema={
        "manager": "SubscriptionManager instance",
    },
    callable=_manage_subscriptions,
    tags=["subscription", "vigilancia"],
)
register_capability(_cap_subscription)


__all__ = [
    "Subscriber",
    "SubscriptionManager",
]
