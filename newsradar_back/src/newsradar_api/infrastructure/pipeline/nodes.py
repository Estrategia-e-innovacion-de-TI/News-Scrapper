"""LangGraph node functions for the news extraction pipeline.

Ported from ``news_radar_mvp/extractor/graph.py`` and adapted to the
hexagonal architecture of ``newsradar_back``.  Each async function
receives a :class:`GraphState` and returns a partial dict update.

Validates: Requirements 19.1-19.6
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from newsradar_api.domain.model.pipeline_models import (
    Document,
    ErrorType,
    FetchMethod,
    GraphState,
    ItemStatus,
    QueueItem,
    SkipReason,
    SourceConfig,
    SourceMetrics,
)

logger = logging.getLogger("newsradar.pipeline.nodes")

_ERROR_TYPE_VALUES = {e.value for e in ErrorType}


# ── Helpers ───────────────────────────────────────────────────────────


def _safe_error_type(val: str | None) -> ErrorType:
    """Convert string to ErrorType safely, defaulting to UNKNOWN."""
    if val and val in _ERROR_TYPE_VALUES:
        return ErrorType(val)
    return ErrorType.UNKNOWN


def _compute_content_hash(title: str, text: str) -> str:
    """SHA-256 hash of title + text for deduplication."""
    payload = f"{title.strip().lower()}|{text.strip()[:2000]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _detect_language(text: str) -> str:
    """Simple language detection heuristic."""
    sample = text[:2000].lower()
    es_markers = ["el ", "la ", "los ", "las ", "de ", "en ", "que ", "por ", "con "]
    en_markers = ["the ", "and ", "for ", "with ", "that ", "this ", "from "]
    es_count = sum(sample.count(m) for m in es_markers)
    en_count = sum(sample.count(m) for m in en_markers)
    if es_count > en_count:
        return "es"
    if en_count > es_count:
        return "en"
    return "unknown"


def _truncate_text(text: str, max_len: int = 500) -> str:
    """Truncate text to *max_len* characters."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def _query_terms_list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _dedupe_terms(terms: list[str], limit: int | None = None) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for raw in terms:
        term = str(raw).strip()
        if not term:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        values.append(term)
        if limit is not None and len(values) >= limit:
            break
    return values


def _batch_flow_filename(focus: str | None) -> str | None:
    if focus == "vigilancia_news":
        return "tech_watch.yaml"
    if focus == "riesgos_news":
        return "risk_mapping.yaml"
    return None


def _batch_flow_sources(focus: str | None) -> dict[str, Any]:
    from newsradar_api.shared_kernel.config.paths import load_yaml_file, resolve_flow_path

    filename = _batch_flow_filename(focus)
    if not filename:
        return {}
    path = resolve_flow_path(filename)
    if not path.exists():
        return {}
    data = load_yaml_file(path)
    sources = data.get("sources")
    return sources if isinstance(sources, dict) else {}


def _enabled_flow_source(focus: str | None, key: str) -> dict[str, Any]:
    sources = _batch_flow_sources(focus)
    raw = sources.get(key)
    if isinstance(raw, dict) and raw.get("enabled", False):
        return raw
    return {}


def _batch_search_groups(focus: str | None) -> list[list[str]]:
    from newsradar_api.shared_kernel.config.paths import load_yaml_file, shared_path

    if focus == "vigilancia_news":
        data = load_yaml_file(shared_path("topics", "tech_watch.yaml"))
        groups: list[list[str]] = []
        for value in data.values():
            if not isinstance(value, dict):
                continue
            terms = _dedupe_terms([str(item) for item in value.get("terms") or []], limit=4)
            if terms:
                groups.append(terms)
        return groups

    if focus == "riesgos_news":
        taxonomy = load_yaml_file(shared_path("topics", "analytics_taxonomy.yaml"))
        groups = []
        for category in taxonomy.get("risk_categories") or []:
            if not isinstance(category, dict):
                continue
            terms = [str(category.get("name") or "").replace("/", " ")]
            terms.extend(str(item) for item in (category.get("keywords") or [])[:3])
            group = _dedupe_terms(terms, limit=4)
            if group:
                groups.append(group)
        return groups

    return []


def _batch_arxiv_terms(focus: str | None, max_terms: int = 10) -> list[str]:
    if focus != "vigilancia_news":
        return []
    values: list[str] = []
    for group in _batch_search_groups(focus):
        values.extend(group[:2])
        if len(values) >= max_terms:
            break
    return _dedupe_terms(values, limit=max_terms)


def _ensure_synthetic_source(
    selected_sources: list[SourceConfig],
    *,
    source_id: str,
    name: str,
    source_type: str = "scrape",
    pipeline_class: str = "news",
    min_text_chars: int = 120,
    timeout_seconds: int = 20,
) -> None:
    if any(source.source_id == source_id for source in selected_sources):
        return
    selected_sources.append(
        SourceConfig(
            source_id=source_id,
            name=name,
            type=source_type,  # type: ignore[arg-type]
            enabled=True,
            focus=[],
            pipeline_class=pipeline_class,
            min_text_chars=min_text_chars,
            timeout_seconds=timeout_seconds,
        )
    )


def _append_unique_queue_items(queue: list[QueueItem], items: list[QueueItem]) -> int:
    existing = {
        (item.source_id, item.url.strip().lower())
        for item in queue
        if item.url
    }
    added = 0
    for item in items:
        key = (item.source_id, item.url.strip().lower())
        if not item.url or key in existing:
            continue
        existing.add(key)
        queue.append(item)
        added += 1
    return added


def _init_source_metrics(source_id: str, requires_playwright: bool = False) -> SourceMetrics:
    """Create a fresh :class:`SourceMetrics` for *source_id*."""
    return SourceMetrics(source_id=source_id, requires_playwright=requires_playwright)


def _update_source_metrics(
    metrics: SourceMetrics,
    *,
    discovered: int = 0,
    fetched_ok: int = 0,
    text_ok: int = 0,
    dupes: int = 0,
    skipped: int = 0,
    errors: int = 0,
    error_type: str | None = None,
    text_len: int = 0,
) -> SourceMetrics:
    """Return an updated copy of *metrics* with incremented counters."""
    m = metrics.model_copy()
    m.discovered += discovered
    m.fetched_ok += fetched_ok
    m.text_ok += text_ok
    m.dupes += dupes
    m.skipped += skipped
    m.errors += errors
    if error_type:
        m.errors_by_type[error_type] = m.errors_by_type.get(error_type, 0) + 1
    if text_len and m.text_ok > 0:
        m.avg_text_len = (
            (m.avg_text_len * (m.text_ok - text_ok) + text_len) / m.text_ok
            if m.text_ok > 0
            else float(text_len)
        )
    return m


# ======================================================================
# NODE: load_catalog
# ======================================================================


async def load_catalog_node(state: GraphState) -> dict[str, Any]:
    """Load and validate catalog from YAML."""
    from newsradar_api.infrastructure.connectors.catalog_loader import load_sources

    logger.info("Loading catalog from %s", state.catalog_path)
    defaults, sources = load_sources(state.catalog_path)
    logger.info("Loaded %d sources from catalog", len(sources))
    return {"defaults": defaults, "sources": sources}


# ======================================================================
# NODE: select_sources
# ======================================================================


async def select_sources_node(state: GraphState) -> dict[str, Any]:
    """Filter sources based on CLI / API params."""
    from newsradar_api.infrastructure.connectors.catalog_loader import filter_sources

    selected = filter_sources(
        state.sources,
        only_source=state.only_source,
        include_disabled=False,
        focus=state.focus,
    )

    source_metrics: dict[str, SourceMetrics] = {}
    for src in selected:
        source_metrics[src.source_id] = _init_source_metrics(
            src.source_id, src.requires_playwright
        )

    logger.info("Selected %d enabled sources", len(selected))
    return {"selected_sources": selected, "source_metrics": source_metrics}


async def _augment_with_batch_google_news(
    state: GraphState,
    *,
    queue: list[QueueItem],
    source_metrics: dict[str, SourceMetrics],
    selected_sources: list[SourceConfig],
) -> None:
    from newsradar_api.infrastructure.connectors import google_news_connector

    source_cfg = _enabled_flow_source(state.focus, "google_news")
    if not source_cfg:
        return

    search_groups = _batch_search_groups(state.focus)
    if not search_groups:
        return

    max_queries = int(source_cfg.get("max_queries", 6))
    max_items = int(source_cfg.get("max_items", 18))
    per_query = max(4, min(max_items, max(4, math.ceil(max_items / max(max_queries, 1)))))

    batch_items: list[QueueItem] = []
    for group in search_groups[:max_queries]:
        items = await google_news_connector.search(
            terms=group,
            date_from=state.date_from,
            date_to=state.date_to,
            max_items=per_query,
        )
        for item in items:
            item.query_terms = list(group)
            batch_items.append(item)

    if not batch_items:
        return

    _ensure_synthetic_source(
        selected_sources,
        source_id="google_news",
        name="Google News",
        source_type="scrape",
        pipeline_class="news",
        min_text_chars=120,
        timeout_seconds=20,
    )
    if "google_news" not in source_metrics:
        source_metrics["google_news"] = _init_source_metrics("google_news", False)
    discovered = _append_unique_queue_items(queue, batch_items)
    if discovered:
        source_metrics["google_news"] = _update_source_metrics(
            source_metrics["google_news"],
            discovered=discovered,
        )
        logger.info("Batch Google News added %d items for focus=%s", discovered, state.focus)


async def _augment_with_batch_arxiv(
    state: GraphState,
    *,
    queue: list[QueueItem],
    source_metrics: dict[str, SourceMetrics],
    selected_sources: list[SourceConfig],
) -> None:
    from newsradar_api.infrastructure.connectors.providers.arxiv_provider import search_arxiv

    source_cfg = _enabled_flow_source(state.focus, "arxiv_papers")
    if not source_cfg:
        return

    terms = _batch_arxiv_terms(
        state.focus,
        max_terms=int(source_cfg.get("max_terms", 10)),
    )
    if not terms:
        return

    max_items_per_term = int(source_cfg.get("max_items_per_term", 6))
    batch_items: list[QueueItem] = []
    for term in terms:
        for candidate in await search_arxiv(
            term,
            max_results=max_items_per_term,
            since_days=max(state.days, 30),
        ):
            batch_items.append(
                QueueItem(
                    source_id="arxiv",
                    url=candidate.url,
                    source_url="arxiv_api",
                    fetch_method=FetchMethod.HTTP,
                    title=candidate.title,
                    published_at=candidate.published_at,
                    snippet=candidate.snippet,
                    query_terms=[candidate.term],
                )
            )

    if not batch_items:
        return

    _ensure_synthetic_source(
        selected_sources,
        source_id="arxiv",
        name="ArXiv",
        source_type="scrape",
        pipeline_class="paper",
        min_text_chars=80,
        timeout_seconds=20,
    )
    if "arxiv" not in source_metrics:
        source_metrics["arxiv"] = _init_source_metrics("arxiv", False)
    discovered = _append_unique_queue_items(queue, batch_items)
    if discovered:
        source_metrics["arxiv"] = _update_source_metrics(
            source_metrics["arxiv"],
            discovered=discovered,
        )
        logger.info("Batch ArXiv added %d items for focus=%s", discovered, state.focus)


# ======================================================================
# NODE: discover_items
# ======================================================================


async def discover_items_node(state: GraphState) -> dict[str, Any]:
    """Discover items from all selected sources, with ad-hoc / candidates support."""
    queue: list[QueueItem] = []
    source_metrics = {k: v.model_copy() for k, v in state.source_metrics.items()}
    selected_sources = list(state.selected_sources)
    errors = list(state.errors)

    # --- Candidates ingestion mode ---
    if state.candidates_path:
        cpath = Path(state.candidates_path)
        if cpath.exists():
            with open(cpath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    qi = QueueItem(
                        source_id=data.get("source_provider", "search"),
                        url=data.get("url", ""),
                        source_url=data.get("url", ""),
                        fetch_method=FetchMethod.HTTP,
                        title=data.get("title", ""),
                        snippet=data.get("snippet"),
                        query_terms=_dedupe_terms(data.get("query_terms") or ([data.get("term")] if data.get("term") else [])),
                    )
                    queue.append(qi)
            logger.info("Loaded %d candidates from %s", len(queue), state.candidates_path)
            return {
                "queue": queue,
                "source_metrics": source_metrics,
                "selected_sources": selected_sources,
                "errors": errors,
            }

    # --- Determine if catalog RSS/scrape discovery should be skipped ---
    _skip_catalog = False
    if state.adhoc and state.date_to:
        try:
            dt_to = datetime.strptime(state.date_to, "%Y-%m-%d")
            if dt_to < datetime.utcnow() - timedelta(days=3):
                _skip_catalog = True
                logger.info(
                    "Historical query (date_to=%s) — skipping catalog RSS/scrape, "
                    "using Google News only",
                    state.date_to,
                )
        except ValueError:
            pass

    # --- Standard discovery from catalog ---
    if not _skip_catalog:
        from newsradar_api.infrastructure.connectors import rss_connector
        from newsradar_api.infrastructure.connectors import scrape_connector

        for source in state.selected_sources:
            try:
                items: list[QueueItem] = []

                if source.type == "rss":
                    items = await rss_connector.discover(
                        source, days=state.days, max_items=state.max_items_per_source
                    )
                elif source.type == "scrape":
                    items = await scrape_connector.discover(
                        source, max_items=state.max_items_per_source
                    )
                elif source.type == "pdf":
                    # PDF discovery — create items from pdf_urls
                    for pdf_url in source.pdf_urls[:state.max_items_per_source]:
                        items.append(
                            QueueItem(
                                source_id=source.source_id,
                                url=pdf_url,
                                source_url=pdf_url,
                                fetch_method=FetchMethod.PDF,
                            )
                        )
                elif source.type in ("query", "custom"):
                    item = QueueItem(
                        source_id=source.source_id,
                        url=source.base_url or "",
                        source_url=source.base_url or "",
                        fetch_method=FetchMethod.HTTP,
                        status=ItemStatus.SKIPPED,
                        error_type=ErrorType.CUSTOM_PENDING,
                        error_msg=f"Type '{source.type}' not supported yet",
                    )
                    items = [item]

                queue.extend(items)

                if source.source_id in source_metrics:
                    discovered = len([i for i in items if i.status != ItemStatus.SKIPPED])
                    skipped = len([i for i in items if i.status == ItemStatus.SKIPPED])
                    source_metrics[source.source_id] = _update_source_metrics(
                        source_metrics[source.source_id],
                        discovered=discovered,
                        skipped=skipped,
                    )
            except Exception as e:
                logger.error("[%s] Discovery error: %s", source.source_id, e)
                errors.append(
                    {"source_id": source.source_id, "phase": "discover", "error": str(e)}
                )

    # --- Ad-hoc: augment with Google News ---
    if state.adhoc and (state.company or state.terms):
        from newsradar_api.infrastructure.connectors import google_news_connector

        terms_list = (
            [t.strip() for t in state.terms.split(",") if t.strip()]
            if state.terms
            else None
        )
        gn_items = await google_news_connector.search(
            company=state.company,
            terms=terms_list,
            date_from=state.date_from,
            date_to=state.date_to,
            max_items=30,
        )
        if gn_items:
            for item in gn_items:
                item.query_terms = _dedupe_terms(terms_list or ([state.company] if state.company else []))
            queue.extend(gn_items)
            if "google_news" not in source_metrics:
                source_metrics["google_news"] = _update_source_metrics(
                    _init_source_metrics("google_news", False),
                    discovered=len(gn_items),
                )
            logger.info("Google News augmented queue with %d items", len(gn_items))

    # --- Ad-hoc filtering (metadata-only match) ---
    if state.adhoc and state.focus == "aras_news" and state.company:
        from newsradar_api.domain.usecase.aras_filter import build_candidates

        pre_count = len(queue)
        effective_topk = (
            max(state.topk_per_source, 50)
            if any(i.source_id == "google_news" for i in queue)
            else state.topk_per_source
        )
        queue, counts_by_source = build_candidates(
            queue,
            company=state.company,
            topk_per_source=effective_topk,
            max_total=state.max_candidates_total,
            date_from=state.date_from,
            date_to=state.date_to,
        )
        for sid, (matched, selected) in counts_by_source.items():
            if sid in source_metrics:
                source_metrics[sid].matched_candidates = matched
                source_metrics[sid].selected_candidates = selected
        logger.info(
            "ARAS adhoc: %d discovered -> %d candidates for '%s'",
            pre_count, len(queue), state.company,
        )

    elif state.adhoc and state.focus == "riesgos_news" and state.terms:
        from newsradar_api.domain.usecase.riesgos_filter import build_candidates as build_riesgos

        pre_count = len(queue)
        effective_topk = (
            max(state.topk_per_source, 50)
            if any(i.source_id == "google_news" for i in queue)
            else state.topk_per_source
        )
        queue = build_riesgos(
            queue,
            terms=state.terms,
            topk_per_source=effective_topk,
            max_total=state.max_candidates_total,
            date_from=state.date_from,
            date_to=state.date_to,
        )
        logger.info(
            "Riesgos adhoc: %d discovered -> %d candidates for terms",
            pre_count, len(queue),
        )

    if not state.adhoc and state.focus in {"vigilancia_news", "riesgos_news"}:
        await _augment_with_batch_google_news(
            state,
            queue=queue,
            source_metrics=source_metrics,
            selected_sources=selected_sources,
        )
        if state.focus == "vigilancia_news":
            await _augment_with_batch_arxiv(
                state,
                queue=queue,
                source_metrics=source_metrics,
                selected_sources=selected_sources,
            )

    logger.info("Total items in queue: %d", len(queue))
    return {
        "queue": queue,
        "source_metrics": source_metrics,
        "selected_sources": selected_sources,
        "errors": errors,
    }


# ======================================================================
# NODE: split_lane
# ======================================================================


async def split_lane_node(state: GraphState) -> dict[str, Any]:
    """Split queue into lanes: http, browser, pdf, skipped."""
    http_queue: list[QueueItem] = []
    browser_queue: list[QueueItem] = []
    pdf_queue: list[QueueItem] = []
    skipped_queue: list[QueueItem] = []

    for item in state.queue:
        if item.status == ItemStatus.SKIPPED:
            skipped_queue.append(item)
            continue

        if item.fetch_method == FetchMethod.PDF:
            pdf_queue.append(item)
            continue

        if item.requires_playwright and not state.no_playwright:
            browser_queue.append(item)
            continue

        if item.requires_playwright and state.no_playwright:
            item.status = ItemStatus.SKIPPED
            item.error_type = ErrorType.DISABLED
            item.skip_reason = SkipReason.PLAYWRIGHT_DISABLED
            item.error_msg = "Playwright disabled via --no-playwright"
            skipped_queue.append(item)
            continue

        http_queue.append(item)

    logger.info(
        "Split lanes: http=%d, browser=%d, pdf=%d, skipped=%d",
        len(http_queue), len(browser_queue), len(pdf_queue), len(skipped_queue),
    )
    return {
        "http_queue": http_queue,
        "browser_queue": browser_queue,
        "pdf_queue": pdf_queue,
        "skipped_queue": skipped_queue,
    }


# ======================================================================
# HELPER: Process HTML → Document
# ======================================================================


async def _process_html(
    html: str,
    item: QueueItem,
    source: SourceConfig,
    state: GraphState,
    seen_hashes: set[str],
    fetch_method: str = "http",
) -> Document | None:
    """Process HTML and create Document. Returns None if duplicate or error."""
    from newsradar_api.infrastructure.extractors.text_extractor import TextExtractor
    from newsradar_api.infrastructure.extractors.metadata_extractor import MetadataExtractor

    extractor = TextExtractor()
    meta_extractor = MetadataExtractor()

    text, method = extractor.extract(html, source.min_text_chars)

    if not text or len(text) < source.min_text_chars:
        item.status = ItemStatus.ERROR
        item.error_type = ErrorType.EMPTY
        return None

    text = extractor.clean_text(text)

    # Text cap
    text_capped = False
    if len(text) > state.max_text_chars:
        text = text[: state.max_text_chars]
        text_capped = True

    # Extract metadata
    meta = meta_extractor.extract(html)
    title = item.title or meta.title or ""

    # Dedupe
    content_hash = _compute_content_hash(title, text)
    if content_hash in seen_hashes:
        item.status = ItemStatus.OK
        return None

    # Determine provenance
    origin = "catalog"
    query_type: str | None = None
    query_terms: list[str] = list(item.query_terms or [])
    query_range: dict[str, str] = {}
    if state.candidates_path:
        origin = "search_ingest"
    elif item.source_id in {"google_news", "arxiv"}:
        origin = "search_ingest"
        if state.focus == "vigilancia_news":
            query_type = "vigilancia"
        elif state.focus == "riesgos_news":
            query_type = "riesgos"
    elif state.adhoc and state.focus:
        origin = "adhoc_query"
        if state.focus == "aras_news":
            query_type = "aras"
            query_terms = query_terms or ([state.company] if state.company else [])
        elif state.focus == "riesgos_news":
            query_type = "riesgos"
            query_terms = query_terms or _query_terms_list(state.terms)
    if state.date_from and state.date_to:
        query_range = {"from": state.date_from, "to": state.date_to}

    return Document(
        run_id=state.run_id,
        source_id=item.source_id,
        pipeline_class=source.pipeline_class,
        focus=source.focus,
        title=title,
        url=item.url,
        canonical_url=meta.canonical_url or item.url,
        published_at=item.published_at or meta.published_at,
        fetched_at=datetime.utcnow().isoformat(),
        language=_detect_language(text),
        text=text,
        excerpt=_truncate_text(text, 500),
        raw_len=len(html),
        text_len=len(text),
        text_capped=text_capped,
        hash=content_hash,
        fetch_method=fetch_method if fetch_method != "http" else item.fetch_method.value,
        status="ok",
        source_url=item.source_url,
        origin=origin,
        query_type=query_type,
        query_terms=query_terms,
        query_range=query_range,
    )


def _document_from_search_metadata(
    item: QueueItem,
    source: SourceConfig,
    state: GraphState,
    seen_hashes: set[str],
) -> Document | None:
    text = " ".join(
        part for part in [item.title or "", item.snippet or ""] if part
    ).strip()
    if not text:
        item.status = ItemStatus.ERROR
        item.error_type = ErrorType.EMPTY
        return None

    content_hash = _compute_content_hash(item.title or item.url, text)
    if content_hash in seen_hashes:
        item.status = ItemStatus.OK
        return None

    if len(text) > state.max_text_chars:
        text = text[: state.max_text_chars]

    query_type: str | None = None
    if state.focus == "vigilancia_news":
        query_type = "vigilancia"
    elif state.focus == "riesgos_news":
        query_type = "riesgos"

    return Document(
        run_id=state.run_id,
        source_id=item.source_id,
        pipeline_class=source.pipeline_class,
        focus=source.focus or ([state.focus] if state.focus else []),
        title=item.title or item.url,
        url=item.url,
        canonical_url=item.url,
        published_at=item.published_at,
        fetched_at=datetime.utcnow().isoformat(),
        language=_detect_language(text),
        text=text,
        excerpt=_truncate_text(item.snippet or text, 500),
        raw_len=len(text),
        text_len=len(text),
        text_capped=False,
        hash=content_hash,
        fetch_method=item.fetch_method.value,
        status="ok",
        source_url=item.source_url,
        origin="search_ingest",
        query_type=query_type,
        query_terms=list(item.query_terms or []),
        query_range=(
            {"from": state.date_from, "to": state.date_to}
            if state.date_from and state.date_to
            else {}
        ),
    )


# ======================================================================
# NODE: fetch_content_http
# ======================================================================


async def fetch_content_http_node(state: GraphState) -> dict[str, Any]:
    """Fetch content via HTTP for items in http_queue."""
    if state.dry_run:
        logger.info("Dry run: skipping HTTP fetch")
        return {}

    documents = list(state.documents)
    source_metrics = {k: v.model_copy() for k, v in state.source_metrics.items()}
    seen_hashes = set(state.seen_hashes)
    errors = list(state.errors)

    source_map = {s.source_id: s for s in state.selected_sources}

    _fallback_source = SourceConfig(
        source_id="_search",
        name="Search Candidate",
        type="scrape",
        min_text_chars=100,
        timeout_seconds=20,
    )

    samples_per_source: dict[str, int] = {}
    max_samples = 3 if state.debug else 999

    from newsradar_api.infrastructure.connectors.scrape_connector import _fetch_html
    from newsradar_api.infrastructure.connectors.utils import rate_limiter

    for item in state.http_queue:
        source = source_map.get(item.source_id)
        if not source:
            if state.candidates_path or item.source_id in {"google_news", "arxiv"}:
                source = _fallback_source
            else:
                continue

        samples_per_source.setdefault(item.source_id, 0)
        if state.debug and samples_per_source[item.source_id] >= max_samples:
            continue

        if item.source_id == "arxiv" and item.snippet:
            doc = _document_from_search_metadata(
                item=item,
                source=source,
                state=state,
                seen_hashes=seen_hashes,
            )
            if doc:
                documents.append(doc)
                seen_hashes.add(doc.hash)
                samples_per_source[item.source_id] += 1
                if item.source_id in source_metrics:
                    source_metrics[item.source_id] = _update_source_metrics(
                        source_metrics[item.source_id],
                        fetched_ok=1,
                        text_ok=1,
                        text_len=doc.text_len,
                    )
            elif item.source_id in source_metrics and item.status == ItemStatus.OK:
                source_metrics[item.source_id] = _update_source_metrics(
                    source_metrics[item.source_id],
                    fetched_ok=1,
                    dupes=1,
                )
            continue

        await rate_limiter.wait(item.source_id, source.rate_limit_rps)
        logger.debug("[%s] Fetching: %s", item.source_id, item.url)

        html, status = await _fetch_html(item.url, timeout=source.timeout_seconds)

        if not html or status >= 400:
            item.status = ItemStatus.ERROR
            error_type_str = (
                "timeout" if status == 0
                else f"http_{status}" if status > 0
                else "unknown"
            )
            item.error_type = _safe_error_type(error_type_str)
            if item.source_id in source_metrics:
                source_metrics[item.source_id] = _update_source_metrics(
                    source_metrics[item.source_id], errors=1, error_type=error_type_str
                )
            continue

        doc = await _process_html(
            html=html,
            item=item,
            source=source,
            state=state,
            seen_hashes=seen_hashes,
        )

        if doc:
            documents.append(doc)
            seen_hashes.add(doc.hash)
            samples_per_source[item.source_id] += 1
            if item.source_id in source_metrics:
                source_metrics[item.source_id] = _update_source_metrics(
                    source_metrics[item.source_id],
                    fetched_ok=1, text_ok=1, text_len=doc.text_len,
                )
        elif doc is None and item.status == ItemStatus.OK:
            # Duplicate
            if item.source_id in source_metrics:
                source_metrics[item.source_id] = _update_source_metrics(
                    source_metrics[item.source_id], fetched_ok=1, dupes=1
                )

    logger.info("HTTP fetch complete: %d documents", len(documents))
    return {
        "documents": documents,
        "source_metrics": source_metrics,
        "seen_hashes": seen_hashes,
        "errors": errors,
    }


# ======================================================================
# NODE: fetch_content_browser
# ======================================================================


async def fetch_content_browser_node(state: GraphState) -> dict[str, Any]:
    """Fetch content via Playwright for items in browser_queue."""
    if state.dry_run:
        logger.info("Dry run: skipping browser fetch")
        return {}

    if not state.browser_queue:
        return {}

    documents = list(state.documents)
    source_metrics = {k: v.model_copy() for k, v in state.source_metrics.items()}
    seen_hashes = set(state.seen_hashes)

    source_map = {s.source_id: s for s in state.selected_sources}
    samples_per_source: dict[str, int] = {}
    max_samples = 3 if state.debug else 999

    from newsradar_api.infrastructure.connectors.utils import rate_limiter

    # Try to import playwright-based fetch; if not available, skip
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed — skipping browser fetch")
        return {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for item in state.browser_queue:
                source = source_map.get(item.source_id)
                if not source:
                    continue

                samples_per_source.setdefault(item.source_id, 0)
                if state.debug and samples_per_source[item.source_id] >= max_samples:
                    continue

                await rate_limiter.wait(item.source_id, source.rate_limit_rps)
                logger.debug("[%s] Browser fetch: %s", item.source_id, item.url)

                try:
                    page = await browser.new_page()
                    await page.goto(item.url, timeout=source.timeout_seconds * 1000)
                    html = await page.content()
                    await page.close()
                except Exception as exc:
                    logger.error("[%s] Browser fetch error: %s", item.source_id, exc)
                    item.status = ItemStatus.ERROR
                    item.error_type = ErrorType.TIMEOUT
                    if item.source_id in source_metrics:
                        source_metrics[item.source_id] = _update_source_metrics(
                            source_metrics[item.source_id], errors=1, error_type="timeout"
                        )
                    continue

                doc = await _process_html(
                    html=html,
                    item=item,
                    source=source,
                    state=state,
                    seen_hashes=seen_hashes,
                    fetch_method="playwright",
                )

                if doc:
                    documents.append(doc)
                    seen_hashes.add(doc.hash)
                    samples_per_source[item.source_id] += 1
                    if item.source_id in source_metrics:
                        source_metrics[item.source_id] = _update_source_metrics(
                            source_metrics[item.source_id],
                            fetched_ok=1, text_ok=1, text_len=doc.text_len,
                        )
        finally:
            await browser.close()

    logger.info("Browser fetch complete: %d documents", len(documents))
    return {
        "documents": documents,
        "source_metrics": source_metrics,
        "seen_hashes": seen_hashes,
    }


# ======================================================================
# NODE: extract_pdf
# ======================================================================


async def extract_pdf_node(state: GraphState) -> dict[str, Any]:
    """Extract text from PDF items."""
    if state.dry_run:
        logger.info("Dry run: skipping PDF extraction")
        return {}

    if not state.pdf_queue:
        return {}

    documents = list(state.documents)
    source_metrics = {k: v.model_copy() for k, v in state.source_metrics.items()}
    seen_hashes = set(state.seen_hashes)

    source_map = {s.source_id: s for s in state.selected_sources}

    from newsradar_api.infrastructure.connectors.utils import rate_limiter

    for item in state.pdf_queue:
        source = source_map.get(item.source_id)
        if not source:
            continue

        logger.debug("[%s] PDF extract: %s", item.source_id, item.url)

        await rate_limiter.wait(item.source_id, source.rate_limit_rps)

        # Fetch PDF and extract text
        text: str | None = None
        error_type_str: str | None = None
        try:
            import httpx

            async with httpx.AsyncClient(
                timeout=source.timeout_seconds, follow_redirects=True, verify=False
            ) as client:
                resp = await client.get(item.url)
                resp.raise_for_status()
                pdf_bytes = resp.content

            # Try pdfplumber, fallback to PyPDF2
            try:
                import pdfplumber

                import io
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    pages_text = [p.extract_text() or "" for p in pdf.pages]
                    text = "\n".join(pages_text)
            except ImportError:
                try:
                    from PyPDF2 import PdfReader
                    import io

                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    pages_text = [p.extract_text() or "" for p in reader.pages]
                    text = "\n".join(pages_text)
                except ImportError:
                    error_type_str = "pdf_parse_error"
                    logger.warning("No PDF library available (pdfplumber or PyPDF2)")
        except Exception as exc:
            error_type_str = "timeout" if "timeout" in str(exc).lower() else "pdf_parse_error"
            logger.error("[%s] PDF fetch/parse error: %s", item.source_id, exc)

        if error_type_str or not text:
            item.status = ItemStatus.ERROR
            item.error_type = _safe_error_type(error_type_str)
            if item.source_id in source_metrics:
                source_metrics[item.source_id] = _update_source_metrics(
                    source_metrics[item.source_id],
                    errors=1, error_type=error_type_str or "parse_error",
                )
            continue

        if len(text) < source.min_text_chars:
            item.status = ItemStatus.ERROR
            item.error_type = ErrorType.EMPTY
            if item.source_id in source_metrics:
                source_metrics[item.source_id] = _update_source_metrics(
                    source_metrics[item.source_id], errors=1, error_type="empty_or_thin"
                )
            continue

        content_hash = _compute_content_hash(item.url, text)
        if content_hash in seen_hashes:
            if item.source_id in source_metrics:
                source_metrics[item.source_id] = _update_source_metrics(
                    source_metrics[item.source_id], fetched_ok=1, dupes=1
                )
            continue

        seen_hashes.add(content_hash)

        doc = Document(
            run_id=state.run_id,
            source_id=item.source_id,
            pipeline_class=source.pipeline_class if hasattr(source, "pipeline_class") else "news",
            focus=source.focus if hasattr(source, "focus") else [],
            title=item.url.split("/")[-1],
            url=item.url,
            canonical_url=item.url,
            published_at=None,
            fetched_at=datetime.utcnow().isoformat(),
            language=_detect_language(text),
            text=text,
            excerpt=_truncate_text(text, 500),
            raw_len=len(text),
            text_len=len(text),
            hash=content_hash,
            fetch_method="pdf",
            status="ok",
            source_url=item.source_url,
        )
        documents.append(doc)
        if item.source_id in source_metrics:
            source_metrics[item.source_id] = _update_source_metrics(
                source_metrics[item.source_id],
                fetched_ok=1, text_ok=1, text_len=len(text),
            )

    logger.info("PDF extraction complete: %d documents", len(documents))
    return {
        "documents": documents,
        "source_metrics": source_metrics,
        "seen_hashes": seen_hashes,
    }


# ======================================================================
# NODE: classify_and_score
# ======================================================================


async def classify_and_score_node(state: GraphState) -> dict[str, Any]:
    """Classify, score severity, extract evidence, and compute relevance.

    Behaviour depends on the run mode:
    - **adhoc** (``state.adhoc``): classify, severity H/M/L, evidence spans.
    - **vigilancia** (``state.focus == "vigilancia_news"``): relevance score.
    """
    documents = list(state.documents)
    source_metrics = {k: v.model_copy() for k, v in state.source_metrics.items()}

    if not documents:
        return {}

    is_adhoc = state.adhoc
    is_vigilancia = state.focus == "vigilancia_news"
    is_risk_batch = state.focus == "riesgos_news" and not is_adhoc

    if not is_adhoc and not is_vigilancia and not is_risk_batch:
        return {}

    # Lazy-init classifiers / scorers
    from newsradar_api.domain.usecase.capabilities import (
        RulesClassifier,
        SeverityScorer,
        EvidenceExtractor,
        process_document,
    )
    from newsradar_api.domain.usecase.relevance_scorer import RelevanceScorer

    classifier = None
    severity_scorer: SeverityScorer | None = None
    evidence_extractor: EvidenceExtractor | None = None
    relevance_scorer: RelevanceScorer | None = None
    query_type = "aras"
    query_terms: list[str] = []

    if is_adhoc:
        if state.classifier_mode == "llm":
            from newsradar_api.domain.usecase.llm_classifier import LLMClassifier
            classifier = LLMClassifier()
        else:
            classifier = RulesClassifier()
        severity_scorer = SeverityScorer()
        evidence_extractor = EvidenceExtractor()
        relevance_scorer = RelevanceScorer()

        if state.focus == "aras_news":
            query_type = "aras"
            query_terms = [state.company] if state.company else []
        elif state.focus == "riesgos_news":
            query_type = "riesgos"
            query_terms = [t.strip() for t in (state.terms or "").split(",") if t.strip()]

    # Geo-region bonus lists
    _PRIORITY_GEO = [
        "colombia", "bogotá", "bogota", "medellín", "medellin",
        "cali", "barranquilla", "cartagena",
        "panamá", "panama", "azuero", "chiriquí",
        "el salvador", "san salvador",
        "guatemala", "ciudad de guatemala",
    ]
    _LATAM_GEO = [
        "perú", "peru", "ecuador", "chile", "méxico", "mexico",
        "brasil", "argentina", "costa rica", "honduras",
        "latinoamérica", "latinoamerica", "latam",
        "centroamérica", "centroamerica",
    ]

    for doc in documents:
        sid = doc.source_id
        try:
            if is_adhoc and classifier and severity_scorer and evidence_extractor:
                qt = doc.query_type or query_type

                # 1. Classify
                cls_result = classifier.classify(
                    text=doc.text, title=doc.title, query_type=qt
                )
                if qt == "aras":
                    doc.category = cls_result.label
                else:
                    doc.risk_type = cls_result.label
                doc.confidence = cls_result.confidence
                doc.matched_keywords = cls_result.matched_keywords
                doc.classifier_mode = state.classifier_mode

                # 2. Severity
                sev_result = severity_scorer.score(text=doc.text, title=doc.title)
                doc.severity = sev_result.severity
                doc.severity_confidence = sev_result.confidence

                # 3. Evidence
                matched_terms = cls_result.matched_keywords
                if matched_terms:
                    doc.evidence_spans = evidence_extractor.extract(
                        text=doc.text, matched_terms=matched_terms
                    )

                # 4. Relevance score with geo bonus
                geo_bonus = 0
                text_lower = (doc.text[:2000] + " " + doc.title).lower()
                if any(s in text_lower for s in _PRIORITY_GEO):
                    geo_bonus = 15
                elif any(s in text_lower for s in _LATAM_GEO):
                    geo_bonus = 8

                if relevance_scorer is None:
                    relevance_scorer = RelevanceScorer()
                score = relevance_scorer.score(doc=doc, query_terms=query_terms)
                matched_count = len(getattr(doc, "query_terms", []) or [])
                if matched_count == 0 and query_terms:
                    score = min(score, 30)
                doc.relevance_score = min(score + geo_bonus, 100)

                # 5. Update source metrics
                if sid in source_metrics:
                    source_metrics[sid].classified_ok += 1
                    if sev_result.severity == "H":
                        source_metrics[sid].severity_h += 1
                    elif sev_result.severity == "M":
                        source_metrics[sid].severity_m += 1
                    else:
                        source_metrics[sid].severity_l += 1

            elif is_vigilancia or is_risk_batch:
                if relevance_scorer is None:
                    relevance_scorer = RelevanceScorer()
                vig_terms = list(getattr(doc, "query_terms", []) or _query_terms_list(state.terms))
                if is_vigilancia and not getattr(doc, "matched_keywords", None) and vig_terms:
                    doc.matched_keywords = vig_terms[:5]
                if is_risk_batch:
                    analysis = process_document(doc.text, doc.title, query_type="riesgos")
                    doc.risk_type = analysis.get("category")
                    doc.materialized_events = analysis.get("events", [])
                    doc.matched_keywords = analysis.get("matched_keywords", [])
                    doc.confidence = analysis.get("confidence")
                    doc.classifier_mode = state.classifier_mode
                score = relevance_scorer.score(doc=doc, query_terms=vig_terms)
                matched_count = len(getattr(doc, "query_terms", []) or [])
                if matched_count == 0 and vig_terms:
                    score = min(score, 25)

                text_lower = (doc.text[:2000] + " " + doc.title).lower()
                if any(s in text_lower for s in _PRIORITY_GEO):
                    score += 10
                elif any(s in text_lower for s in _LATAM_GEO):
                    score += 5
                doc.relevance_score = min(score, 100)

                if sid in source_metrics:
                    source_metrics[sid].classified_ok += 1

        except Exception as exc:
            logger.error("[%s] classify_and_score error for %s: %s", sid, doc.url, exc)
            doc.category = "error"
            doc.severity = None
            doc.severity_confidence = None
            doc.evidence_spans = []
            if sid in source_metrics:
                source_metrics[sid].classified_error += 1

    logger.info("classify_and_score complete: %d documents processed", len(documents))

    # --- LLM re-ranking ---
    if state.classifier_mode == "llm" and documents and (is_adhoc or is_vigilancia or is_risk_batch):
        from newsradar_api.domain.usecase.llm_reranker import LLMReranker

        reranker = LLMReranker(flow=state.focus)
        if reranker._prompts:
            if state.focus == "aras_news":
                qctx = f"Búsqueda ARAS para empresa: {state.company or 'N/A'}"
            elif state.focus == "riesgos_news":
                qctx = f"Búsqueda de Riesgos Emergentes con términos: {state.terms or 'N/A'}"
            elif state.focus == "vigilancia_news":
                qctx = f"Vigilancia Tecnológica — temas: {state.terms or 'todos los grupos'}"
            else:
                qctx = "Búsqueda general de noticias"

            logger.info("LLM re-ranking %d documents...", len(documents))
            for doc in documents:
                heuristic = doc.relevance_score or 0
                llm_score, reasoning = reranker.rerank(doc, qctx, heuristic)
                doc.relevance_score = llm_score
            logger.info("LLM re-ranking complete")

    return {"documents": documents, "source_metrics": source_metrics}


# ======================================================================
# NODE: persist_and_report
# ======================================================================


async def persist_and_report_node(state: GraphState) -> dict[str, Any]:
    """Persist documents as JSONL and generate a run report."""
    out_dir = Path(state.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save documents as JSONL
    if state.documents:
        docs_path = out_dir / f"documents_{state.run_id}.jsonl"
        with open(docs_path, "w", encoding="utf-8") as f:
            for doc in state.documents:
                f.write(doc.model_dump_json() + "\n")
        logger.info("Saved %d documents to %s", len(state.documents), docs_path)

    # Save run report
    from newsradar_api.domain.model.pipeline_models import RunMetrics

    finished_at = datetime.utcnow().isoformat()
    started = datetime.fromisoformat(state.started_at)
    duration = (datetime.utcnow() - started).total_seconds()

    total_discovered = sum(m.discovered for m in state.source_metrics.values())
    total_fetched = sum(m.fetched_ok for m in state.source_metrics.values())
    total_ok = sum(m.text_ok for m in state.source_metrics.values())
    total_errors = sum(m.errors for m in state.source_metrics.values())
    total_dupes = sum(m.dupes for m in state.source_metrics.values())
    total_skipped = sum(m.skipped for m in state.source_metrics.values())

    metrics = RunMetrics(
        run_id=state.run_id,
        started_at=state.started_at,
        finished_at=finished_at,
        duration_seconds=round(duration, 2),
        total_sources=len(state.selected_sources),
        total_discovered=total_discovered,
        total_fetched=total_fetched,
        total_ok=total_ok,
        total_skipped=total_skipped,
        total_errors=total_errors,
        total_dupes=total_dupes,
        by_source=state.source_metrics,
    )

    report_path = out_dir / f"report_{state.run_id}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(metrics.model_dump_json(indent=2))
    logger.info("Saved report to %s", report_path)

    execution_id = None
    try:
        from newsradar_api.shared_kernel.documents.persistence import (
            persist_pipeline_results,
        )

        execution_id = await persist_pipeline_results(state, metrics)
    except Exception:
        logger.exception("Failed to persist pipeline results to database")

    logger.info(
        "Run complete: %d documents, %d sources processed",
        len(state.documents), len(state.selected_sources),
    )
    payload: dict[str, Any] = {"metrics": metrics}
    if execution_id:
        payload["execution_id"] = execution_id
    return payload
