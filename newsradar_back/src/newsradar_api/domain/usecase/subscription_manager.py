"""SubscriptionManager — validates and manages vigilancia subscriptions.

Loads valid query_groups from ``terms_vigilancia.yaml`` (top-level keys)
and provides validation, subscription, and term retrieval.

Ported from news_radar_mvp/extractor/capabilities/subscription.py,
adapted to the hexagonal backend architecture.

Validates: Requirements 22.1-22.4
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from newsradar_api.shared_kernel.config.paths import resolve_terms_path

logger = logging.getLogger(__name__)

_DEFAULT_TERMS_PATH = resolve_terms_path()


class SubscriptionManager:
    """Validate query_groups and retrieve associated terms.

    Parameters
    ----------
    terms_path
        Path to ``terms_vigilancia.yaml``.  Defaults to
        ``newsradar_back/config/terms_vigilancia.yaml``.
    """

    def __init__(self, terms_path: str | Path | None = None) -> None:
        self._terms_path = resolve_terms_path(terms_path) if terms_path else _DEFAULT_TERMS_PATH
        self._terms_data: dict[str, Any] = {}
        self._valid_groups: set[str] = set()
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load terms_vigilancia.yaml and extract valid groups."""
        try:
            with open(self._terms_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if not isinstance(data, dict):
                logger.warning("terms_vigilancia.yaml is not a mapping — no valid groups loaded")
                return
            self._terms_data = data
            self._valid_groups = set(data.keys())
            logger.info(
                "Loaded %d query_groups from %s", len(self._valid_groups), self._terms_path,
            )
        except FileNotFoundError:
            logger.warning("terms_vigilancia.yaml not found at %s", self._terms_path)
        except Exception:
            logger.warning("Failed to load terms_vigilancia.yaml", exc_info=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def valid_groups(self) -> set[str]:
        """Set of valid query_group names from terms_vigilancia.yaml."""
        return set(self._valid_groups)

    def validate_groups(self, query_groups: list[str]) -> tuple[list[str], list[str]]:
        """Validate query_groups against terms_vigilancia.yaml keys.

        Returns
        -------
        (accepted, rejected)
            Two lists: groups that exist and groups that don't.

        Validates: Requirement 22.1
        """
        accepted: list[str] = []
        rejected: list[str] = []
        for g in query_groups:
            if g in self._valid_groups:
                accepted.append(g)
            else:
                rejected.append(g)
        return accepted, rejected

    def subscribe(self, query_groups: list[str]) -> dict[str, Any]:
        """Validate and subscribe to multiple query_groups.

        Returns a dict with subscription result including terms per group.
        Raises ValueError if any group is invalid.

        Validates: Requirements 22.1-22.4
        """
        accepted, rejected = self.validate_groups(query_groups)

        if rejected:
            valid_list = sorted(self._valid_groups)
            raise ValueError(
                f"Grupos inexistentes: {rejected}. "
                f"Grupos válidos disponibles: {valid_list}"
            )

        # Build terms mapping for accepted groups
        terms_by_group = self.get_terms_for_groups(accepted)

        return {
            "subscribed_groups": accepted,
            "terms_by_group": terms_by_group,
        }

    def get_terms_for_groups(self, query_groups: list[str]) -> dict[str, list[str]]:
        """Return terms associated to each query_group.

        Validates: Requirement 22.4
        """
        result: dict[str, list[str]] = {}
        for g in query_groups:
            section = self._terms_data.get(g, {})
            if isinstance(section, dict):
                result[g] = section.get("terms", [])
            else:
                result[g] = []
        return result

    def get_all_groups(self) -> list[str]:
        """Return all valid query_groups sorted alphabetically."""
        return sorted(self._valid_groups)

    def get_terms_for_mode(self, mode: str) -> list[str]:
        """Get search terms for a specific mode (papers, repos, patents).

        Used by SearchOrchestrator.
        """
        section = self._terms_data.get(mode, {})
        if isinstance(section, dict):
            return section.get("terms", [])
        return []

    def get_filters_for_mode(self, mode: str) -> dict[str, Any]:
        """Get filters for a specific mode (papers, repos, patents).

        Used by SearchOrchestrator.
        """
        section = self._terms_data.get(mode, {})
        if isinstance(section, dict):
            return section.get("filters", {})
        return {}
