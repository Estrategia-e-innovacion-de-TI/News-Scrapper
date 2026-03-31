"""Riesgos Emergentes REST endpoints — live Google News search + PostgreSQL.

Enhanced with RiesgosFilter, PresetsLoader, LLMClassifier, LLMReranker.

Validates: Requirements 1.1-1.5, 2.1-2.5, 17.1-17.3, 21.1-21.3
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime as dt
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.dtos import (
    RiesgosSearchRequest,
    RiesgosSearchResponse,
    DocumentResult,
)
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter
from newsradar_api.domain.usecase.news_search import search_google_news, _build_query
from newsradar_api.domain.usecase.capabilities import (
    SeverityScorer,
    process_document,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy singletons
_llm_classifier = None
_llm_reranker = None
_excel_exporter = None


def _get_llm_classifier():
    global _llm_classifier
    if _llm_classifier is None:
        from newsradar_api.domain.usecase.llm_classifier import LLMClassifier
        _llm_classifier = LLMClassifier()
    return _llm_classifier


def _get_llm_reranker():
    global _llm_reranker
    if _llm_reranker is None:
        from newsradar_api.domain.usecase.llm_reranker import LLMReranker
        _llm_reranker = LLMReranker(flow="riesgos_news")
    return _llm_reranker


def _get_excel_exporter():
    global _excel_exporter
    if _excel_exporter is None:
        from newsradar_api.domain.usecase.excel_exporter import ExcelExporter
        _excel_exporter = ExcelExporter()
    return _excel_exporter


def _resolve_terms(terms: list[str] | None, terms_preset: str | None) -> list[str]:
    """Resolve search terms from explicit list and/or preset (Req 21.1-21.3)."""
    search_terms = list(terms or [])

    if terms_preset:
        try:
            from newsradar_api.domain.usecase.presets_loader import resolve_preset, merge_terms
            preset_terms = resolve_preset(terms_preset)
            search_terms = merge_terms(search_terms or None, preset_terms)
        except KeyError as exc:
            logger.warning("Preset resolution failed: %s", exc)
            # Fall back to inline presets
            from newsradar_api.domain.usecase.news_search import RISK_PRESETS
            if terms_preset in RISK_PRESETS:
                search_terms.extend(RISK_PRESETS[terms_preset])
        except Exception as exc:
            logger.warning("Preset loading failed: %s", exc)
            from newsradar_api.domain.usecase.news_search import RISK_PRESETS
            if terms_preset in RISK_PRESETS:
                search_terms.extend(RISK_PRESETS[terms_preset])

    return search_terms


@router.post("/search", response_model=RiesgosSearchResponse)
async def search_riesgos_endpoint(
    request: RiesgosSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> RiesgosSearchResponse:
    logger.info(
        "POST /api/riesgos/search — terms=%s, preset=%s, classifier=%s",
        request.terms, request.terms_preset, request.classifier,
    )

    run_id = str(uuid.uuid4())[:8]
    classifier_mode = request.classifier or "rules"

    # Req 21.1-21.3: Resolve terms from preset
    search_terms = _resolve_terms(request.terms, request.terms_preset)

    if not search_terms:
        return RiesgosSearchResponse(
            run_id=run_id, total_documents=0, total_classified=0, results=[],
        )

    # Search Google News
    query = _build_query(
        terms=search_terms,
        date_from=request.date_from.isoformat() if request.date_from else None,
        date_to=request.date_to.isoformat() if request.date_to else None,
    )
    entries = await search_google_news(query, max_items=30)

    # Req 17.1-17.3: Apply RiesgosFilter for metadata matching
    from newsradar_api.domain.model.pipeline_models import QueueItem, FetchMethod
    queue_items = [
        QueueItem(
            source_id="google_news",
            url=e.get("url", ""),
            source_url="google_news_rss",
            fetch_method=FetchMethod.HTTP,
            title=e.get("title", ""),
            published_at=e.get("published_at"),
            snippet=e.get("summary", ""),
        )
        for e in entries
    ]

    if queue_items:
        from newsradar_api.domain.usecase.riesgos_filter import filter_riesgos_candidates
        candidates = filter_riesgos_candidates(
            queue_items, search_terms,
            date_from=request.date_from.isoformat() if request.date_from else None,
            date_to=request.date_to.isoformat() if request.date_to else None,
        )
        filtered_urls = {c.url for c in candidates}
        # Keep all entries if filter returns nothing (no metadata match)
        if filtered_urls:
            entries = [e for e in entries if e.get("url", "") in filtered_urls]

    category = (
        request.terms_preset.replace("_", " ").title()
        if request.terms_preset
        else "Riesgo Emergente"
    )

    # Process each entry
    results: list[DocumentResult] = []
    classified_count = 0

    for entry in entries:
        text = entry.get("summary", "")
        title = entry.get("title", "")

        r = {
            "title": title,
            "source": entry.get("source", ""),
            "published_at": entry.get("published_at"),
            "url": entry.get("url", ""),
            "summary": text,
            "category": category,
            "severity": None,
            "evidence": [],
            "classifier_mode": classifier_mode,
            "confidence": None,
            "matched_keywords": [],
            "events": [],
            "relevance_score": None,
        }

        if text:
            # Req 1.1-1.5: Use LLM or rules classifier
            if classifier_mode == "llm":
                try:
                    clf = _get_llm_classifier()
                    cr = clf.classify(text, title, query_type="riesgos")
                    r["category"] = cr.label.replace("_", " ").title() if cr.label != "otro" else r["category"]
                    r["confidence"] = round(cr.confidence, 2)
                    r["matched_keywords"] = cr.matched_keywords
                except Exception as exc:
                    logger.warning("LLM classify failed, using rules: %s", exc)
                    analysis = process_document(text, title, query_type="riesgos")
                    r["category"] = analysis["category"] or r["category"]
                    r["confidence"] = analysis["confidence"]
                    r["matched_keywords"] = analysis["matched_keywords"]
                    r["events"] = analysis["events"]
            else:
                analysis = process_document(text, title, query_type="riesgos")
                r["category"] = analysis["category"] or r["category"]
                r["severity"] = analysis["severity"]
                r["evidence"] = analysis["evidence"]
                r["confidence"] = analysis["confidence"]
                r["matched_keywords"] = analysis["matched_keywords"]
                r["events"] = analysis["events"]

            # Severity scoring
            if r["severity"] is None:
                scorer = SeverityScorer()
                sr = scorer.score(text, title)
                r["severity"] = sr.severity
                r["evidence"] = [s.text for s in sr.evidence_spans]

            # Req 2.1-2.5: LLM reranking
            if classifier_mode == "llm":
                try:
                    reranker = _get_llm_reranker()

                    class _DocProxy:
                        def __init__(self, e):
                            self.title = e.get("title", "")
                            self.text = e.get("summary", "")
                            self.source_id = e.get("source", "")
                            self.published_at = e.get("published_at")

                    terms_str = ", ".join(search_terms[:5])
                    score, reasoning = reranker.rerank(
                        _DocProxy(entry), query_context=terms_str, heuristic_score=50,
                    )
                    r["relevance_score"] = score
                except Exception as exc:
                    logger.warning("LLM rerank failed: %s", exc)

            if r["category"] and r["category"] != category:
                classified_count += 1

        results.append(DocumentResult(**r))

    # Check DB for previously saved results
    db = DBAdapter(session)
    db_docs = await db.search_documents(
        search_type="riesgos", terms=request.terms,
        terms_preset=request.terms_preset,
        date_from=request.date_from, date_to=request.date_to,
    )

    seen_urls: set[str] = {r_item.url for r_item in results if r_item.url}
    for d in db_docs:
        url = d.url or ""
        if url and url not in seen_urls:
            seen_urls.add(url)
            results.append(DocumentResult(
                title=d.title, source=d.source_id, published_at=d.published_at,
                url=d.url, summary=d.excerpt or "",
                category=d.category, severity=d.severity,
                evidence=[],
            ))

    # Generate Excel export
    excel_url = None
    if results:
        try:
            exporter = _get_excel_exporter()
            from newsradar_api.domain.model.pipeline_models import Document as PipelineDoc

            docs_for_export = []
            for r_item in results:
                docs_for_export.append(PipelineDoc(
                    run_id=run_id,
                    source_id=r_item.source or "unknown",
                    title=r_item.title or "",
                    url=r_item.url or "",
                    text=r_item.summary or "",
                    excerpt=r_item.summary[:200] if r_item.summary else "",
                    hash=hashlib.sha256((r_item.url or r_item.title or "").encode()).hexdigest()[:64],
                    fetch_method="http",
                    fetched_at=dt.utcnow().isoformat(),
                    published_at=r_item.published_at.isoformat() if r_item.published_at else None,
                    category=r_item.category,
                    severity=r_item.severity,
                ))

            out_path = Path(f"/tmp/newsradar_exports/{run_id}_riesgos.xlsx")
            exporter.export(docs_for_export, out_path, metadata={
                "run_id": run_id,
                "empresa_o_términos": ", ".join(search_terms[:5]),
                "total_documentos": len(results),
                "total_clasificados": classified_count,
            })
            excel_url = f"/api/export/download/{run_id}_riesgos.xlsx"
        except Exception as exc:
            logger.warning("Excel export failed: %s", exc)

    return RiesgosSearchResponse(
        run_id=run_id,
        total_documents=len(results),
        total_classified=classified_count,
        results=results,
        excel_url=excel_url,
    )
