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
from newsradar_api.shared_kernel.analytics.legacy_trend_adapter import (
    build_legacy_trendmap_payload,
)
from newsradar_api.shared_kernel.config.paths import load_yaml_file, resolve_flow_path

_LEGACY_CLUSTER_ID_MAX = 50


def _legacy_direction(direction: str | None) -> str:
    return {
        "up": "creciente",
        "down": "decreciente",
        "stable": "estable",
    }.get(direction or "", "estable")


def _legacy_cluster_id(cluster_id: str) -> str:
    value = str(cluster_id or "").strip()
    if len(value) <= _LEGACY_CLUSTER_ID_MAX:
        return value
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    prefix_length = _LEGACY_CLUSTER_ID_MAX - len(digest) - 1
    prefix = value[:max(prefix_length, 1)].rstrip("-_")
    return f"{prefix}-{digest}"[:_LEGACY_CLUSTER_ID_MAX]


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


def _normalized_keyword_set(cluster: dict[str, Any]) -> set[str]:
    values = cluster.get("keywords") or cluster.get("top_keywords") or []
    result: set[str] = set()
    for value in values:
        text = str(value).strip().lower()
        if text:
            result.add(text)
    return result


def _category_value(cluster: dict[str, Any]) -> str:
    return str(cluster.get("dominant_risk") or cluster.get("category") or "").strip().lower()


def _flow_analytics_settings(report_type: str) -> dict[str, Any]:
    filename = "risk_mapping.yaml" if report_type == "risk_mapping" else "trend_mapping.yaml"
    path = resolve_flow_path(filename)
    if not path.exists():
        return {}
    analytics = load_yaml_file(path).get("analytics") or {}
    return analytics if isinstance(analytics, dict) else {}


def _snapshot_llm_enabled(report_type: str, *, default: bool = True) -> bool:
    analytics = _flow_analytics_settings(report_type)
    raw = analytics.get("snapshot_llm_enabled")
    if raw is None:
        return default
    return bool(raw)


def _mark_snapshot_llm_skipped(payload: dict[str, Any], report_type: str, reason: str) -> dict[str, Any]:
    parameters = payload.setdefault("parameters", {})
    parameters["llm_enrichment"] = {
        "enabled": False,
        "used": False,
        "report_type": report_type,
        "provider": "bedrock",
        "mode": "disabled",
        "cluster_calls": 0,
        "report_calls": 0,
        "errors": [],
        "reason": reason,
    }
    return payload


def _cluster_taxonomy_set(cluster: dict[str, Any]) -> set[str]:
    values = set()
    for item in cluster.get("taxonomy_matches") or []:
        name = str(item.get("name") or "").strip().lower()
        if name:
            values.add(name)
    return values


def _rewrite_cluster_ids(payload: dict[str, Any], mapping: dict[str, str]) -> None:
    if not mapping:
        return
    for cluster in payload.get("clusters", []):
        cluster_id = cluster.get("cluster_id")
        if cluster_id in mapping:
            cluster["cluster_id"] = mapping[cluster_id]
        lineage_id = cluster.get("lineage_id")
        if lineage_id in mapping:
            cluster["lineage_id"] = mapping[lineage_id]
        comparative = cluster.get("comparative_signal")
        if isinstance(comparative, dict):
            current_id = comparative.get("cluster_id")
            if current_id in mapping:
                comparative["cluster_id"] = mapping[current_id]
    for collection_key in ("documents", "articles"):
        for item in payload.get(collection_key) or []:
            cluster_id = item.get("cluster_id")
            if cluster_id in mapping:
                item["cluster_id"] = mapping[cluster_id]
    for entry in payload.get("timeline") or payload.get("trends") or []:
        cluster_id = entry.get("cluster_id")
        if cluster_id in mapping:
            entry["cluster_id"] = mapping[cluster_id]
    for collection_key in ("cluster_cards", "weak_signals"):
        for item in payload.get(collection_key) or []:
            cluster_id = item.get("cluster_id")
            if cluster_id in mapping:
                item["cluster_id"] = mapping[cluster_id]
    for group in payload.get("super_clusters") or []:
        cluster_ids = group.get("clusters") or group.get("sub_cluster_ids")
        if isinstance(cluster_ids, list):
            for index, cluster_id in enumerate(cluster_ids):
                if cluster_id in mapping:
                    cluster_ids[index] = mapping[cluster_id]
    for signal in payload.get("risk_signals") or []:
        related = signal.get("related_clusters")
        if isinstance(related, list):
            signal["related_clusters"] = [mapping.get(cluster_id, cluster_id) for cluster_id in related]


def _sync_cluster_cards(payload: dict[str, Any]) -> None:
    cluster_index = {
        str(cluster.get("cluster_id")): cluster
        for cluster in payload.get("clusters", [])
        if cluster.get("cluster_id")
    }
    for key in ("cluster_cards", "weak_signals"):
        for card in payload.get(key) or []:
            cluster = cluster_index.get(str(card.get("cluster_id")))
            if not cluster:
                continue
            if cluster.get("comparative_signal") is not None:
                card["comparative_signal"] = cluster["comparative_signal"]
            if cluster.get("signal_state"):
                card["signal_state"] = cluster["signal_state"]


def _cluster_similarity(current: dict[str, Any], previous: dict[str, Any]) -> float:
    current_keywords = _normalized_keyword_set(current)
    previous_keywords = _normalized_keyword_set(previous)
    keyword_overlap = (
        len(current_keywords & previous_keywords) / len(current_keywords | previous_keywords)
        if current_keywords and previous_keywords
        else 0.0
    )
    label_current = str(current.get("label") or "").strip().lower()
    label_previous = str(previous.get("label") or "").strip().lower()
    label_score = 1.0 if label_current and label_current == label_previous else 0.0
    category_score = 1.0 if _category_value(current) and _category_value(current) == _category_value(previous) else 0.0
    taxonomy_current = _cluster_taxonomy_set(current)
    taxonomy_previous = _cluster_taxonomy_set(previous)
    taxonomy_overlap = (
        len(taxonomy_current & taxonomy_previous) / len(taxonomy_current | taxonomy_previous)
        if taxonomy_current and taxonomy_previous
        else 0.0
    )
    fingerprint_score = 1.0 if current.get("cluster_fingerprint") and current.get("cluster_fingerprint") == previous.get("cluster_fingerprint") else 0.0
    return 0.40 * keyword_overlap + 0.18 * label_score + 0.18 * category_score + 0.14 * taxonomy_overlap + 0.10 * fingerprint_score


def _attach_comparative_signals(payload: dict[str, Any], previous_payload: dict[str, Any] | None) -> None:
    report_type = str(payload.get("report_type") or "trend_mapping")
    analytics_settings = _flow_analytics_settings(report_type)
    similarity_threshold = float(analytics_settings.get("lineage_similarity_threshold") or 0.52)
    reuse_previous_cluster_ids = bool(analytics_settings.get("reuse_previous_cluster_ids", True))
    quality_checks = payload.setdefault("quality_checks", {})
    filters_metadata = payload.setdefault("filters_metadata", {})

    if not previous_payload:
        payload["comparative_signals"] = {
            "previous_snapshot_available": False,
            "summary": "No hay snapshot previo comparable.",
            "clusters": [],
            "matched_clusters": 0,
            "new_clusters": len(payload.get("clusters") or []),
            "accelerating_clusters": 0,
            "cooling_clusters": 0,
            "stable_clusters": 0,
            "stability_score_avg": 0.0,
        }
        quality_checks["stability_score_avg"] = 0.0
        quality_checks["lineage_reused_clusters"] = 0
        quality_checks["new_cluster_ratio"] = 0.0 if not payload.get("clusters") else 100.0
        filters_metadata["comparative_statuses"] = ["new", "accelerating", "cooling", "stable"]
        _sync_cluster_cards(payload)
        return

    current_clusters = list(payload.get("clusters") or [])
    previous_clusters = list(previous_payload.get("clusters") or [])
    candidate_pairs: list[tuple[float, int, int]] = []
    for current_index, current in enumerate(current_clusters):
        for previous_index, candidate in enumerate(previous_clusters):
            candidate_pairs.append((_cluster_similarity(current, candidate), current_index, previous_index))
    candidate_pairs.sort(key=lambda item: item[0], reverse=True)

    matched_current: set[int] = set()
    matched_previous: set[int] = set()
    matches: dict[int, tuple[int, float]] = {}
    for score, current_index, previous_index in candidate_pairs:
        if score < similarity_threshold:
            break
        if current_index in matched_current or previous_index in matched_previous:
            continue
        matched_current.add(current_index)
        matched_previous.add(previous_index)
        matches[current_index] = (previous_index, score)

    id_mapping: dict[str, str] = {}
    new_count = accelerating_count = cooling_count = stable_count = 0
    stability_scores: list[float] = []

    for current_index, cluster in enumerate(current_clusters):
        match = matches.get(current_index)
        if match is None:
            new_count += 1
            comparison = {
                "cluster_id": cluster["cluster_id"],
                "lineage_id": cluster.get("lineage_id") or cluster["cluster_id"],
                "matched_previous_cluster": None,
                "previous_label": None,
                "history_depth": int(cluster.get("history_depth") or 1),
                "status": "new",
                "delta_documents": cluster.get("item_count") or cluster.get("documents") or 0,
                "delta_impact": cluster.get("impact_score") or 0,
                "delta_momentum": cluster.get("momentum_score") or 0,
                "similarity": 0.0,
                "stability_score": 0.0,
            }
            cluster["comparative_signal"] = comparison
            cluster["lineage_id"] = comparison["lineage_id"]
            cluster["history_depth"] = comparison["history_depth"]
            continue

        previous_index, best_score = match
        previous_cluster = previous_clusters[previous_index]
        previous_cluster_id = str(previous_cluster.get("cluster_id") or "")
        current_docs = float(cluster.get("item_count") or cluster.get("documents") or 0)
        previous_docs = float(previous_cluster.get("item_count") or previous_cluster.get("documents") or 0)
        current_impact = float(cluster.get("impact_score") or cluster.get("avg_score") or 0)
        previous_impact = float(previous_cluster.get("impact_score") or previous_cluster.get("avg_score") or 0)
        current_momentum = float(cluster.get("momentum_score") or 0)
        previous_momentum = float(previous_cluster.get("momentum_score") or 0)
        delta_documents = round(current_docs - previous_docs, 1)
        delta_impact = round(current_impact - previous_impact, 1)
        delta_momentum = round(current_momentum - previous_momentum, 1)
        if delta_momentum >= 8 or delta_documents >= 2:
            status = "accelerating"
            accelerating_count += 1
        elif delta_momentum <= -8:
            status = "cooling"
            cooling_count += 1
        else:
            status = "stable"
            stable_count += 1

        lineage_id = str(previous_cluster.get("lineage_id") or previous_cluster_id or cluster["cluster_id"])
        history_depth = int(previous_cluster.get("history_depth") or 1) + 1
        stability_score = round(best_score * 100, 1)
        stability_scores.append(stability_score)
        if reuse_previous_cluster_ids and previous_cluster_id and previous_cluster_id != cluster["cluster_id"]:
            id_mapping[str(cluster["cluster_id"])] = previous_cluster_id
        comparison = {
            "cluster_id": cluster["cluster_id"],
            "lineage_id": lineage_id,
            "matched_previous_cluster": previous_cluster_id or None,
            "previous_label": previous_cluster.get("label"),
            "history_depth": history_depth,
            "status": status,
            "delta_documents": delta_documents,
            "delta_impact": delta_impact,
            "delta_momentum": delta_momentum,
            "similarity": round(best_score, 3),
            "stability_score": stability_score,
        }
        cluster["comparative_signal"] = comparison
        cluster["lineage_id"] = lineage_id
        cluster["history_depth"] = history_depth

    if id_mapping:
        _rewrite_cluster_ids(payload, id_mapping)

    cluster_comparisons = [
        cluster["comparative_signal"]
        for cluster in payload.get("clusters", [])
        if isinstance(cluster.get("comparative_signal"), dict)
    ]
    stability_avg = round(sum(stability_scores) / len(stability_scores), 1) if stability_scores else 0.0
    matched_count = len(stability_scores)
    total_clusters = len(payload.get("clusters", []) or [])
    quality_checks["stability_score_avg"] = stability_avg
    quality_checks["lineage_reused_clusters"] = matched_count
    quality_checks["new_cluster_ratio"] = round((new_count / max(total_clusters, 1)) * 100, 1)
    filters_metadata["comparative_statuses"] = ["new", "accelerating", "cooling", "stable"]

    payload["comparative_signals"] = {
        "previous_snapshot_available": True,
        "summary": (
            f"{matched_count} clusters con continuidad historica, {new_count} nuevos, "
            f"{accelerating_count} acelerando y {cooling_count} enfriandose frente al snapshot previo."
        ),
        "clusters": cluster_comparisons,
        "matched_clusters": matched_count,
        "new_clusters": new_count,
        "accelerating_clusters": accelerating_count,
        "cooling_clusters": cooling_count,
        "stable_clusters": stable_count,
        "stability_score_avg": stability_avg,
    }
    _sync_cluster_cards(payload)


def build_trendmap_payload(documents: list[Document], window_months: int) -> dict[str, Any]:
    analytics_settings = _flow_analytics_settings("trend_mapping")
    if str(analytics_settings.get("analysis_engine") or "").strip().lower() == "legacy_trend_pipeline_adapter":
        payload = build_legacy_trendmap_payload(documents, window_months)
        if _snapshot_llm_enabled("trend_mapping", default=False):
            return SnapshotLLMEnricher("trend_mapping").enrich_payload(payload)
        return _mark_snapshot_llm_skipped(
            payload,
            "trend_mapping",
            "snapshot llm disabled by trend_mapping flow config",
        )

    analysis = generate_report_analysis(documents, "trend_mapping", window_months)
    generated_at = analysis["generated_at"]
    clusters = analysis["clusters"]

    payload = {
        "report_type": "trend_mapping",
        "generated_at": generated_at,
        "window_months": window_months,
        "version": 3,
        "methodology_version": analysis["parameters"]["methodology_version"],
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
                "maturity_score": cluster["maturity_score"],
                "horizon_score": cluster["horizon_score"],
                "maturity_stage": cluster["maturity_stage"],
                "hype_stage": cluster["hype_stage"],
                "direction": cluster["direction"],
                "growth_ratio": cluster["growth_ratio"],
                "acceleration_ratio": cluster["acceleration_ratio"],
                "momentum_score": cluster["momentum_score"],
                "novelty_score": cluster["novelty_score"],
                "novelty_band": cluster.get("novelty_band"),
                "uncertainty_score": cluster["uncertainty_score"],
                "weak_signal_flag": cluster["weak_signal_flag"],
                "signal_state": cluster.get("signal_state"),
                "lineage_id": cluster.get("lineage_id"),
                "cluster_fingerprint": cluster.get("cluster_fingerprint"),
                "history_depth": cluster.get("history_depth"),
                "subtitle": cluster["subtitle"],
                "rationale": cluster["rationale"],
                "taxonomy_matches": cluster["taxonomy_matches"],
                "cluster_quality": cluster["cluster_quality"],
                "maturity_score_breakdown": cluster["maturity_score_breakdown"],
                "impact_score_breakdown": cluster["impact_score_breakdown"],
                "momentum_score_breakdown": cluster["momentum_score_breakdown"],
                "novelty_score_breakdown": cluster["novelty_score_breakdown"],
                "uncertainty_score_breakdown": cluster["uncertainty_score_breakdown"],
                "hull_polygon": cluster["hull_polygon"],
                "articles": cluster["articles"],
                "top_documents": cluster["top_documents"],
                "representative_documents": cluster["representative_documents"],
                "source_mix": cluster["source_mix"],
                "source_count": cluster.get("source_count"),
                "active_months": cluster.get("active_months"),
                "impact_targets": cluster.get("impact_targets"),
                "evidence_line": cluster.get("evidence_line"),
                "insight_evidence": cluster["insight_evidence"],
                "executive_takeaway": cluster["executive_takeaway"],
                "what_is_happening": cluster["what_is_happening"],
                "why_it_matters": cluster["why_it_matters"],
                "decision_prompt": cluster["decision_prompt"],
                "coords": cluster["coords"],
            }
            for cluster in clusters
        ],
        "super_clusters": analysis["super_clusters"],
        "articles": analysis["documents"],
        "documents": analysis["documents"],
        "trends": analysis["timeline"],
        "charts": {
            "embedding_scatter": analysis["documents"],
            "cluster_scatter": [
                {
                    "label": cluster["label"],
                    "category": cluster["category"],
                    "x": cluster["impact_score"],
                    "y": cluster["maturity_score"],
                    "size": cluster["item_count"],
                }
                for cluster in clusters
            ],
            "cluster_sizes": [
                {"label": cluster["label"], "count": cluster["item_count"]}
                for cluster in clusters
            ],
            "source_mix": analysis["source_mix"],
            "timeline": analysis["timeline"],
            "hype_cycle": [
                {
                    "label": cluster["label"],
                    "stage": cluster["hype_stage"],
                    "x": round(cluster["maturity_score"], 2),
                    "y": cluster["impact_score"],
                    "momentum": cluster["momentum_score"],
                }
                for cluster in clusters
            ],
            "monthly_volume": analysis["monthly_volume"],
        },
        "insights": analysis["insights"],
        "recommendations": analysis["recommendations"],
        "risk_signals": analysis["risk_signals"],
        "top_documents": analysis["top_documents"],
        "cluster_cards": analysis["cluster_cards"],
        "trend_cards": analysis["trend_cards"],
        "taxonomy_breakdown": analysis["taxonomy_breakdown"],
        "quality_checks": analysis["quality_checks"],
        "filters_metadata": analysis["filters_metadata"],
        "weak_signals": analysis["weak_signals"],
        "methodology": analysis["methodology"],
        "sources_used": [item["source"] for item in analysis["source_mix"]],
        "parameters": analysis["parameters"],
    }
    if _snapshot_llm_enabled("trend_mapping", default=True):
        return SnapshotLLMEnricher("trend_mapping").enrich_payload(payload)
    return _mark_snapshot_llm_skipped(
        payload,
        "trend_mapping",
        "snapshot llm disabled by trend_mapping flow config",
    )


def build_riskmap_payload(documents: list[Document], window_months: int) -> dict[str, Any]:
    analysis = generate_report_analysis(documents, "risk_mapping", window_months)
    generated_at = analysis["generated_at"]
    clusters = analysis["clusters"]

    payload = {
        "report_type": "risk_mapping",
        "generated_at": generated_at,
        "window_months": window_months,
        "version": 3,
        "methodology_version": analysis["parameters"]["methodology_version"],
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
                "dominant_risk": cluster["dominant_risk"] or cluster["category"],
                "keywords": cluster["keywords"],
                "relevance": cluster["relevance"],
                "documents": cluster["documents"],
                "item_count": cluster["item_count"],
                "effective_documents": cluster.get("effective_documents"),
                "avg_score": cluster["avg_score"],
                "impact_score": cluster["impact_score"],
                "maturity_score": cluster["maturity_score"],
                "coords": cluster["coords"],
                "hull_polygon": cluster["hull_polygon"],
                "articles": cluster["articles"],
                "top_keywords": cluster["top_keywords"],
                "direction": cluster["direction"],
                "growth_ratio": cluster["growth_ratio"],
                "acceleration_ratio": cluster["acceleration_ratio"],
                "horizon_score": cluster["horizon_score"],
                "momentum_score": cluster["momentum_score"],
                "novelty_score": cluster["novelty_score"],
                "novelty_band": cluster.get("novelty_band"),
                "uncertainty_score": cluster["uncertainty_score"],
                "persistence_score": cluster["persistence_score"],
                "persistence_score_breakdown": cluster.get("persistence_score_breakdown"),
                "risk_severity": cluster["risk_severity"],
                "severity_band": cluster.get("severity_band"),
                "risk_severity_breakdown": cluster["risk_severity_breakdown"],
                "maturity_stage": cluster["maturity_stage"],
                "hype_stage": cluster["hype_stage"],
                "weak_signal_flag": cluster["weak_signal_flag"],
                "signal_state": cluster.get("signal_state"),
                "lineage_id": cluster.get("lineage_id"),
                "cluster_fingerprint": cluster.get("cluster_fingerprint"),
                "history_depth": cluster.get("history_depth"),
                "subtitle": cluster["subtitle"],
                "rationale": cluster["rationale"],
                "taxonomy_matches": cluster["taxonomy_matches"],
                "cluster_quality": cluster["cluster_quality"],
                "maturity_score_breakdown": cluster["maturity_score_breakdown"],
                "impact_score_breakdown": cluster["impact_score_breakdown"],
                "momentum_score_breakdown": cluster["momentum_score_breakdown"],
                "novelty_score_breakdown": cluster["novelty_score_breakdown"],
                "uncertainty_score_breakdown": cluster["uncertainty_score_breakdown"],
                "source_mix": cluster["source_mix"],
                "summary": cluster["summary"],
                "top_documents": cluster["top_documents"],
                "representative_documents": cluster["representative_documents"],
                "insight_evidence": cluster["insight_evidence"],
                "executive_takeaway": cluster["executive_takeaway"],
                "what_is_happening": cluster["what_is_happening"],
                "why_it_matters": cluster["why_it_matters"],
                "decision_prompt": cluster["decision_prompt"],
                "source_count": cluster.get("source_count"),
                "active_months": cluster.get("active_months"),
                "impact_targets": cluster.get("impact_targets"),
                "evidence_line": cluster.get("evidence_line"),
            }
            for cluster in clusters
        ],
        "super_clusters": analysis["super_clusters"],
        "documents": analysis["documents"],
        "articles": analysis["documents"],
        "timeline": analysis["timeline"],
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
                    "stage": cluster["hype_stage"],
                    "x": round(cluster["maturity_score"], 2),
                    "y": cluster["impact_score"],
                    "momentum": cluster["momentum_score"],
                }
                for cluster in clusters
            ],
            "risk_scatter": [
                {
                    "label": cluster["label"],
                    "category": cluster["dominant_risk"],
                    "x": cluster["risk_severity"],
                    "y": cluster["momentum_score"],
                    "size": cluster["documents"],
                }
                for cluster in clusters
            ],
            "embedding_scatter": analysis["documents"],
            "monthly_volume": analysis["monthly_volume"],
        },
        "top_documents": analysis["top_documents"],
        "cluster_cards": analysis["cluster_cards"],
        "trend_cards": analysis["trend_cards"],
        "taxonomy_breakdown": analysis["taxonomy_breakdown"],
        "quality_checks": analysis["quality_checks"],
        "filters_metadata": analysis["filters_metadata"],
        "weak_signals": analysis["weak_signals"],
        "methodology": analysis["methodology"],
        "sources_used": [item["source"] for item in analysis["source_mix"]],
        "parameters": analysis["parameters"],
        "insights": analysis["insights"],
        "recommendations": analysis["recommendations"],
        "risk_signals": analysis["risk_signals"],
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


async def _latest_previous_snapshot(
    session: AsyncSession,
    report_type: str,
    business_flow: str,
) -> ReportSnapshot | None:
    stmt = (
        select(ReportSnapshot)
        .where(ReportSnapshot.report_type == report_type)
        .where(ReportSnapshot.business_flow == business_flow)
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

    previous_snapshot = await _latest_previous_snapshot(session, report_type, business_flow)
    _attach_comparative_signals(payload, previous_snapshot.data_json if previous_snapshot else None)
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
                    direction=_legacy_direction(cluster.get("direction")),
                    momentum=float(
                        max(
                            0.0,
                            min(
                                1.0,
                                0.5 + float(cluster.get("growth_ratio") or 0.0) * 0.35,
                            ),
                        )
                    ),
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
                cluster_id=_legacy_cluster_id(cluster["cluster_id"]),
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
