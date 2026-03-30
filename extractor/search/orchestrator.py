"""Search orchestrator: runs providers and applies filters."""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from .export import save_candidates_jsonl, save_search_report
from .filters import apply_filters
from .loader import get_filters_for_mode, get_terms_for_mode, load_terms
from .models import SearchCandidate, SearchReport
from .providers.arxiv import search_arxiv
from .providers.github import search_github
from .providers.google_patents import search_google_patents
from .providers.lens_patents import search_lens_patents
from .providers.epo_patents import search_epo_patents

logger = logging.getLogger("news_radar.search")

PROVIDER_MAP = {
    "papers": search_arxiv,
    "repos": search_github,
    "patents": search_epo_patents,
}

PROVIDER_NAMES = {
    "papers": "arxiv",
    "repos": "github",
    "patents": "epo_ops",
}


async def run_search(
    terms_path: str | Path,
    mode: str,
    out_dir: str | Path,
    since_days: int = 30,
    max_per_term: int = 20,
) -> tuple[list[SearchCandidate], SearchReport]:
    """
    Run search for a given mode (papers|repos|patents).
    
    Returns (candidates, report).
    """
    start = time.time()
    out_dir = Path(out_dir)
    
    terms_data = load_terms(terms_path)
    terms = get_terms_for_mode(terms_data, mode)
    filters = get_filters_for_mode(terms_data, mode)

    if not terms:
        logger.warning(f"No terms found for mode '{mode}'")
        return [], SearchReport(mode=mode, terms_count=0, total_candidates=0)
    
    provider_fn = PROVIDER_MAP.get(mode)
    if not provider_fn:
        raise ValueError(f"Unknown search mode: {mode}. Use: papers|repos|patents")
    
    logger.info(f"Search mode={mode}, terms={len(terms)}, max_per_term={max_per_term}")
    
    all_candidates: list[SearchCandidate] = []
    by_term: dict[str, int] = {}
    errors: list[dict] = []
    
    for term in terms:
        try:
            results = await provider_fn(term, max_results=max_per_term, since_days=since_days)
            all_candidates.extend(results)
            by_term[term] = len(results)
            
            # Rate limit between terms
            await asyncio.sleep(1.0)
            
        except Exception as e:
            logger.error(f"Search error for term '{term}': {e}")
            errors.append({"term": term, "error": str(e)})
            by_term[term] = 0
    
    # Apply filters
    filtered = apply_filters(all_candidates, filters, mode)
    
    logger.info(f"Search complete: {len(all_candidates)} raw -> {len(filtered)} filtered")
    
    # Build report
    duration = time.time() - start
    report = SearchReport(
        mode=mode,
        terms_count=len(terms),
        total_candidates=len(filtered),
        by_term=by_term,
        providers_used=[PROVIDER_NAMES.get(mode, mode)],
        errors=errors,
        duration_seconds=round(duration, 2),
    )
    
    # Save outputs
    save_candidates_jsonl(filtered, out_dir)
    save_search_report(report, out_dir)
    
    return filtered, report
