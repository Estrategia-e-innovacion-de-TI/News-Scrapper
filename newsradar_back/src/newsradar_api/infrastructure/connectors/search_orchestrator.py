"""Search orchestrator: runs providers and applies post-search filters.

Loads terms and filters from ``terms_vigilancia.yaml`` via
SubscriptionManager, executes searches against ArXiv, GitHub, or EPO OPS,
applies mode-specific filters, saves results to JSONL, and generates a
SearchReport with statistics.

Ported from news_radar_mvp/extractor/search/orchestrator.py.

Validates: Requirements 18.1-18.5
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Awaitable

from .providers.arxiv_provider import search_arxiv
from .providers.github_provider import search_github
from .providers.epo_provider import search_epo_patents
from .search_models import SearchCandidate, SearchReport
from newsradar_api.shared_kernel.config.paths import resolve_terms_path

logger = logging.getLogger(__name__)

_DEFAULT_TERMS_PATH = resolve_terms_path()

PROVIDER_MAP: dict[str, Callable[..., Awaitable[list[SearchCandidate]]]] = {
    "papers": search_arxiv,
    "repos": search_github,
    "patents": search_epo_patents,
}

PROVIDER_NAMES: dict[str, str] = {
    "papers": "arxiv",
    "repos": "github",
    "patents": "epo_ops",
}


# ── Post-search filters ──────────────────────────────────────────────


def _filter_papers(
    candidates: list[SearchCandidate],
    filters: dict[str, Any],
) -> list[SearchCandidate]:
    """Filter paper candidates by require_keywords_any."""
    require_any = filters.get("require_keywords_any", [])
    if not require_any:
        return candidates

    require_lower = [k.lower() for k in require_any]
    return [
        c
        for c in candidates
        if any(kw in f"{c.title} {c.snippet}".lower() for kw in require_lower)
    ]


def _filter_repos(
    candidates: list[SearchCandidate],
    filters: dict[str, Any],
) -> list[SearchCandidate]:
    """Filter repo candidates by min_stars and updated_within_days."""
    min_stars = filters.get("min_stars", 0)
    updated_within_days = filters.get("updated_within_days", 0)

    result: list[SearchCandidate] = []
    for c in candidates:
        stars = c.extra.get("stars", 0)
        if min_stars and stars < min_stars:
            continue

        if updated_within_days and c.extra.get("updated_at"):
            try:
                updated = datetime.fromisoformat(
                    c.extra["updated_at"].replace("Z", "+00:00")
                )
                cutoff = datetime.now(updated.tzinfo) - timedelta(
                    days=updated_within_days
                )
                if updated < cutoff:
                    continue
            except (ValueError, TypeError):
                pass

        result.append(c)
    return result


def _filter_patents(
    candidates: list[SearchCandidate],
    filters: dict[str, Any],
) -> list[SearchCandidate]:
    """Filter patent candidates (pass-through for MVP)."""
    return candidates


def apply_filters(
    candidates: list[SearchCandidate],
    filters: dict[str, Any],
    mode: str,
) -> list[SearchCandidate]:
    """Apply mode-specific post-search filters."""
    if mode == "papers":
        return _filter_papers(candidates, filters)
    if mode == "repos":
        return _filter_repos(candidates, filters)
    if mode == "patents":
        return _filter_patents(candidates, filters)
    return candidates


# ── JSONL export ─────────────────────────────────────────────────────


def _save_candidates_jsonl(
    candidates: list[SearchCandidate],
    out_dir: Path,
) -> Path:
    """Save candidates to JSONL file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "candidates.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c.model_dump(), ensure_ascii=False) + "\n")
    return path


def _save_search_report(report: SearchReport, out_dir: Path) -> Path:
    """Save search report to JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "search_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
    return path


# ── Orchestrator ─────────────────────────────────────────────────────


async def run_search(
    mode: str,
    out_dir: str | Path,
    terms: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    terms_path: str | Path | None = None,
    since_days: int = 30,
    max_per_term: int = 20,
) -> tuple[list[SearchCandidate], SearchReport]:
    """Run search for a given mode (papers | repos | patents).

    Parameters
    ----------
    mode
        Search mode: ``papers``, ``repos``, or ``patents``.
    out_dir
        Directory to write candidates.jsonl and search_report.json.
    terms
        Explicit list of search terms. If *None*, loaded from
        ``terms_vigilancia.yaml`` for the given mode.
    filters
        Explicit filter dict. If *None*, loaded from
        ``terms_vigilancia.yaml`` for the given mode.
    terms_path
        Path to ``terms_vigilancia.yaml``. Defaults to
        ``newsradar_back/config/terms_vigilancia.yaml``.
    since_days
        Look-back window in days.
    max_per_term
        Maximum results per search term.

    Returns
    -------
    (candidates, report)
        Filtered candidates and a SearchReport with statistics.

    Validates: Requirements 18.1-18.5
    """
    import yaml

    start_time = time.time()
    out_dir = Path(out_dir)

    # Load terms and filters from YAML if not provided explicitly
    if terms is None or filters is None:
        _path = Path(terms_path) if terms_path else _DEFAULT_TERMS_PATH
        try:
            with open(_path, "r", encoding="utf-8") as fh:
                terms_data = yaml.safe_load(fh) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"Terms file not found: {_path}")

        section = terms_data.get(mode, {})
        if terms is None:
            terms = section.get("terms", [])
        if filters is None:
            filters = section.get("filters", {})

    if not terms:
        logger.warning("No terms found for mode '%s'", mode)
        return [], SearchReport(mode=mode, terms_count=0, total_candidates=0)

    provider_fn = PROVIDER_MAP.get(mode)
    if not provider_fn:
        raise ValueError(f"Unknown search mode: {mode}. Use: papers|repos|patents")

    logger.info("Search mode=%s, terms=%d, max_per_term=%d", mode, len(terms), max_per_term)

    all_candidates: list[SearchCandidate] = []
    by_term: dict[str, int] = {}
    errors: list[dict] = []

    for term in terms:
        try:
            results = await provider_fn(
                term, max_results=max_per_term, since_days=since_days,
            )
            all_candidates.extend(results)
            by_term[term] = len(results)

            # Rate limit: 1s pause between terms (Req 18.4)
            await asyncio.sleep(1.0)

        except Exception as e:
            logger.error("Search error for term '%s': %s", term, e)
            errors.append({"term": term, "error": str(e)})
            by_term[term] = 0

    # Apply post-search filters (Req 18.3)
    filtered = apply_filters(all_candidates, filters or {}, mode)

    logger.info(
        "Search complete: %d raw -> %d filtered", len(all_candidates), len(filtered),
    )

    # Build report (Req 18.5)
    duration = time.time() - start_time
    report = SearchReport(
        mode=mode,
        terms_count=len(terms),
        total_candidates=len(filtered),
        by_term=by_term,
        providers_used=[PROVIDER_NAMES.get(mode, mode)],
        errors=errors,
        duration_seconds=round(duration, 2),
    )

    # Save outputs (Req 18.5)
    _save_candidates_jsonl(filtered, out_dir)
    _save_search_report(report, out_dir)

    return filtered, report
