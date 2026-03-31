"""Capability: RelevanceScorer — configurable relevance scoring (0..100).

Ported from news_radar_mvp/extractor/capabilities/ranking.py.
Implements a four-factor weighted scorer with top-K selection and source diversity.

Validates: Requirements 9.1-9.5
"""
from __future__ import annotations

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "keyword_density": 40,
    "recency": 20,
    "source_authority": 20,
    "topic_alignment": 20,
}

SOURCE_AUTHORITY_MAP: dict[str, float] = {
    "tier0": 100,
    "tier1": 70,
    "tier2": 30,
}
SOURCE_AUTHORITY_UNKNOWN = 10.0

RECENCY_DECAY_PER_DAY = 14.3

SCORING_RUBRIC_PATH = Path(__file__).resolve().parents[4] / "config" / "scoring_rubric.yaml"


# ---------------------------------------------------------------------------
# Weight helpers
# ---------------------------------------------------------------------------

def _load_weights(rubric_path: Path | None = None) -> dict[str, float]:
    """Load scoring weights from YAML, falling back to defaults.

    * If the file does not exist → use defaults silently (Req 9.2).
    * If weights do not sum to 100 → normalise proportionally and log WARNING (Req 9.3).
    """
    path = rubric_path or SCORING_RUBRIC_PATH
    weights = dict(DEFAULT_WEIGHTS)

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            raw = data.get("weights", {})
            if raw and isinstance(raw, dict):
                weights = {
                    k: float(raw.get(k, DEFAULT_WEIGHTS.get(k, 0)))
                    for k in DEFAULT_WEIGHTS
                }
        except Exception:
            logger.warning("Failed to parse %s — using default weights", path)

    return _normalise_weights(weights)


def _normalise_weights(weights: dict[str, float]) -> dict[str, float]:
    """Ensure weights sum to 100; normalise proportionally if not (Req 9.3)."""
    total = sum(weights.values())
    if total == 0:
        logger.warning("All weights are zero — using defaults")
        return dict(DEFAULT_WEIGHTS)
    if not math.isclose(total, 100, abs_tol=0.01):
        logger.warning(
            "Scoring weights sum to %.2f instead of 100 — normalising",
            total,
        )
        factor = 100.0 / total
        weights = {k: v * factor for k, v in weights.items()}
    return weights


# ---------------------------------------------------------------------------
# Factor calculators
# ---------------------------------------------------------------------------

def _keyword_density(matched_count: int, total_terms: int) -> float:
    """(matched_terms_count / total_query_terms) × 100."""
    if total_terms <= 0:
        return 0.0
    return (matched_count / total_terms) * 100.0


def _recency(fetched_at: str, published_at: str | None) -> float:
    """max(0, 100 − days_since_publication × 14.3).

    Returns 0 if published_at is None or unparseable (Req 9.4).
    """
    if not published_at:
        return 0.0
    try:
        pub = datetime.fromisoformat(published_at)
        fetch = datetime.fromisoformat(fetched_at)
        days = max(0.0, (fetch - pub).total_seconds() / 86400)
    except (ValueError, TypeError):
        return 0.0
    return max(0.0, 100.0 - days * RECENCY_DECAY_PER_DAY)


def _source_authority(source_id: str, tier_map: dict[str, str] | None) -> float:
    """tier0=100, tier1=70, tier2=30, unknown=10."""
    if not tier_map:
        return SOURCE_AUTHORITY_UNKNOWN
    tier = tier_map.get(source_id, "unknown")
    return SOURCE_AUTHORITY_MAP.get(tier, SOURCE_AUTHORITY_UNKNOWN)


def _topic_alignment(
    query_terms: list[str],
    subscriber_groups: list[str] | None,
) -> float:
    """100 if document matches at least one term from subscriber's query_group, else 0."""
    if not subscriber_groups or not query_terms:
        return 0.0
    groups_set = {g.lower() for g in subscriber_groups}
    terms_set = {t.lower() for t in query_terms}
    return 100.0 if groups_set & terms_set else 0.0


# ---------------------------------------------------------------------------
# RelevanceScorer
# ---------------------------------------------------------------------------

class RelevanceScorer:
    """Configurable relevance scorer producing an integer 0..100.

    Combines four factors (Req 9.1):
    - keyword_density (default 40%)
    - recency (default 20%)
    - source_authority (default 20%)
    - topic_alignment (default 20%)

    Weights are loaded from ``scoring_rubric.yaml``; if the file is missing
    the defaults are used silently (Req 9.2).

    Parameters
    ----------
    rubric_path : Path | None
        Override path to ``scoring_rubric.yaml``.
    tier_map : dict[str, str] | None
        Mapping of ``source_id`` → tier string (``"tier0"``, ``"tier1"``, …).
    """

    def __init__(
        self,
        rubric_path: Path | None = None,
        tier_map: dict[str, str] | None = None,
    ) -> None:
        self.weights = _load_weights(rubric_path)
        self.tier_map = tier_map

    def score(
        self,
        doc: Any,
        query_terms: list[str],
        subscriber_groups: list[str] | None = None,
    ) -> int:
        """Compute relevance score for *doc*.

        Parameters
        ----------
        doc
            A ``Document``-like object with ``published_at``, ``fetched_at``,
            ``source_id``, and ``query_terms`` attributes.
        query_terms
            Full list of query terms used in the search.
        subscriber_groups
            Optional list of subscriber query-group names / terms.

        Returns
        -------
        int
            Score in [0, 100].
        """
        matched_terms: list[str] = getattr(doc, "query_terms", []) or []
        matched_count = len(matched_terms)
        total_terms = len(query_terms) if query_terms else 0

        kd = _keyword_density(matched_count, total_terms)
        rec = _recency(
            getattr(doc, "fetched_at", ""),
            getattr(doc, "published_at", None),
        )
        sa = _source_authority(
            getattr(doc, "source_id", ""),
            self.tier_map,
        )
        ta = _topic_alignment(matched_terms, subscriber_groups)

        raw = (
            kd * self.weights["keyword_density"] / 100
            + rec * self.weights["recency"] / 100
            + sa * self.weights["source_authority"] / 100
            + ta * self.weights["topic_alignment"] / 100
        )
        return max(0, min(100, round(raw)))


# ---------------------------------------------------------------------------
# Top-K selection with source diversity (Req 9.5)
# ---------------------------------------------------------------------------

def select_top_k(
    items: list[Any],
    k: int = 10,
    min_score: int = 51,
    diversity_target: int = 5,
) -> list[Any]:
    """Select up to *k* items with ``relevance_score > 50``, ensuring source diversity.

    Algorithm (greedy):
    1. Filter items with ``relevance_score > 50`` (i.e. ``>= min_score``).
    2. Sort by score descending.
    3. Greedy pass — pick highest-score item; if adding it doesn't increase
       source diversity *and* we haven't met the diversity target yet, defer it.
    4. Back-fill remaining slots from deferred items by score.

    Parameters
    ----------
    items
        Sequence of objects with ``relevance_score`` (int) and ``source_id`` (str).
    k
        Maximum items to return (default 10).
    min_score
        Minimum score threshold (exclusive >50 means ``>= 51``).
    diversity_target
        Desired number of distinct ``source_id`` values.
    """
    # 1. Filter
    eligible = [
        it for it in items
        if (getattr(it, "relevance_score", None) or 0) >= min_score
    ]

    # 2. Sort descending by score
    eligible.sort(
        key=lambda x: getattr(x, "relevance_score", 0),
        reverse=True,
    )

    # Compute actual diversity target
    all_sources = {getattr(it, "source_id", "") for it in eligible}
    target = min(diversity_target, len(all_sources))

    selected: list[Any] = []
    deferred: list[Any] = []
    seen_sources: set[str] = set()

    # 3. Greedy pass
    for it in eligible:
        if len(selected) >= k:
            break
        sid = getattr(it, "source_id", "")
        adds_diversity = sid not in seen_sources
        diversity_met = len(seen_sources) >= target

        if adds_diversity or diversity_met:
            selected.append(it)
            seen_sources.add(sid)
        else:
            deferred.append(it)

    # 4. Back-fill from deferred
    for it in deferred:
        if len(selected) >= k:
            break
        selected.append(it)
        seen_sources.add(getattr(it, "source_id", ""))

    return selected


__all__ = [
    "RelevanceScorer",
    "select_top_k",
]
