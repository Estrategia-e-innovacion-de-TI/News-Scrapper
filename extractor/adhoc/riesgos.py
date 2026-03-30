"""Riesgos ad-hoc: build candidates for terms + date range."""
from __future__ import annotations

import logging
from datetime import datetime
from ..state import QueueItem, FetchMethod
from .match import MatchResult, metadata_match, rank_candidates

logger = logging.getLogger("news_radar.adhoc.riesgos")


def parse_terms(terms_str: str) -> list[str]:
    """Parse comma-separated terms string."""
    return [t.strip() for t in terms_str.split(",") if t.strip()]


def filter_riesgos_candidates(
    items: list[QueueItem],
    terms: list[str],
    topk_per_source: int = 5,
    max_total: int = 50,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[MatchResult]:
    """
    Filter discovered items by risk terms match on metadata only.
    Applies date range filter if provided.
    Returns ranked candidates ready for fetch.
    """
    from .aras import _in_date_range
    
    all_candidates: list[MatchResult] = []
    by_source: dict[str, list[MatchResult]] = {}
    
    for item in items:
        # Date range filter
        if not _in_date_range(item.published_at, date_from, date_to):
            continue
        
        title = item.title or ""
        snippet = ""
        
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
    
    for source_id, candidates in by_source.items():
        ranked = rank_candidates(candidates, topk=topk_per_source)
        all_candidates.extend(ranked)

    all_candidates = rank_candidates(all_candidates, topk=max_total)
    
    logger.info(
        f"Riesgos filter: {len(items)} items -> {len(all_candidates)} candidates "
        f"for {len(terms)} terms (date_from={date_from}, date_to={date_to})"
    )
    
    return all_candidates


def build_riesgos_candidates(
    items: list[QueueItem],
    terms_str: str,
    topk_per_source: int = 5,
    max_total: int = 50,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[QueueItem]:
    """Build QueueItem list from Riesgos-filtered candidates."""
    terms = parse_terms(terms_str)
    candidates = filter_riesgos_candidates(
        items, terms, topk_per_source, max_total,
        date_from=date_from, date_to=date_to,
    )
    
    queue = []
    for c in candidates:
        qi = QueueItem(
            source_id=c.source_id,
            url=c.url,
            source_url=c.source_url,
            fetch_method=FetchMethod.HTTP,
            title=c.title,
            published_at=c.published_at,
        )
        queue.append(qi)
    
    return queue
