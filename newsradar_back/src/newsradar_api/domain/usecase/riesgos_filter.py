"""Riesgos ad-hoc: build candidates for terms + date range.

Ported from news_radar_mvp/extractor/adhoc/riesgos.py
Validates: Requirements 17.1-17.3
"""
from __future__ import annotations

import logging

from newsradar_api.domain.model.pipeline_models import FetchMethod, QueueItem

from .aras_filter import _in_date_range
from .metadata_match import MatchResult, metadata_match, rank_candidates

logger = logging.getLogger("newsradar.adhoc.riesgos")


def parse_terms(terms_str: str) -> list[str]:
    """Parse comma-separated terms string (Req 17.1)."""
    return [t.strip() for t in terms_str.split(",") if t.strip()]


def filter_riesgos_candidates(
    items: list[QueueItem],
    terms: list[str],
    topk_per_source: int = 5,
    max_total: int = 50,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[MatchResult]:
    """Filter discovered items by risk terms match on metadata.

    Applies date range filter if provided (Req 17.2).
    Returns ranked candidates ready for fetch (Req 17.3).
    """
    by_source: dict[str, list[MatchResult]] = {}

    for item in items:
        if not _in_date_range(item.published_at, date_from, date_to):
            continue

        title = item.title or ""
        snippet = item.snippet or ""

        score, matched = metadata_match(title, snippet, terms)

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

    all_candidates: list[MatchResult] = []
    for source_id, candidates in by_source.items():
        ranked = rank_candidates(candidates, topk=topk_per_source)
        all_candidates.extend(ranked)

    all_candidates = rank_candidates(all_candidates, topk=max_total)

    logger.info(
        "Riesgos filter: %d items -> %d candidates for %d terms "
        "(date_from=%s, date_to=%s)",
        len(items),
        len(all_candidates),
        len(terms),
        date_from,
        date_to,
    )

    return all_candidates


def build_candidates(
    queue: list[QueueItem],
    terms: str,
    topk_per_source: int = 5,
    max_total: int = 50,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[QueueItem]:
    """Build QueueItem list from Riesgos-filtered candidates."""
    parsed_terms = parse_terms(terms)
    candidates = filter_riesgos_candidates(
        queue,
        parsed_terms,
        topk_per_source,
        max_total,
        date_from=date_from,
        date_to=date_to,
    )

    out: list[QueueItem] = []
    for c in candidates:
        qi = QueueItem(
            source_id=c.source_id,
            url=c.url,
            source_url=c.source_url,
            fetch_method=FetchMethod.HTTP,
            title=c.title,
            published_at=c.published_at,
            snippet=c.snippet,
            metadata_score=c.score,
        )
        out.append(qi)

    return out
