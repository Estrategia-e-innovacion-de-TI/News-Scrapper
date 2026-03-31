"""Persistence helpers for executions, sources, documents, and scores."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from newsradar_api.domain.model.pipeline_models import Document as PipelineDocument
from newsradar_api.domain.model.pipeline_models import GraphState, RunMetrics
from newsradar_api.infrastructure.driven_adapters.database import async_session
from newsradar_api.infrastructure.driven_adapters.db_models import (
    Document,
    DocumentScore,
    DocumentTopic,
    EvidenceSpan,
    Execution,
    ExecutionSource,
    PipelineRun,
    SourceCatalogEntry,
)


FLOW_MAP = {
    "vigilancia_news": "tech_watch",
    "riesgos_news": "risk_mapping",
    "aras_news": "aras_search",
}

SOURCE_TYPE_MAP = {
    "rss": "rss",
    "scrape": "scraped_page",
    "pdf": "pdf",
    "query": "query",
    "custom": "institutional_report",
}


def resolve_business_flow(state: GraphState) -> str:
    if state.adhoc:
        return "aras_search"
    return FLOW_MAP.get(state.focus or "", "tech_watch")


def resolve_source_type(source_id: str, state: GraphState) -> str | None:
    source = next((item for item in state.selected_sources if item.source_id == source_id), None)
    if source is None:
        return None
    return SOURCE_TYPE_MAP.get(source.type, source.type)


def parse_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _serialize_query_range(state: GraphState) -> dict[str, str]:
    payload: dict[str, str] = {}
    if state.date_from:
        payload["date_from"] = state.date_from
    if state.date_to:
        payload["date_to"] = state.date_to
    return payload


def _score_rows(doc: PipelineDocument, execution_id) -> list[DocumentScore]:
    rows: list[DocumentScore] = []
    if doc.relevance_score is not None:
        rows.append(
            DocumentScore(
                execution_id=execution_id,
                score_type="relevance",
                score=float(doc.relevance_score),
                prompt_version="heuristic_v1",
                reasoning="Pipeline relevance score",
            )
        )
    if doc.severity_confidence is not None:
        rows.append(
            DocumentScore(
                execution_id=execution_id,
                score_type="severity_confidence",
                score=float(doc.severity_confidence),
                prompt_version="severity_rules_v1",
                reasoning="Severity scoring confidence",
            )
        )
    if doc.confidence is not None:
        rows.append(
            DocumentScore(
                execution_id=execution_id,
                score_type="classification_confidence",
                score=float(doc.confidence),
                prompt_version="classifier_v1",
                reasoning="Classification confidence",
            )
        )
    return rows


def _topic_rows(doc: PipelineDocument) -> list[DocumentTopic]:
    rows: list[DocumentTopic] = []
    if doc.category:
        rows.append(
            DocumentTopic(
                topic_type="category",
                value=doc.category,
                confidence=doc.confidence,
                source_method=doc.classifier_mode or "rules",
            )
        )
    if doc.risk_type:
        rows.append(
            DocumentTopic(
                topic_type="risk",
                value=doc.risk_type,
                confidence=doc.confidence,
                source_method=doc.classifier_mode or "rules",
            )
        )
    for keyword in doc.matched_keywords or []:
        rows.append(
            DocumentTopic(
                topic_type="keyword",
                value=keyword,
                confidence=doc.confidence,
                source_method=doc.classifier_mode or "rules",
            )
        )
    return rows


async def persist_pipeline_results(state: GraphState, metrics: RunMetrics) -> str | None:
    """Persist pipeline execution metadata, documents, and scoring traces."""
    business_flow = resolve_business_flow(state)
    source_metrics = state.source_metrics or {}
    document_hashes = [doc.hash for doc in state.documents if doc.hash]

    async with async_session() as session:
        execution_stmt = select(Execution).where(Execution.run_key == state.run_id)
        execution = (await session.execute(execution_stmt)).scalar_one_or_none()
        finished_at = parse_dt(metrics.finished_at) or datetime.now(timezone.utc)
        started_at = parse_dt(state.started_at) or datetime.now(timezone.utc)
        if execution is None:
            execution = Execution(
                run_key=state.run_id,
                business_flow=business_flow,
                trigger_type="adhoc" if state.adhoc else "manual",
                source_scope=state.focus,
                status="completed",
                metrics_json=metrics.model_dump(mode="json"),
                config_json={
                    "catalog_path": state.catalog_path,
                    "days": state.days,
                    "focus": state.focus,
                    "adhoc": state.adhoc,
                    "classifier_mode": state.classifier_mode,
                },
                started_at=started_at,
                finished_at=finished_at,
            )
            session.add(execution)
            await session.flush()
        else:
            execution.business_flow = business_flow
            execution.status = "completed"
            execution.source_scope = state.focus
            execution.metrics_json = metrics.model_dump(mode="json")
            execution.finished_at = finished_at

        pipeline_run_stmt = select(PipelineRun).where(PipelineRun.run_id == state.run_id)
        pipeline_run = (await session.execute(pipeline_run_stmt)).scalar_one_or_none()
        if pipeline_run is not None:
            pipeline_run.finished_at = finished_at
            pipeline_run.duration_seconds = metrics.duration_seconds
            pipeline_run.total_sources = metrics.total_sources
            pipeline_run.total_discovered = metrics.total_discovered
            pipeline_run.total_fetched = metrics.total_fetched
            pipeline_run.total_ok = metrics.total_ok
            pipeline_run.total_errors = metrics.total_errors
            pipeline_run.total_dupes = metrics.total_dupes

        for source in state.selected_sources:
            source_entry_stmt = select(SourceCatalogEntry).where(
                SourceCatalogEntry.source_id == source.source_id
            )
            source_entry = (await session.execute(source_entry_stmt)).scalar_one_or_none()
            if source_entry is None:
                source_entry = SourceCatalogEntry(source_id=source.source_id)
                session.add(source_entry)
            source_entry.name = source.name
            source_entry.business_flow = business_flow
            source_entry.source_type = SOURCE_TYPE_MAP.get(source.type, source.type)
            source_entry.enabled = source.enabled
            source_entry.config_path = str(state.catalog_path)
            source_entry.config_json = source.model_dump(mode="json")

        existing_docs: dict[str, Document] = {}
        if document_hashes:
            result = await session.execute(select(Document).where(Document.hash.in_(document_hashes)))
            existing_docs = {doc.hash: doc for doc in result.scalars().all()}

        for source_id, metric in source_metrics.items():
            stmt = select(ExecutionSource).where(
                ExecutionSource.execution_id == execution.id,
                ExecutionSource.source_id == source_id,
            )
            source_row = (await session.execute(stmt)).scalar_one_or_none()
            if source_row is None:
                source_row = ExecutionSource(
                    execution_id=execution.id,
                    source_id=source_id,
                    source_type=resolve_source_type(source_id, state),
                )
                session.add(source_row)
            source_row.status = "completed"
            source_row.discovered = metric.discovered
            source_row.fetched_ok = metric.fetched_ok
            source_row.text_ok = metric.text_ok
            source_row.dupes = metric.dupes
            source_row.skipped = metric.skipped
            source_row.errors = metric.errors
            source_row.classified_ok = metric.classified_ok
            source_row.classified_error = metric.classified_error
            source_row.severity_h = metric.severity_h
            source_row.severity_m = metric.severity_m
            source_row.severity_l = metric.severity_l
            source_row.matched_candidates = metric.matched_candidates
            source_row.selected_candidates = metric.selected_candidates
            source_row.avg_text_len = metric.avg_text_len
            source_row.errors_by_type = metric.errors_by_type

        for doc in state.documents:
            db_doc = existing_docs.get(doc.hash)
            is_new = db_doc is None
            if db_doc is None:
                db_doc = Document(
                    hash=doc.hash,
                    run_id=state.run_id,
                    source_id=doc.source_id,
                    title=doc.title,
                    url=doc.url,
                    fetched_at=parse_dt(doc.fetched_at) or finished_at,
                    text=doc.text,
                )
                session.add(db_doc)
                await session.flush()
                existing_docs[doc.hash] = db_doc

            db_doc.execution_id = execution.id
            db_doc.run_id = state.run_id
            db_doc.business_flow = business_flow
            db_doc.source_id = doc.source_id
            db_doc.source_type = resolve_source_type(doc.source_id, state)
            db_doc.pipeline_class = doc.pipeline_class
            db_doc.focus = doc.focus or ([state.focus] if state.focus else [])
            db_doc.title = doc.title
            db_doc.url = doc.url
            db_doc.canonical_url = doc.canonical_url
            db_doc.source_url = doc.source_url
            db_doc.published_at = parse_dt(doc.published_at)
            db_doc.fetched_at = parse_dt(doc.fetched_at) or finished_at
            db_doc.language = doc.language
            db_doc.text = doc.text
            db_doc.excerpt = doc.excerpt
            db_doc.raw_len = doc.raw_len
            db_doc.text_len = doc.text_len
            db_doc.text_capped = doc.text_capped
            db_doc.fetch_method = doc.fetch_method
            db_doc.status = doc.status
            db_doc.origin = doc.origin
            db_doc.query_type = doc.query_type or (
                "aras" if state.adhoc and (state.company or state.nit) else "risk_terms" if state.adhoc else None
            )
            db_doc.query_terms = doc.query_terms or (
                [state.company] if state.company else [state.terms] if state.terms else []
            )
            db_doc.query_range = doc.query_range or _serialize_query_range(state)
            db_doc.category = doc.category
            db_doc.risk_type = doc.risk_type
            db_doc.classifier_mode = doc.classifier_mode or state.classifier_mode
            db_doc.confidence = doc.confidence
            db_doc.matched_keywords = doc.matched_keywords
            db_doc.materialized_events = doc.materialized_events
            db_doc.severity = doc.severity
            db_doc.severity_confidence = doc.severity_confidence
            db_doc.relevance_score = doc.relevance_score

            for score_row in _score_rows(doc, execution.id):
                score_row.document_id = db_doc.id
                session.add(score_row)

            if is_new:
                for span in doc.evidence_spans or []:
                    session.add(
                        EvidenceSpan(
                            document_id=db_doc.id,
                            text=span.text,
                            start_offset=span.start_offset,
                            end_offset=span.end_offset,
                            matched_term=span.matched_term,
                        )
                    )
                for topic_row in _topic_rows(doc):
                    topic_row.document_id = db_doc.id
                    session.add(topic_row)

        await session.commit()
        return str(execution.id)
