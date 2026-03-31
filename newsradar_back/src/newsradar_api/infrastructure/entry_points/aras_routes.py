"""ARAS REST endpoints — live Google News search + PostgreSQL.

Enhanced with LLMClassifier, LLMReranker, ArasFilter, NITResolver,
and ExcelExporter integration.

Validates: Requirements 1.1-1.5, 2.1-2.5, 16.1-16.5, 20.1-20.3
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.dtos import (
    ArasSearchRequest,
    ArasSearchResponse,
    DocumentResult,
)
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter
from newsradar_api.domain.usecase.news_search import search_aras, search_google_news, _build_query
from newsradar_api.domain.usecase.capabilities import (
    RulesClassifier,
    SeverityScorer,
    EvidenceExtractor,
    process_document,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy singletons
_llm_classifier = None
_llm_reranker = None
_nit_resolver = None
_excel_exporter = None


def _get_llm_classifier():
    global _llm_classifier
    if _llm_classifier is None:
        from newsradar_api.domain.usecase.llm_classifier import LLMClassifier
        _llm_classifier = LLMClassifier()
    return _llm_classifier


def _get_llm_reranker(flow: str = "aras_news"):
    global _llm_reranker
    if _llm_reranker is None:
        from newsradar_api.domain.usecase.llm_reranker import LLMReranker
        _llm_reranker = LLMReranker(flow=flow)
    return _llm_reranker


def _get_nit_resolver():
    global _nit_resolver
    if _nit_resolver is None:
        from newsradar_api.domain.usecase.nit_resolver import NITResolver
        _nit_resolver = NITResolver()
    return _nit_resolver


def _get_excel_exporter():
    global _excel_exporter
    if _excel_exporter is None:
        from newsradar_api.domain.usecase.excel_exporter import ExcelExporter
        _excel_exporter = ExcelExporter()
    return _excel_exporter


@router.post("/search", response_model=ArasSearchResponse)
async def search_aras_endpoint(
    request: ArasSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> ArasSearchResponse:
    logger.info(
        "POST /api/aras/search — company=%s, nit=%s, classifier=%s",
        request.company, request.nit, request.classifier,
    )

    run_id = str(uuid.uuid4())[:8]
    company = request.company
    classifier_mode = request.classifier or "rules"

    # Req 20.1-20.3: Resolve NIT to company name if provided
    if request.nit and not company:
        try:
            resolver = _get_nit_resolver()
            resolved = resolver.resolve(request.nit)
            if resolved:
                company = resolved
                logger.info("NIT %s resolved to: %s", request.nit, company)
        except Exception as exc:
            logger.warning("NIT resolution failed: %s", exc)

    if not company and not request.nit:
        return ArasSearchResponse(run_id=run_id, total_documents=0, total_classified=0, results=[])

    # Build query and search Google News
    search_company = company or request.nit or ""
    query = _build_query(company=search_company,
                         date_from=request.date_from.isoformat() if request.date_from else None,
                         date_to=request.date_to.isoformat() if request.date_to else None)
    entries = await search_google_news(query, max_items=30)

    # Req 16.1-16.5: Apply ArasFilter for metadata matching
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

    if search_company and queue_items:
        from newsradar_api.domain.usecase.aras_filter import filter_aras_candidates
        filter_result = filter_aras_candidates(
            queue_items, search_company,
            date_from=request.date_from.isoformat() if request.date_from else None,
            date_to=request.date_to.isoformat() if request.date_to else None,
        )
        # Rebuild entries from filtered candidates, preserving order
        filtered_urls = {c.url for c in filter_result.candidates}
        entries = [e for e in entries if e.get("url", "") in filtered_urls]

    # Process each entry with classification + scoring
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
            "category": request.risk_category or "General",
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
                    cr = clf.classify(text, title, query_type="aras")
                    r["category"] = cr.label.replace("_", " ").title() if cr.label != "otro" else r["category"]
                    r["confidence"] = round(cr.confidence, 2)
                    r["matched_keywords"] = cr.matched_keywords
                except Exception as exc:
                    logger.warning("LLM classify failed, using rules: %s", exc)
                    analysis = process_document(text, title, query_type="aras")
                    r["category"] = analysis["category"] or r["category"]
                    r["confidence"] = analysis["confidence"]
                    r["matched_keywords"] = analysis["matched_keywords"]
            else:
                analysis = process_document(text, title, query_type="aras")
                r["category"] = analysis["category"] or r["category"]
                r["severity"] = analysis["severity"]
                r["evidence"] = analysis["evidence"]
                r["confidence"] = analysis["confidence"]
                r["matched_keywords"] = analysis["matched_keywords"]

            # Severity scoring (always applied)
            if r["severity"] is None:
                scorer = SeverityScorer()
                sr = scorer.score(text, title)
                r["severity"] = sr.severity
                r["evidence"] = [s.text for s in sr.evidence_spans]

            # Req 2.1-2.5: LLM reranking when classifier_mode="llm"
            if classifier_mode == "llm":
                try:
                    reranker = _get_llm_reranker(flow="aras_news")

                    class _DocProxy:
                        def __init__(self, e):
                            self.title = e.get("title", "")
                            self.text = e.get("summary", "")
                            self.source_id = e.get("source", "")
                            self.published_at = e.get("published_at")

                    score, reasoning = reranker.rerank(
                        _DocProxy(entry), query_context=search_company, heuristic_score=50,
                    )
                    r["relevance_score"] = score
                except Exception as exc:
                    logger.warning("LLM rerank failed: %s", exc)

            if r["category"] and r["category"] != "General":
                classified_count += 1

        results.append(DocumentResult(**r))

    # Also check DB for previously saved results
    db = DBAdapter(session)
    db_docs = await db.search_documents(
        search_type="aras", company=request.company, nit=request.nit,
        risk_category=request.risk_category,
        date_from=request.date_from, date_to=request.date_to,
    )

    seen_urls: set[str] = {r.url for r in results if r.url}
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

    # Req 12.1-12.6: Generate Excel export
    excel_url = None
    if results:
        try:
            exporter = _get_excel_exporter()
            from newsradar_api.domain.model.pipeline_models import Document as PipelineDoc
            from datetime import datetime as dt
            import hashlib

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

            out_path = Path(f"/tmp/newsradar_exports/{run_id}_aras.xlsx")
            exporter.export(docs_for_export, out_path, metadata={
                "run_id": run_id,
                "empresa_o_términos": search_company,
                "total_documentos": len(results),
                "total_clasificados": classified_count,
            })
            excel_url = f"/api/export/download/{run_id}_aras.xlsx"
        except Exception as exc:
            logger.warning("Excel export failed: %s", exc)

    return ArasSearchResponse(
        run_id=run_id,
        total_documents=len(results),
        total_classified=classified_count,
        results=results,
        excel_url=excel_url,
    )
