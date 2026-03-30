"""LangGraph definition for news extraction pipeline."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import StateGraph, END

from .catalog import filter_sources, load_sources
from .connectors.browser import close_browser, fetch_with_browser
from .connectors.pdf import discover_pdf_items, fetch_and_extract_pdf
from .connectors.rss import discover_rss_items
from .connectors.scrape import discover_scrape_items, fetch_article_html
from .extract.dedupe import Deduplicator, compute_content_hash
from .extract.metadata import extract_metadata
from .extract.text import clean_text, extract_text
from .report import (
    init_source_metrics,
    save_documents_jsonl,
    save_report,
    update_source_metrics,
)
from .state import (
    Document,
    ErrorType,
    FetchMethod,
    GraphState,
    ItemStatus,
    QueueItem,
    SkipReason,
    SourceConfig,
)
from .capabilities.classify import RulesClassifier
from .capabilities.evidence import EvidenceExtractor
from .capabilities.llm_classify import LLMClassifier
from .capabilities.llm_rerank import LLMReranker
from .capabilities.ranking import RelevanceScorer
from .capabilities.severity import SeverityScorer
from .utils import detect_language, rate_limiter, truncate_text

logger = logging.getLogger("news_radar.graph")

# Global deduplicator for the run
_deduplicator = Deduplicator()

_ERROR_TYPE_VALUES = {e.value for e in ErrorType}


def _safe_error_type(val: str | None) -> ErrorType:
    """Convert string to ErrorType safely, defaulting to UNKNOWN."""
    if val and val in _ERROR_TYPE_VALUES:
        return ErrorType(val)
    return ErrorType.UNKNOWN


# ============================================================================
# NODE: load_catalog
# ============================================================================
async def load_catalog_node(state: GraphState) -> dict[str, Any]:
    """Load and validate catalog."""
    logger.info(f"Loading catalog from {state.catalog_path}")
    
    defaults, sources = load_sources(state.catalog_path)
    
    logger.info(f"Loaded {len(sources)} sources from catalog")
    
    return {
        "defaults": defaults,
        "sources": sources,
    }


# ============================================================================
# NODE: select_sources
# ============================================================================
async def select_sources_node(state: GraphState) -> dict[str, Any]:
    """Filter sources based on CLI params."""
    selected = filter_sources(
        state.sources,
        only_source=state.only_source,
        include_disabled=False,
        focus=state.focus,
    )
    
    # Initialize metrics for each source
    source_metrics = {}
    for src in selected:
        source_metrics[src.source_id] = init_source_metrics(
            src.source_id,
            src.requires_playwright,
        )
    
    logger.info(f"Selected {len(selected)} enabled sources")
    
    return {
        "selected_sources": selected,
        "source_metrics": source_metrics,
    }


# ============================================================================
# NODE: discover_items
# ============================================================================
async def discover_items_node(state: GraphState) -> dict[str, Any]:
    """Discover items from all selected sources, with adhoc/candidates support."""
    queue: list[QueueItem] = []
    source_metrics = state.source_metrics.copy()
    errors = state.errors.copy()
    
    # --- Candidates ingestion mode ---
    if state.candidates_path:
        import json
        from pathlib import Path
        
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
                    )
                    queue.append(qi)
            
            logger.info(f"Loaded {len(queue)} candidates from {state.candidates_path}")
            return {"queue": queue, "source_metrics": source_metrics, "errors": errors}
    
    # --- Determine if catalog RSS/scrape discovery should be skipped ---
    # When date_to is more than 3 days in the past, RSS feeds won't have
    # historical items — skip catalog discovery and rely on Google News only.
    _skip_catalog = False
    if state.adhoc and state.date_to:
        from datetime import datetime, timedelta

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

    # --- Standard discovery ---
    if not _skip_catalog:
        for source in state.selected_sources:
            try:
                items = []
                
                if source.type == "rss":
                    items = await discover_rss_items(
                        source,
                        days=state.days,
                        max_items=state.max_items_per_source,
                    )
                elif source.type == "scrape":
                    items = await discover_scrape_items(
                        source,
                        max_items=state.max_items_per_source,
                        max_pages=2,
                    )
                elif source.type == "pdf":
                    items = await discover_pdf_items(
                        source,
                        max_items=state.max_items_per_source,
                    )
                elif source.type in ("query", "custom"):
                    item = QueueItem(
                        source_id=source.source_id,
                        url=source.base_url or "",
                        source_url=source.base_url or "",
                        fetch_method=FetchMethod.HTTP,
                        status=ItemStatus.SKIPPED,
                        error_type=ErrorType.CUSTOM_PENDING,
                        error_msg=f"Type '{source.type}' not supported in MVP",
                    )
                    items = [item]
                    logger.info(f"[{source.source_id}] Skipped: {source.type} type not supported")
                
                queue.extend(items)
                
                if source.source_id in source_metrics:
                    discovered = len([i for i in items if i.status != ItemStatus.SKIPPED])
                    skipped = len([i for i in items if i.status == ItemStatus.SKIPPED])
                    source_metrics[source.source_id] = update_source_metrics(
                        source_metrics[source.source_id],
                        discovered=discovered,
                        skipped=skipped,
                    )
                    
            except Exception as e:
                logger.error(f"[{source.source_id}] Discovery error: {e}")
                errors.append({
                    "source_id": source.source_id,
                    "phase": "discover",
                    "error": str(e),
                })
    
    # --- Ad-hoc: augment with Google News for historical coverage ---
    if state.adhoc and (state.company or state.terms):
        from .connectors.google_news import search_google_news

        terms_list = (
            [t.strip() for t in state.terms.split(",") if t.strip()]
            if state.terms
            else None
        )
        gn_items = await search_google_news(
            company=state.company,
            terms=terms_list,
            date_from=state.date_from,
            date_to=state.date_to,
            max_items=30,
        )
        if gn_items:
            queue.extend(gn_items)
            # Init metrics for google_news source
            if "google_news" not in source_metrics:
                source_metrics["google_news"] = update_source_metrics(
                    init_source_metrics("google_news", False),
                    discovered=len(gn_items),
                )
            logger.info(f"Google News augmented queue with {len(gn_items)} items")

    # --- Ad-hoc filtering (metadata-only match) ---
    if state.adhoc and state.focus == "aras_news" and state.company:
        from .adhoc.aras import build_aras_candidates
        
        pre_filter_count = len(queue)
        # Use higher topk_per_source for google_news since all items come from one source
        effective_topk = max(state.topk_per_source, 50) if any(
            i.source_id == "google_news" for i in queue
        ) else state.topk_per_source
        queue, counts_by_source = build_aras_candidates(
            queue,
            company=state.company,
            topk_per_source=effective_topk,
            max_total=state.max_candidates_total,
            date_from=state.date_from,
            date_to=state.date_to,
        )
        # Update source metrics with adhoc counts
        for sid, (matched, selected) in counts_by_source.items():
            if sid in source_metrics:
                source_metrics[sid].matched_candidates = matched
                source_metrics[sid].selected_candidates = selected
        
        logger.info(
            f"ARAS adhoc: {pre_filter_count} discovered -> "
            f"{len(queue)} candidates for '{state.company}'"
        )
    
    elif state.adhoc and state.focus == "riesgos_news" and state.terms:
        from .adhoc.riesgos import build_riesgos_candidates

        pre_filter_count = len(queue)
        # Use higher topk_per_source for google_news since all items come from one source
        effective_topk = max(state.topk_per_source, 50) if any(
            i.source_id == "google_news" for i in queue
        ) else state.topk_per_source
        queue = build_riesgos_candidates(
            queue,
            terms_str=state.terms,
            topk_per_source=effective_topk,
            max_total=state.max_candidates_total,
            date_from=state.date_from,
            date_to=state.date_to,
        )
        logger.info(
            f"Riesgos adhoc: {pre_filter_count} discovered -> "
            f"{len(queue)} candidates for terms"
        )

    logger.info(f"Total items in queue: {len(queue)}")
    
    return {
        "queue": queue,
        "source_metrics": source_metrics,
        "errors": errors,
    }


# ============================================================================
# NODE: split_lane
# ============================================================================
async def split_lane_node(state: GraphState) -> dict[str, Any]:
    """Split queue into lanes: http, browser, pdf, skipped."""
    http_queue = []
    browser_queue = []
    pdf_queue = []
    skipped_queue = []
    
    for item in state.queue:
        # Already skipped items
        if item.status == ItemStatus.SKIPPED:
            skipped_queue.append(item)
            continue
        
        # PDF items
        if item.fetch_method == FetchMethod.PDF:
            pdf_queue.append(item)
            continue
        
        # Browser required
        if item.requires_playwright and not state.no_playwright:
            browser_queue.append(item)
            continue
        
        # Browser required but disabled
        if item.requires_playwright and state.no_playwright:
            item.status = ItemStatus.SKIPPED
            item.error_type = ErrorType.DISABLED
            item.skip_reason = SkipReason.PLAYWRIGHT_DISABLED
            item.error_msg = "Playwright disabled via --no-playwright"
            skipped_queue.append(item)
            continue
        
        # Default: HTTP
        http_queue.append(item)
    
    logger.info(
        f"Split lanes: http={len(http_queue)}, browser={len(browser_queue)}, "
        f"pdf={len(pdf_queue)}, skipped={len(skipped_queue)}"
    )
    
    return {
        "http_queue": http_queue,
        "browser_queue": browser_queue,
        "pdf_queue": pdf_queue,
        "skipped_queue": skipped_queue,
    }


# ============================================================================
# NODE: fetch_content_http
# ============================================================================
async def fetch_content_http_node(state: GraphState) -> dict[str, Any]:
    """Fetch content via HTTP for items in http_queue."""
    if state.dry_run:
        logger.info("Dry run: skipping HTTP fetch")
        return {}
    
    documents = state.documents.copy()
    source_metrics = state.source_metrics.copy()
    seen_hashes = state.seen_hashes.copy()
    errors = state.errors.copy()
    
    # Get source configs for lookup
    source_map = {s.source_id: s for s in state.selected_sources}
    
    # Fallback config for candidates from search/google_news (not in catalog)
    _fallback_source = SourceConfig(
        source_id="_search",
        name="Search Candidate",
        type="scrape",
        min_text_chars=100,
        timeout_seconds=20,
    )
    
    # Debug: limit samples per source
    samples_per_source: dict[str, int] = {}
    max_samples = 3 if state.debug else 999
    
    for item in state.http_queue:
        source = source_map.get(item.source_id)
        if not source:
            if state.candidates_path or item.source_id == "google_news":
                source = _fallback_source
            else:
                continue
        
        # Debug sample limit
        samples_per_source.setdefault(item.source_id, 0)
        if state.debug and samples_per_source[item.source_id] >= max_samples:
            continue
        
        await rate_limiter.wait(item.source_id, source.rate_limit_rps)
        
        logger.debug(f"[{item.source_id}] Fetching: {item.url}")
        
        html, status, error_type = await fetch_article_html(
            item.url,
            timeout=source.timeout_seconds,
        )
        
        if error_type or not html:
            item.status = ItemStatus.ERROR
            item.error_type = _safe_error_type(error_type)
            if item.source_id in source_metrics:
                source_metrics[item.source_id] = update_source_metrics(
                    source_metrics[item.source_id],
                    errors=1,
                    error_type=error_type,
                )
            continue
        
        # Extract text and metadata
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
                source_metrics[item.source_id] = update_source_metrics(
                    source_metrics[item.source_id],
                    fetched_ok=1,
                    text_ok=1,
                    text_len=doc.text_len,
                )
        elif doc is None and item.status == ItemStatus.OK:
            # Duplicate
            if item.source_id in source_metrics:
                source_metrics[item.source_id] = update_source_metrics(
                    source_metrics[item.source_id],
                    fetched_ok=1,
                    dupes=1,
                )
    
    logger.info(f"HTTP fetch complete: {len(documents)} documents")
    
    return {
        "documents": documents,
        "source_metrics": source_metrics,
        "seen_hashes": seen_hashes,
        "errors": errors,
    }


# ============================================================================
# NODE: fetch_content_browser
# ============================================================================
async def fetch_content_browser_node(state: GraphState) -> dict[str, Any]:
    """Fetch content via Playwright for items in browser_queue."""
    if state.dry_run:
        logger.info("Dry run: skipping browser fetch")
        return {}
    
    if not state.browser_queue:
        return {}
    
    documents = state.documents.copy()
    source_metrics = state.source_metrics.copy()
    seen_hashes = state.seen_hashes.copy()
    
    source_map = {s.source_id: s for s in state.selected_sources}
    
    samples_per_source: dict[str, int] = {}
    max_samples = 3 if state.debug else 999
    
    try:
        for item in state.browser_queue:
            source = source_map.get(item.source_id)
            if not source:
                continue
            
            samples_per_source.setdefault(item.source_id, 0)
            if state.debug and samples_per_source[item.source_id] >= max_samples:
                continue
            
            await rate_limiter.wait(item.source_id, source.rate_limit_rps)
            
            logger.debug(f"[{item.source_id}] Browser fetch: {item.url}")
            
            html, status, error_type = await fetch_with_browser(
                item.url,
                timeout=source.timeout_seconds,
            )
            
            if error_type or not html:
                item.status = ItemStatus.ERROR
                item.error_type = _safe_error_type(error_type)
                source_metrics[item.source_id] = update_source_metrics(
                    source_metrics[item.source_id],
                    errors=1,
                    error_type=error_type,
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
                source_metrics[item.source_id] = update_source_metrics(
                    source_metrics[item.source_id],
                    fetched_ok=1,
                    text_ok=1,
                    text_len=doc.text_len,
                )
    finally:
        await close_browser()
    
    logger.info(f"Browser fetch complete: {len(documents)} documents")
    
    return {
        "documents": documents,
        "source_metrics": source_metrics,
        "seen_hashes": seen_hashes,
    }


# ============================================================================
# NODE: extract_pdf
# ============================================================================
async def extract_pdf_node(state: GraphState) -> dict[str, Any]:
    """Extract text from PDF items."""
    if state.dry_run:
        logger.info("Dry run: skipping PDF extraction")
        return {}
    
    if not state.pdf_queue:
        return {}
    
    documents = state.documents.copy()
    source_metrics = state.source_metrics.copy()
    seen_hashes = state.seen_hashes.copy()
    
    source_map = {s.source_id: s for s in state.selected_sources}
    
    for item in state.pdf_queue:
        source = source_map.get(item.source_id)
        if not source:
            continue
        
        logger.debug(f"[{item.source_id}] PDF extract: {item.url}")
        
        text, error_type = await fetch_and_extract_pdf(
            item.url,
            source.source_id,
            timeout=source.timeout_seconds,
            rate_limit_rps=source.rate_limit_rps,
        )
        
        if error_type or not text:
            item.status = ItemStatus.ERROR
            item.error_type = _safe_error_type(error_type) if error_type else ErrorType.PARSE
            source_metrics[item.source_id] = update_source_metrics(
                source_metrics[item.source_id],
                errors=1,
                error_type=error_type or "parse_error",
            )
            continue
        
        # Check text length
        if len(text) < source.min_text_chars:
            item.status = ItemStatus.ERROR
            item.error_type = ErrorType.EMPTY
            source_metrics[item.source_id] = update_source_metrics(
                source_metrics[item.source_id],
                errors=1,
                error_type="empty_or_thin",
            )
            continue
        
        # Dedupe
        content_hash = compute_content_hash(item.url, text)
        if content_hash in seen_hashes:
            source_metrics[item.source_id] = update_source_metrics(
                source_metrics[item.source_id],
                fetched_ok=1,
                dupes=1,
            )
            continue
        
        seen_hashes.add(content_hash)
        
        # Create document
        doc = Document(
            run_id=state.run_id,
            source_id=item.source_id,
            pipeline_class=source.pipeline_class,
            focus=source.focus,
            title=item.url.split("/")[-1],  # Use filename as title
            url=item.url,
            canonical_url=item.url,
            published_at=None,
            fetched_at=datetime.utcnow().isoformat(),
            language=detect_language(text),
            text=text,
            excerpt=truncate_text(text, 500),
            raw_len=len(text),
            text_len=len(text),
            hash=content_hash,
            fetch_method="pdf",
            status="ok",
            source_url=item.source_url,
        )
        
        documents.append(doc)
        source_metrics[item.source_id] = update_source_metrics(
            source_metrics[item.source_id],
            fetched_ok=1,
            text_ok=1,
            text_len=len(text),
        )
    
    logger.info(f"PDF extraction complete: {len(documents)} documents")
    
    return {
        "documents": documents,
        "source_metrics": source_metrics,
        "seen_hashes": seen_hashes,
    }


# ============================================================================
# NODE: persist_and_report
# ============================================================================
# ============================================================================
# NODE: classify_and_score
# ============================================================================
async def classify_and_score_node(state: GraphState) -> dict[str, Any]:
    """Classify, score severity, and extract evidence for fetched documents.

    Behaviour depends on the run mode:
    - **adhoc** (``state.adhoc == True``): classify each document, assign
      severity H/M/L, and extract evidence spans.
    - **vigilancia** (``state.focus == "vigilancia_news"``): compute a
      relevance score 0..100 for each document.

    Errors on individual documents are caught, logged, and the document is
    marked with ``category="error"`` / ``severity=None`` so the rest of the
    batch continues.
    """
    documents = state.documents.copy()
    source_metrics = state.source_metrics.copy()

    if not documents:
        return {}

    is_adhoc = state.adhoc
    is_vigilancia = state.focus == "vigilancia_news"

    # Nothing to do if neither adhoc nor vigilancia
    if not is_adhoc and not is_vigilancia:
        return {}

    # --- Lazy-init classifiers / scorers ---
    classifier: RulesClassifier | LLMClassifier | None = None
    severity_scorer: SeverityScorer | None = None
    evidence_extractor: EvidenceExtractor | None = None
    relevance_scorer: RelevanceScorer | None = None

    if is_adhoc:
        if state.classifier_mode == "llm":
            classifier = LLMClassifier()
        else:
            classifier = RulesClassifier()
        severity_scorer = SeverityScorer()
        evidence_extractor = EvidenceExtractor()
        relevance_scorer = RelevanceScorer()

        # Build query terms for relevance scoring
        if state.focus == "aras_news":
            query_type = "aras"
            query_terms = [state.company] if state.company else []
        elif state.focus == "riesgos_news":
            query_type = "riesgos"
            query_terms = [t.strip() for t in (state.terms or "").split(",") if t.strip()]
        else:
            query_type = "aras"
            query_terms = []

    for doc in documents:
        sid = doc.source_id
        try:
            if is_adhoc and classifier and severity_scorer and evidence_extractor:
                query_type = doc.query_type or "aras"

                # 1. Classify
                cls_result = classifier.classify(
                    text=doc.text,
                    title=doc.title,
                    query_type=query_type,
                )

                if query_type == "aras":
                    doc.category = cls_result.label
                else:
                    doc.risk_type = cls_result.label

                doc.materialized_events = cls_result.metadata.get("events", [])

                # 2. Severity
                sev_result = severity_scorer.score(
                    text=doc.text,
                    title=doc.title,
                    classify_result=cls_result,
                )
                doc.severity = sev_result.severity
                doc.severity_confidence = sev_result.confidence

                # 3. Evidence
                matched_terms = cls_result.metadata.get("matched_keywords", [])
                if matched_terms:
                    doc.evidence_spans = evidence_extractor.extract(
                        text=doc.text,
                        matched_terms=matched_terms,
                    )

                # 4. Relevance score (with geo bonus for priority regions)
                geo_bonus = 0
                text_lower = (doc.text[:2000] + " " + doc.title).lower()
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
                if any(signal in text_lower for signal in _PRIORITY_GEO):
                    geo_bonus = 15  # priority region
                elif any(signal in text_lower for signal in _LATAM_GEO):
                    geo_bonus = 8   # other Latam

                score = relevance_scorer.score(
                    doc=doc,
                    query_terms=query_terms,
                )
                # Penalty: if no query terms matched, cap the score
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

            elif is_vigilancia:
                # Compute heuristic relevance score
                if relevance_scorer is None:
                    relevance_scorer = RelevanceScorer()
                vig_terms = [t.strip() for t in (state.terms or "").split(",") if t.strip()]
                score = relevance_scorer.score(doc=doc, query_terms=vig_terms)

                # Vigilancia penalty: if no query terms matched in the doc,
                # the score should be very low regardless of recency/source
                matched_count = len(getattr(doc, "query_terms", []) or [])
                if matched_count == 0 and vig_terms:
                    score = min(score, 25)  # cap at 25 if zero keyword match

                # Geo bonus for priority regions
                text_lower = (doc.text[:2000] + " " + doc.title).lower()
                _P_GEO = ["colombia", "bogotá", "bogota", "medellín", "medellin",
                           "cali", "barranquilla", "cartagena",
                           "panamá", "panama", "el salvador", "san salvador",
                           "guatemala", "ciudad de guatemala"]
                _L_GEO = ["perú", "peru", "ecuador", "chile", "méxico", "mexico",
                           "brasil", "argentina", "latam", "centroamérica"]
                if any(s in text_lower for s in _P_GEO):
                    score += 10
                elif any(s in text_lower for s in _L_GEO):
                    score += 5
                doc.relevance_score = min(score, 100)

                if sid in source_metrics:
                    source_metrics[sid].classified_ok += 1

        except Exception as exc:
            logger.error(
                "[%s] classify_and_score error for %s: %s",
                sid,
                doc.url,
                exc,
            )
            doc.category = "error"
            doc.severity = None
            doc.severity_confidence = None
            doc.evidence_spans = []
            if sid in source_metrics:
                source_metrics[sid].classified_error += 1

    logger.info(
        "classify_and_score complete: %d documents processed",
        len(documents),
    )

    # --- LLM re-ranking (only when --classifier llm) ---
    if state.classifier_mode == "llm" and documents and (is_adhoc or is_vigilancia):
        reranker = LLMReranker(flow=state.focus)
        if reranker._prompts:
            # Build query context string
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
                logger.debug(
                    "  rerank: [%d->%d] %s — %s",
                    heuristic, llm_score, doc.title[:60], reasoning,
                )
            logger.info("LLM re-ranking complete")

    return {
        "documents": documents,
        "source_metrics": source_metrics,
    }


# ============================================================================
# NODE: persist_and_report
# ============================================================================
async def persist_and_report_node(state: GraphState) -> dict[str, Any]:
    """Persist documents and generate report."""
    out_dir = Path(state.out_dir)
    
    # Save documents
    if state.documents:
        save_documents_jsonl(state.documents, out_dir)
    
    # Save report
    save_report(state, out_dir)
    
    logger.info(
        f"Run complete: {len(state.documents)} documents, "
        f"{len(state.selected_sources)} sources processed"
    )
    
    return {}


# ============================================================================
# HELPER: Process HTML to Document
# ============================================================================
async def _process_html(
    html: str,
    item: QueueItem,
    source: SourceConfig,
    state: GraphState,
    seen_hashes: set[str],
    fetch_method: str = "http",
) -> Document | None:
    """Process HTML and create Document. Returns None if duplicate or error."""
    # Extract text
    text, method = extract_text(html, source.min_text_chars)
    
    if not text or len(text) < source.min_text_chars:
        item.status = ItemStatus.ERROR
        item.error_type = ErrorType.EMPTY
        return None
    
    text = clean_text(text)
    
    # Text cap
    text_capped = False
    if len(text) > state.max_text_chars:
        text = text[:state.max_text_chars]
        text_capped = True
    
    # Extract metadata
    meta = extract_metadata(html)
    
    # Use item title if available (from RSS), else extracted
    title = item.title or meta.get("title") or ""
    
    # Dedupe
    content_hash = compute_content_hash(title, text)
    if content_hash in seen_hashes:
        item.status = ItemStatus.OK  # Mark as OK but return None (dupe)
        return None
    
    # Determine provenance
    origin = "catalog"
    query_type = None
    query_terms: list[str] = []
    query_range: dict[str, str] = {}
    if state.candidates_path:
        origin = "search_ingest"
    elif state.adhoc and state.focus:
        origin = "adhoc_query"
        if state.focus == "aras_news":
            query_type = "aras"
            query_terms = [state.company] if state.company else []
        elif state.focus == "riesgos_news":
            query_type = "riesgos"
            query_terms = [t.strip() for t in (state.terms or "").split(",") if t.strip()]
        if state.date_from and state.date_to:
            query_range = {"from": state.date_from, "to": state.date_to}
    
    # Build document
    return Document(
        run_id=state.run_id,
        source_id=item.source_id,
        pipeline_class=source.pipeline_class,
        focus=source.focus,
        title=title,
        url=item.url,
        canonical_url=meta.get("canonical_url") or item.url,
        published_at=item.published_at or meta.get("published_at"),
        fetched_at=datetime.utcnow().isoformat(),
        language=detect_language(text),
        text=text,
        excerpt=truncate_text(text, 500),
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


# ============================================================================
# GRAPH BUILDER
# ============================================================================
def build_graph() -> StateGraph:
    """Build the LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("load_catalog", load_catalog_node)
    workflow.add_node("select_sources", select_sources_node)
    workflow.add_node("discover_items", discover_items_node)
    workflow.add_node("split_lane", split_lane_node)
    workflow.add_node("fetch_content_http", fetch_content_http_node)
    workflow.add_node("fetch_content_browser", fetch_content_browser_node)
    workflow.add_node("extract_pdf", extract_pdf_node)
    workflow.add_node("classify_and_score", classify_and_score_node)
    workflow.add_node("persist_and_report", persist_and_report_node)

    # Define edges
    workflow.set_entry_point("load_catalog")
    workflow.add_edge("load_catalog", "select_sources")
    workflow.add_edge("select_sources", "discover_items")
    workflow.add_edge("discover_items", "split_lane")
    workflow.add_edge("split_lane", "fetch_content_http")
    workflow.add_edge("fetch_content_http", "fetch_content_browser")
    workflow.add_edge("fetch_content_browser", "extract_pdf")
    workflow.add_edge("extract_pdf", "classify_and_score")
    workflow.add_edge("classify_and_score", "persist_and_report")
    workflow.add_edge("persist_and_report", END)

    return workflow


def compile_graph():
    """Compile the graph for execution."""
    workflow = build_graph()
    return workflow.compile()


async def run_extraction(
    catalog_path: str = "catalog.yaml",
    days: int = 7,
    max_items_per_source: int = 20,
    out_dir: str = "out",
    debug: bool = False,
    dry_run: bool = False,
    only_source: str | None = None,
    no_playwright: bool = False,
    store_raw_html: bool = False,
    # New params
    focus: str | None = None,
    adhoc: bool = False,
    company: str | None = None,
    terms: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    topk_per_source: int = 5,
    max_candidates_total: int = 50,
    candidates_path: str | None = None,
    classifier_mode: str = "rules",
    nit: str | None = None,
    terms_preset: str | None = None,
) -> GraphState:
    """Run the extraction pipeline."""
    # Reset deduplicator
    _deduplicator.clear()
    
    # Initialize state
    initial_state = GraphState(
        catalog_path=catalog_path,
        days=days,
        max_items_per_source=max_items_per_source,
        out_dir=out_dir,
        debug=debug,
        dry_run=dry_run,
        only_source=only_source,
        no_playwright=no_playwright,
        store_raw_html=store_raw_html,
        focus=focus,
        adhoc=adhoc,
        company=company,
        terms=terms,
        date_from=date_from,
        date_to=date_to,
        topk_per_source=topk_per_source,
        max_candidates_total=max_candidates_total,
        candidates_path=candidates_path,
        classifier_mode=classifier_mode,
        nit=nit,
        terms_preset=terms_preset,
    )
    
    # Compile and run
    app = compile_graph()
    
    logger.info(f"Starting extraction run {initial_state.run_id}")
    if focus:
        logger.info(f"Focus: {focus}, adhoc={adhoc}")
    
    final_state = await app.ainvoke(initial_state)
    
    return GraphState(**final_state)
