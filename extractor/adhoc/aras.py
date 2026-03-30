"""ARAS ad-hoc: build candidates for company + date range."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from ..state import QueueItem, FetchMethod
from .match import MatchResult, metadata_match, rank_candidates

logger = logging.getLogger("news_radar.adhoc.aras")


@dataclass
class ArasFilterResult:
    """Result of ARAS candidate filtering with counts per source."""
    candidates: list[MatchResult]
    # source_id -> (matched_before_topk, selected_after_topk)
    counts_by_source: dict[str, tuple[int, int]] = field(default_factory=dict)


def company_to_terms(company: str) -> list[str]:
    """Expand company name into search terms."""
    terms = [company.strip()]
    lower = company.lower().strip()
    if " " in lower:
        terms.append(lower.replace(" ", "-"))
    return terms


def _in_date_range(
    published_at: str | None,
    date_from: str | None,
    date_to: str | None,
) -> bool:
    """Check if published_at is within date range. Items without date are included."""
    if not published_at:
        return True
    if not date_from and not date_to:
        return True
    try:
        pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        pub_date_str = pub_date.strftime("%Y-%m-%d")
        if date_from and pub_date_str < date_from:
            return False
        if date_to and pub_date_str > date_to:
            return False
        return True
    except (ValueError, TypeError):
        return True


def filter_aras_candidates(
    items: list[QueueItem],
    company: str,
    topk_per_source: int = 5,
    max_total: int = 50,
    date_from: str | None = None,
    date_to: str | None = None,
) -> ArasFilterResult:
    """Filter discovered items by company name match on metadata only.

    Applies date range filter, URL slug matching, and score penalty for
    items without ``published_at``.

    Returns ``ArasFilterResult`` with ranked candidates and per-source counts.
    """
    terms = company_to_terms(company)

    by_source: dict[str, list[MatchResult]] = {}

    for item in items:
        if not _in_date_range(item.published_at, date_from, date_to):
            continue

        title = item.title or ""
        snippet = ""

        score, matched = metadata_match(title, snippet, terms, url=item.url)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "  [%s] title=%r  score=%.2f  matched=%s",
                item.source_id, title[:80], score, matched,
            )

        # Penalize items without published_at when a date range is requested
        if score > 0 and not item.published_at and (date_from or date_to):
            score *= 0.7

        if score > 0:
            result = MatchResult(
                url=item.url,
                source_id=item.source_id,
                title=title,
                snippet=snippet,
                published_at=item.published_at,
                score=score,
                matched_terms=matched,
                source_url=item.source_url,
            )
            by_source.setdefault(item.source_id, []).append(result)

    # Top-K per source + track counts
    all_candidates: list[MatchResult] = []
    counts_by_source: dict[str, tuple[int, int]] = {}

    for source_id, candidates in by_source.items():
        matched_count = len(candidates)
        ranked = rank_candidates(candidates, topk=topk_per_source)
        selected_count = len(ranked)
        counts_by_source[source_id] = (matched_count, selected_count)
        all_candidates.extend(ranked)

    # Global top-K
    all_candidates = rank_candidates(all_candidates, topk=max_total)

    logger.info(
        f"ARAS filter: {len(items)} items -> {len(all_candidates)} candidates "
        f"for company='{company}' (date_from={date_from}, date_to={date_to})"
    )

    return ArasFilterResult(candidates=all_candidates, counts_by_source=counts_by_source)


def build_aras_candidates(
    items: list[QueueItem],
    company: str,
    topk_per_source: int = 5,
    max_total: int = 50,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[list[QueueItem], dict[str, tuple[int, int]]]:
    """Build QueueItem list from ARAS-filtered candidates.

    Returns ``(queue, counts_by_source)`` where counts_by_source maps
    source_id -> (matched_candidates, selected_candidates).
    """
    result = filter_aras_candidates(
        items, company, topk_per_source, max_total,
        date_from=date_from, date_to=date_to,
    )

    queue = []
    for c in result.candidates:
        qi = QueueItem(
            source_id=c.source_id,
            url=c.url,
            source_url=c.source_url,
            fetch_method=FetchMethod.HTTP,
            title=c.title,
            published_at=c.published_at,
        )
        queue.append(qi)

    return queue, result.counts_by_source
