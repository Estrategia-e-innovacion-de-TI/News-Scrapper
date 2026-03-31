"""Snapshot builders backed by the shared advanced analytics engine."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from newsradar_api.infrastructure.driven_adapters.db_models import (
    Cluster,
    Document,
    LLMPrompt,
    ReportSnapshot,
    RiskReport,
    Trend,
    TrendReport,
    TrendmapSnapshot,
)
from newsradar_api.shared_kernel.bedrock import SnapshotLLMEnricher
from newsradar_api.shared_kernel.analytics import generate_report_analysis


def _document_source_kind(doc: Document) -> str:
    if doc.source_type in {"paper", "patent"}:
        return doc.source_type
    if doc.source_type in {"pdf", "institutional_report"}:
        return "paper"
    return "news"


def _window_start(window_months: int) -> datetime:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=max(window_months, 1) * 30)


def _base_document_payload(doc: Document) -> dict[str, Any]:
    published = doc.published_at or doc.fetched_at
    return {
        "id": str(doc.id),
        "title": doc.title,
        "source": doc.source_id,
        "source_type": _document_source_kind(doc),
        "date": published.isoformat() if published else None,
        "score": doc.relevance_score or 0,
        "url": doc.url,
        "summary": doc.excerpt or doc.title,
        "category": doc.category,
        "risk_type": doc.risk_type,
    }


def build_trendmap_payload(documents: list[Document], window_months: int) -> dict[str, Any]:
    analysis = generate_report_analysis(documents, "trend_mapping", window_months)
    generated_at = analysis["generated_at"]
    clusters = analysis["clusters"]

    payload = {
        "report_type": "trend_mapping",
        "generated_at": generated_at,
        "window_months": window_months,
        "version": 2,
        "meta": analysis["meta"],
        "summary": {
            **analysis["summary"],
            "executive_summary": analysis["executive_summary"],
        },
        "clusters": [
            {
                "cluster_id": cluster["cluster_id"],
                "label": cluster["label"],
                "category": cluster["category"],
                "summary": cluster["summary"],
                "keywords": cluster["keywords"],
                "relevance": cluster["relevance"],
                "item_count": cluster["item_count"],
                "impact_score": cluster["impact_score"],
                "horizon_score": cluster["horizon_score"],
                "maturity_stage": cluster["maturity_stage"],
                "direction": cluster["direction"],
                "growth_ratio": cluster["growth_ratio"],
                "hull_polygon": cluster["hull_polygon"],
                "articles": cluster["articles"],
                "top_documents": cluster["top_documents"],
                "source_mix": cluster["source_mix"],
                "executive_takeaway": cluster["executive_takeaway"],
                "coords": cluster["coords"],
            }
            for cluster in clusters
        ],
        "super_clusters": analysis["super_clusters"],
        "articles": analysis["documents"],
        "trends": analysis["timeline"],
        "charts": {
            "embedding_scatter": analysis["documents"],
            "cluster_sizes": [
                {"label": cluster["label"], "count": cluster["item_count"]}
                for cluster in clusters
            ],
            "source_mix": analysis["source_mix"],
            "timeline": analysis["timeline"],
            "hype_cycle": [
                {
                    "label": cluster["label"],
                    "x": round(cluster["horizon_score"] * 100, 2),
                    "y": cluster["impact_score"],
                }
                for cluster in clusters
            ],
            "monthly_volume": analysis["monthly_volume"],
        },
        "insights": analysis["insights"],
        "recommendations": analysis["recommendations"],
        "risk_signals": analysis["risk_signals"],
        "top_documents": analysis["top_documents"],
        "sources_used": [item["source"] for item in analysis["source_mix"]],
        "parameters": analysis["parameters"],
    }
    return SnapshotLLMEnricher("trend_mapping").enrich_payload(payload)


def build_riskmap_payload(documents: list[Document], window_months: int) -> dict[str, Any]:
    analysis = generate_report_analysis(documents, "risk_mapping", window_months)
    generated_at = analysis["generated_at"]
    clusters = analysis["clusters"]

    payload = {
        "report_type": "risk_mapping",
        "generated_at": generated_at,
        "window_months": window_months,
        "version": 2,
        "summary": {
            **analysis["summary"],
            "executive_summary": analysis["executive_summary"],
        },
        "clusters": [
            {
                "cluster_id": cluster["cluster_id"],
                "label": cluster["label"],
                "dominant_risk": cluster["dominant_risk"] or cluster["category"],
                "documents": cluster["documents"],
                "avg_score": cluster["avg_score"],
                "coords": cluster["coords"],
                "top_keywords": cluster["top_keywords"],
                "direction": cluster["direction"],
                "growth_ratio": cluster["growth_ratio"],
                "horizon_score": cluster["horizon_score"],
                "source_mix": cluster["source_mix"],
                "summary": cluster["summary"],
                "top_documents": cluster["top_documents"],
                "executive_takeaway": cluster["executive_takeaway"],
            }
            for cluster in clusters
        ],
        "charts": {
            "timeline": analysis["timeline"],
            "source_mix": analysis["source_mix"],
            "cluster_sizes": [
                {"label": cluster["label"], "count": cluster["documents"]}
                for cluster in clusters
            ],
            "hype_cycle": [
                {
                    "label": cluster["label"],
                    "x": round(cluster["horizon_score"] * 100, 2),
                    "y": cluster["avg_score"],
                }
                for cluster in clusters
            ],
            "embedding_scatter": analysis["documents"],
            "monthly_volume": analysis["monthly_volume"],
        },
        "top_documents": analysis["top_documents"],
        "sources_used": [item["source"] for item in analysis["source_mix"]],
        "parameters": analysis["parameters"],
        "insights": analysis["insights"],
    }
    return SnapshotLLMEnricher("risk_mapping").enrich_payload(payload)


async def load_documents_for_flow(
    session: AsyncSession,
    business_flow: str,
    window_months: int,
) -> list[Document]:
    window_start = _window_start(window_months)
    published_at_or_fetched = func.coalesce(Document.published_at, Document.fetched_at)
    stmt = (
        select(Document)
        .where(Document.business_flow == business_flow)
        .where(published_at_or_fetched >= window_start)
        .order_by(Document.published_at.desc().nullslast(), Document.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _next_snapshot_version(
    session: AsyncSession,
    report_type: str,
    business_flow: str,
) -> int:
    stmt = select(func.max(ReportSnapshot.version)).where(
        ReportSnapshot.report_type == report_type,
        ReportSnapshot.business_flow == business_flow,
    )
    current = (await session.execute(stmt)).scalar_one_or_none()
    return int(current or 0) + 1


async def _latest_existing_snapshot(
    session: AsyncSession,
    report_type: str,
    business_flow: str,
    window_months: int,
    source_execution_id,
) -> ReportSnapshot | None:
    if source_execution_id is None:
        return None
    stmt = (
        select(ReportSnapshot)
        .where(ReportSnapshot.report_type == report_type)
        .where(ReportSnapshot.business_flow == business_flow)
        .where(ReportSnapshot.window_months == window_months)
        .where(ReportSnapshot.source_execution_id == source_execution_id)
        .order_by(ReportSnapshot.generated_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def persist_snapshot(
    session: AsyncSession,
    report_type: str,
    business_flow: str,
    window_months: int,
    payload: dict[str, Any],
    source_execution_id=None,
    *,
    force: bool = False,
) -> ReportSnapshot:
    if not force:
        existing = await _latest_existing_snapshot(
            session,
            report_type,
            business_flow,
            window_months,
            source_execution_id,
        )
        if existing is not None:
            return existing

    generated_at = datetime.now(timezone.utc)
    version = await _next_snapshot_version(session, report_type, business_flow)
    parameters = payload.get("parameters") or {"window_months": window_months}
    llm_trace = parameters.get("llm_enrichment") if isinstance(parameters, dict) else None
    prompt_content = None
    if isinstance(llm_trace, dict):
        prompt_content = llm_trace.pop("_content_json", None)
    config_hash = hashlib.sha256(
        json.dumps(parameters, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()

    snapshot = ReportSnapshot(
        snapshot_key=f"{report_type}:{business_flow}:v{version}:{generated_at.isoformat()}",
        report_type=report_type,
        business_flow=business_flow,
        version=version,
        status="completed",
        generated_at=generated_at,
        window_months=window_months,
        source_execution_id=source_execution_id,
        config_hash=config_hash,
        summary_json=payload.get("summary") or payload.get("meta"),
        parameters_json=parameters,
        data_json=payload,
    )
    session.add(snapshot)
    await session.flush()

    if isinstance(llm_trace, dict) and llm_trace.get("prompt_key") and llm_trace.get("prompt_version"):
        stmt = select(LLMPrompt).where(
            LLMPrompt.prompt_key == llm_trace["prompt_key"],
            LLMPrompt.version == llm_trace["prompt_version"],
        )
        prompt_row = (await session.execute(stmt)).scalar_one_or_none()
        if prompt_row is None:
            prompt_row = LLMPrompt(
                prompt_key=llm_trace["prompt_key"],
                version=llm_trace["prompt_version"],
                model_id=llm_trace.get("model_id"),
                prompt_file=llm_trace.get("prompt_file") or "unknown",
                prompt_hash=llm_trace.get("prompt_hash"),
                content_json=prompt_content,
                active=True,
            )
            session.add(prompt_row)

    if report_type == "trend_mapping":
        session.add(
            TrendReport(
                snapshot_id=snapshot.id,
                execution_id=source_execution_id,
                title="Trend Mapping Snapshot",
                summary_text=payload.get("summary", {}).get("executive_summary")
                or "Snapshot analitico de vigilancia tecnologica.",
                top_topics_json=[cluster["label"] for cluster in payload.get("clusters", [])[:5]],
            )
        )
        session.add(
            TrendmapSnapshot(
                id=snapshot.id,
                generated_at=generated_at,
                data_json=payload,
                meta_json=payload.get("meta"),
            )
        )
        await session.execute(delete(Trend))
        for cluster in payload.get("clusters", [])[:10]:
            session.add(
                Trend(
                    trend=cluster["label"],
                    category=cluster.get("category") or "Otros",
                    direction=cluster.get("direction") or "stable",
                    momentum=float(cluster.get("impact_score") or 0.0),
                    maturity_stage=cluster.get("maturity_stage") or "plateau_of_productivity",
                    description=cluster.get("summary") or "",
                    impact_on_finance=cluster.get("executive_takeaway") or "",
                )
            )
    else:
        session.add(
            RiskReport(
                snapshot_id=snapshot.id,
                execution_id=source_execution_id,
                title="Risk Mapping Snapshot",
                summary_text=payload.get("summary", {}).get("executive_summary")
                or "Snapshot analitico de riesgos.",
                dominant_risks_json=payload.get("summary", {}).get("dominant_risks", []),
            )
        )

    await session.execute(delete(Cluster).where(Cluster.business_flow == business_flow))
    for cluster in payload.get("clusters", []):
        coords = cluster.get("coords") or {}
        session.add(
            Cluster(
                cluster_id=cluster["cluster_id"],
                label=cluster.get("label", cluster["cluster_id"]),
                category=cluster.get("category") or cluster.get("dominant_risk") or "Otros",
                summary=cluster.get("summary", ""),
                keywords=cluster.get("keywords") or cluster.get("top_keywords") or [],
                item_count=cluster.get("item_count") or cluster.get("documents") or 0,
                impact_score=cluster.get("impact_score") or cluster.get("avg_score") or 0,
                horizon_score=cluster.get("horizon_score") or 0,
                hull_polygon=cluster.get("hull_polygon") or [],
                avg_score=cluster.get("impact_score") or cluster.get("avg_score") or 0,
                x_embed=coords.get("x", 0.0),
                y_embed=coords.get("y", 0.0),
                relevance=cluster.get("relevance", "media"),
                cluster_kind=report_type,
                business_flow=business_flow,
                snapshot_id=snapshot.id,
            )
        )

    await session.commit()
    await session.refresh(snapshot)
    return snapshot
