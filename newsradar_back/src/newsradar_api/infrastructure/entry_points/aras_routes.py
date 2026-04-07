"""ARAS/Riesgos ad-hoc REST endpoints with audit persistence."""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.domain.model.dtos import (
    ArasSearchRequest,
    ArasSearchResponse,
    DocumentResult,
)
from newsradar_api.domain.usecase.capabilities import SeverityScorer, process_document
from newsradar_api.domain.usecase.news_search import _build_query, search_google_news
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter
from newsradar_api.infrastructure.driven_adapters.db_models import ExportAudit, SearchAudit

logger = logging.getLogger(__name__)
router = APIRouter()
EXPORT_DIR = Path(gettempdir()) / "newsradar_exports"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


GOOGLE_NEWS_ADHOC_MAX_ITEMS = _env_int("NEWSRADAR_GOOGLE_NEWS_ADHOC_MAX_ITEMS", 80)

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


def _search_terms(request: ArasSearchRequest) -> list[str]:
    values = []
    if request.term:
        values.append(request.term)
    values.extend(request.terms or [])
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        if clean and clean not in seen:
            seen.add(clean)
            deduped.append(clean)
    return deduped


def _serialize_result(item: DocumentResult) -> dict[str, Any]:
    return {
        "title": item.title,
        "source": item.source,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "url": item.url,
        "summary": item.summary,
        "category": item.category,
        "severity": item.severity,
        "evidence": item.evidence,
        "confidence": item.confidence,
        "matched_keywords": item.matched_keywords,
        "events": item.events,
        "relevance_score": item.relevance_score,
    }


@router.post("/search", response_model=ArasSearchResponse)
async def search_aras_endpoint(
    request: ArasSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> ArasSearchResponse:
    logger.info(
        "POST /api/aras/search - company=%s issuer=%s nit=%s term=%s classifier=%s",
        request.company,
        request.issuer,
        request.nit,
        request.term,
        request.classifier,
    )

    run_id = str(uuid.uuid4())[:8]
    classifier_mode = request.classifier or "llm"
    company = request.company or request.issuer
    search_terms = _search_terms(request)

    if request.nit and not company:
        try:
            resolved = _get_nit_resolver().resolve(request.nit)
            if resolved:
                company = resolved
        except Exception as exc:
            logger.warning("NIT resolution failed: %s", exc)

    search_label = company or request.nit or ", ".join(search_terms[:5])
    if not search_label:
        return ArasSearchResponse(run_id=run_id, total_documents=0, total_classified=0, results=[])

    query = _build_query(
        company=company or request.nit,
        terms=search_terms if not company else search_terms[:3],
        date_from=request.date_from.isoformat() if request.date_from else None,
        date_to=request.date_to.isoformat() if request.date_to else None,
    )
    entries = await search_google_news(query, max_items=GOOGLE_NEWS_ADHOC_MAX_ITEMS)

    from newsradar_api.domain.model.pipeline_models import FetchMethod, QueueItem

    queue_items = [
        QueueItem(
            source_id="google_news",
            url=entry.get("url", ""),
            source_url="google_news_rss",
            fetch_method=FetchMethod.HTTP,
            title=entry.get("title", ""),
            published_at=entry.get("published_at"),
            snippet=entry.get("summary", ""),
        )
        for entry in entries
    ]

    if company and queue_items:
        from newsradar_api.domain.usecase.aras_filter import filter_aras_candidates

        candidates = filter_aras_candidates(
            queue_items,
            company,
            date_from=request.date_from.isoformat() if request.date_from else None,
            date_to=request.date_to.isoformat() if request.date_to else None,
        )
        allowed = {candidate.url for candidate in candidates.candidates}
        entries = [entry for entry in entries if entry.get("url", "") in allowed]
    elif search_terms and queue_items:
        from newsradar_api.domain.usecase.riesgos_filter import filter_riesgos_candidates

        candidates = filter_riesgos_candidates(
            queue_items,
            search_terms,
            date_from=request.date_from.isoformat() if request.date_from else None,
            date_to=request.date_to.isoformat() if request.date_to else None,
        )
        allowed = {candidate.url for candidate in candidates}
        if allowed:
            entries = [entry for entry in entries if entry.get("url", "") in allowed]

    results: list[DocumentResult] = []
    classified_count = 0
    query_type = "aras" if company or request.nit else "riesgos"
    default_category = request.risk_category or ("General" if query_type == "aras" else "Riesgo")

    for entry in entries:
        text = entry.get("summary", "")
        title = entry.get("title", "")
        payload: dict[str, Any] = {
            "title": title,
            "source": entry.get("source", ""),
            "published_at": entry.get("published_at"),
            "url": entry.get("url", ""),
            "summary": text,
            "category": default_category,
            "severity": None,
            "evidence": [],
            "classifier_mode": classifier_mode,
            "confidence": None,
            "matched_keywords": [],
            "events": [],
            "relevance_score": None,
        }

        if text:
            if classifier_mode == "llm":
                try:
                    classifier = _get_llm_classifier()
                    result = classifier.classify(text, title, query_type=query_type)
                    payload["category"] = (
                        result.label.replace("_", " ").title()
                        if result.label != "otro"
                        else payload["category"]
                    )
                    payload["confidence"] = round(result.confidence, 2)
                    payload["matched_keywords"] = result.matched_keywords
                except Exception as exc:
                    logger.warning("LLM classify failed, using rules: %s", exc)
                    analysis = process_document(text, title, query_type=query_type)
                    payload["category"] = analysis.get("category") or payload["category"]
                    payload["confidence"] = analysis.get("confidence")
                    payload["matched_keywords"] = analysis.get("matched_keywords", [])
                    payload["events"] = analysis.get("events", [])
            else:
                analysis = process_document(text, title, query_type=query_type)
                payload["category"] = analysis.get("category") or payload["category"]
                payload["severity"] = analysis.get("severity")
                payload["evidence"] = analysis.get("evidence", [])
                payload["confidence"] = analysis.get("confidence")
                payload["matched_keywords"] = analysis.get("matched_keywords", [])
                payload["events"] = analysis.get("events", [])

            if payload["severity"] is None:
                scorer = SeverityScorer()
                severity = scorer.score(text, title)
                payload["severity"] = severity.severity
                payload["evidence"] = [span.text for span in severity.evidence_spans]

            if classifier_mode == "llm":
                try:
                    reranker = _get_llm_reranker(flow="aras_news" if query_type == "aras" else "riesgos_news")

                    class _DocProxy:
                        def __init__(self, raw: dict[str, Any]) -> None:
                            self.title = raw.get("title", "")
                            self.text = raw.get("summary", "")
                            self.source_id = raw.get("source", "")
                            self.published_at = raw.get("published_at")

                    payload["relevance_score"], _ = reranker.rerank(
                        _DocProxy(entry),
                        query_context=search_label,
                        heuristic_score=50,
                    )
                except Exception as exc:
                    logger.warning("LLM rerank failed: %s", exc)

            if payload["category"] and payload["category"] != default_category:
                classified_count += 1

        results.append(DocumentResult(**payload))

    db = DBAdapter(session)
    db_docs = await db.search_documents(
        search_type="aras" if query_type == "aras" else "risk_terms",
        company=company,
        nit=request.nit,
        risk_category=request.risk_category,
        terms=search_terms,
        date_from=request.date_from,
        date_to=request.date_to,
    )
    seen_urls = {item.url for item in results if item.url}
    for doc in db_docs:
        if doc.url and doc.url not in seen_urls:
            seen_urls.add(doc.url)
            results.append(
                DocumentResult(
                    title=doc.title,
                    source=doc.source_id,
                    published_at=doc.published_at,
                    url=doc.url,
                    summary=doc.excerpt or "",
                    category=doc.category or doc.risk_type,
                    severity=doc.severity,
                    evidence=[],
                    confidence=doc.confidence,
                    matched_keywords=doc.matched_keywords or [],
                    events=doc.materialized_events or [],
                    relevance_score=doc.relevance_score,
                )
            )

    audit = SearchAudit(
        search_kind="aras_search",
        query_mode=query_type,
        company=request.company,
        issuer=request.issuer,
        nit=request.nit,
        term=request.term,
        terms_json=search_terms,
        date_from=request.date_from,
        date_to=request.date_to,
        parameters_json=request.model_dump(mode="json"),
        results_json=[_serialize_result(item) for item in results],
        results_count=len(results),
        requested_at=datetime.now(timezone.utc),
        executed_at=datetime.now(timezone.utc),
    )
    session.add(audit)

    excel_url = None
    export_id = None
    if results:
        try:
            exporter = _get_excel_exporter()
            from newsradar_api.domain.model.pipeline_models import Document as PipelineDoc

            docs_for_export = []
            for item in results:
                docs_for_export.append(
                    PipelineDoc(
                        run_id=run_id,
                        source_id=item.source or "unknown",
                        title=item.title or "",
                        url=item.url or "",
                        text=item.summary or "",
                        excerpt=item.summary[:200] if item.summary else "",
                        hash=hashlib.sha256((item.url or item.title or "").encode()).hexdigest()[:64],
                        fetch_method="http",
                        fetched_at=datetime.utcnow().isoformat(),
                        published_at=item.published_at.isoformat() if item.published_at else None,
                        category=item.category,
                        severity=item.severity,
                        relevance_score=item.relevance_score,
                    )
                )

            out_path = EXPORT_DIR / f"{run_id}_aras.xlsx"
            exporter.export(
                docs_for_export,
                out_path,
                metadata={
                    "run_id": run_id,
                    "empresa_o_terminos": search_label,
                    "total_documentos": len(results),
                    "total_clasificados": classified_count,
                },
            )
            excel_url = f"/api/export/download/{run_id}_aras.xlsx"
            export = ExportAudit(
                export_kind="excel",
                file_name=out_path.name,
                file_path=str(out_path),
                status="created",
                row_count=len(results),
                metadata_json={"run_id": run_id, "search_label": search_label},
            )
            session.add(export)
            await session.flush()
            export_id = str(export.id) if getattr(export, "id", None) else None
            audit.export_id = getattr(export, "id", None)
        except Exception as exc:
            logger.warning("Excel export failed: %s", exc)

    await session.commit()
    audit_id = str(audit.id) if getattr(audit, "id", None) else None
    return ArasSearchResponse(
        run_id=run_id,
        search_id=audit_id,
        audit_id=audit_id,
        export_id=export_id,
        total_documents=len(results),
        total_classified=classified_count,
        results=results,
        excel_url=excel_url,
    )
