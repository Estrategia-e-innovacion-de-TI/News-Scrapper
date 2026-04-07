"""Build-trendmap adapter for snapshot-driven Trend Mapping."""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from newsradar_api.infrastructure.pipeline.trendmap_pipeline import TrendmapPipeline, _sha256

from .advanced_engine import _build_breakdown, _cluster_signal_state, _score_band

_METHOD_VERSION = "build_trendmap_adapter_v3"
_GARTNER_STAGES = (
    "innovation_trigger",
    "peak_of_inflated_expectations",
    "trough_of_disillusionment",
    "slope_of_enlightenment",
    "plateau_of_productivity",
)
_HYPE_STAGE_ORDER = (
    "weak_signal",
    "innovation_trigger",
    "rising_attention",
    "peak_visibility",
    "correction",
    "consolidation",
    "productive_adoption",
)
_STAGE_SCORE = {
    "innovation_trigger": 25.0,
    "peak_of_inflated_expectations": 46.0,
    "trough_of_disillusionment": 34.0,
    "slope_of_enlightenment": 72.0,
    "plateau_of_productivity": 88.0,
}
_CATEGORY_TARGETS = {
    "Inteligencia Artificial": ["automatizacion", "productividad", "servicio al cliente"],
    "Ciberseguridad": ["continuidad", "riesgo operacional", "terceros"],
    "Blockchain/Cripto": ["pagos", "activos digitales", "cumplimiento"],
    "Fintech/Banca Digital": ["clientes", "producto", "canales digitales"],
    "Cloud/Datos": ["arquitectura", "datos", "eficiencia"],
    "Regulacion": ["cumplimiento", "gobierno", "riesgo de modelo"],
    "Computación Cuántica": ["seguridad", "criptografia", "estrategia"],
    "Innovación General": ["portafolio", "capacidades", "vigilancia"],
    "Otros": ["portafolio", "capacidades", "vigilancia"],
}
_GENERIC_KEYWORDS = {
    "news", "report", "reports", "update", "updates", "market", "markets",
    "technology", "technologies", "article", "articles", "latest", "breaking",
}


def _safe_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _as_utc(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = _safe_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _document_date(doc: Any) -> datetime | None:
    return _as_utc(getattr(doc, "published_at", None) or getattr(doc, "fetched_at", None))


def _document_source_type(doc: Any) -> str:
    source_type = _safe_text(getattr(doc, "source_type", "")).lower()
    if source_type in {"rss", "paper", "pdf", "institutional_report", "patent"}:
        return source_type
    return "news"


def _cluster_slug(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    return "-".join(tokens[:6]) or "cluster"


def _clean_legacy_label(label: str, category: str) -> str:
    text = _safe_text(label)
    stripped = re.sub(r"^\[[^\]]+\]\s*", "", text).strip()
    return stripped or category or "Cluster"


def _cluster_identity(label: str, category: str, keywords: list[str]) -> tuple[str, str]:
    seed_parts = [category, label, *keywords[:4]]
    seed = " | ".join(part.lower() for part in seed_parts if _safe_text(part))
    fingerprint = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10] if seed else "cluster0000"
    return f"trend-{_cluster_slug(label or category)}-{fingerprint}", fingerprint


def _record_id(doc: Any) -> str:
    return _sha256(_safe_text(getattr(doc, "url", "")) or _safe_text(getattr(doc, "title", "")) or _safe_text(getattr(doc, "id", "")))


def _doc_to_record(doc: Any) -> dict[str, Any]:
    date = _document_date(doc)
    return {
        "title": _safe_text(getattr(doc, "title", "")),
        "excerpt": _safe_text(getattr(doc, "excerpt", "")),
        "text": _safe_text(getattr(doc, "text", "")),
        "url": _safe_text(getattr(doc, "url", "")),
        "published_at": date.isoformat() if date else None,
        "relevance_score": float(getattr(doc, "relevance_score", 0) or 0),
        "source_id": _safe_text(getattr(doc, "source_id", "")),
    }


def _representative_reason(doc_payload: dict[str, Any]) -> str:
    reasons: list[str] = []
    if float(doc_payload.get("score") or 0) >= 80:
        reasons.append("alto score")
    if float(doc_payload.get("recency_score") or 0) >= 70:
        reasons.append("senal reciente")
    if doc_payload.get("source_type") in {"paper", "pdf", "institutional_report", "patent"}:
        reasons.append("evidencia especializada")
    if not reasons:
        reasons.append("pieza representativa")
    return " + ".join(reasons[:3])


def _legacy_maturity_score(stage: str, horizon_score: float) -> float:
    base = _STAGE_SCORE.get(stage, 42.0)
    if horizon_score:
        return round(min(100.0, max(0.0, base * 0.65 + float(horizon_score) * 35)), 1)
    return round(base, 1)


def _temporal_metrics(docs: list[dict[str, Any]], window_months: int) -> dict[str, Any]:
    month_counts = Counter()
    recent_scores: list[float] = []
    now = datetime.now(timezone.utc)
    for doc in docs:
        date = _as_utc(doc.get("date"))
        if date is None:
            continue
        month_counts[date.strftime("%Y-%m")] += 1
        age_days = max(0.0, (now - date).total_seconds() / 86400.0)
        recent_scores.append(max(0.0, 1.0 - min(age_days / max(window_months * 30, 1), 1.0)))
    ordered = [count for _, count in sorted(month_counts.items())]
    active_months = len(month_counts)
    if len(ordered) >= 2:
        first = ordered[0]
        last = ordered[-1]
        growth_ratio = round((last - first) / max(first, 1), 3)
    else:
        growth_ratio = 0.0
    if len(ordered) >= 3:
        prev_delta = ordered[-2] - ordered[-3]
        latest_delta = ordered[-1] - ordered[-2]
        acceleration_ratio = round((latest_delta - prev_delta) / max(abs(prev_delta), 1), 3)
    else:
        acceleration_ratio = round(growth_ratio / 2, 3)
    direction = "up" if growth_ratio > 0.22 else "down" if growth_ratio < -0.18 else "stable"
    recurrence = round(active_months / max(window_months, 1), 3)
    recent_share = round(float(mean(recent_scores)) if recent_scores else 0.0, 3)
    return {
        "month_counts": month_counts,
        "active_months": active_months,
        "growth_ratio": growth_ratio,
        "acceleration_ratio": acceleration_ratio,
        "direction": direction,
        "recurrence": recurrence,
        "recent_share": recent_share,
    }


def _legacy_hype_stage(stage: str, momentum_score: float, weak_signal_flag: bool) -> str:
    if weak_signal_flag:
        return "weak_signal"
    if stage == "innovation_trigger":
        return "innovation_trigger"
    if stage == "peak_of_inflated_expectations":
        return "peak_visibility" if momentum_score >= 65 else "rising_attention"
    if stage == "trough_of_disillusionment":
        return "correction"
    if stage == "slope_of_enlightenment":
        return "consolidation"
    return "productive_adoption"


def _cluster_quality(avg_score: float, source_count: int, active_months: int, category: str) -> dict[str, float]:
    coherence = round(min(100.0, 52 + avg_score * 0.38 + min(source_count, 5) * 3.5), 1)
    separation = round(min(100.0, 48 + min(active_months, 6) * 6.0 + min(source_count, 4) * 4.0), 1)
    taxonomy_focus = 78.0 if category not in {"Otros", "Innovación General"} else 42.0
    duplicate_pressure = 8.0
    score = round(
        0.38 * coherence
        + 0.22 * separation
        + 0.20 * taxonomy_focus
        + 0.10 * min(100.0, source_count * 18.0)
        + 0.10 * (100.0 - duplicate_pressure),
        1,
    )
    return {
        "score": score,
        "coherence": coherence,
        "separation": separation,
        "taxonomy_focus": taxonomy_focus,
        "duplicate_pressure": duplicate_pressure,
    }


def _impact_targets(category: str) -> list[str]:
    return list(_CATEGORY_TARGETS.get(category, _CATEGORY_TARGETS["Innovación General"]))


def _taxonomy_matches(category: str, keywords: list[str]) -> list[dict[str, Any]]:
    score = 0.8 if category not in {"Otros", "Innovación General"} else 0.45
    return [
        {
            "name": category or "Innovación General",
            "score": round(score, 3),
            "matched_terms": keywords[:5],
            "matched_fields": ["cluster_label", "cluster_keywords"],
            "sector_tags": _impact_targets(category)[:3],
            "capability_tags": _impact_targets(category)[1:3],
        }
    ]


def _top_documents(docs: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    ranked = sorted(
        docs,
        key=lambda doc: (float(doc.get("score") or 0), _safe_text(doc.get("date"))),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for doc in ranked:
        source = _safe_text(doc.get("source"))
        if len(selected) < max(2, limit - 1) and source and source in seen_sources:
            continue
        seen_sources.add(source)
        selected.append(doc)
        if len(selected) >= limit:
            break
    return selected


def _summary_line(label: str, category: str, keywords: list[str], item_count: int, source_count: int) -> str:
    focus = ", ".join(keywords[:3]) if keywords else category.lower()
    return (
        f"{label} agrupa {item_count} registros sobre {category.lower()}, con evidencia concentrada en "
        f"{focus} y cobertura de {source_count} fuentes."
    )


def _decision_prompt(hype_stage: str, label: str, targets: list[str]) -> str:
    target_text = ", ".join(targets[:2]) or "capacidades transversales"
    if hype_stage in {"weak_signal", "innovation_trigger"}:
        return f"Definir una exploracion acotada para {label}, con hipotesis, owner y criterio de descarte sobre {target_text}."
    if hype_stage in {"rising_attention", "peak_visibility"}:
        return f"Fijar postura estrategica para {label}: decidir si pasa a piloto, partnership o vigilancia prioritaria en {target_text}."
    return f"Llevar {label} a roadmap operativo, conectando capacidades y dependencias sobre {target_text}."


def _score_breakdowns(
    *,
    impact_score: float,
    maturity_score: float,
    momentum_score: float,
    novelty_score: float,
    uncertainty_score: float,
    avg_score: float,
    item_count: int,
    source_count: int,
    active_months: int,
    recent_share: float,
    growth_ratio: float,
) -> dict[str, dict[str, Any]]:
    volume_signal = min(1.0, math.log1p(item_count) / math.log1p(25))
    source_signal = min(1.0, source_count / 5.0)
    active_signal = min(1.0, active_months / 6.0)
    impact_breakdown = _build_breakdown(
        "0.45 score medio + 0.25 volumen + 0.20 recencia + 0.10 diversidad de fuentes",
        {"avg_score": 0.45, "volume": 0.25, "recent_share": 0.20, "source_diversity": 0.10},
        {
            "avg_score": avg_score / 100.0,
            "volume": volume_signal,
            "recent_share": recent_share,
            "source_diversity": source_signal,
        },
    )
    impact_breakdown["score"] = round(impact_score, 1)
    maturity_breakdown = _build_breakdown(
        "0.55 stage base + 0.25 actividad temporal + 0.20 volumen observado",
        {"stage_signal": 0.55, "active_months": 0.25, "volume": 0.20},
        {
            "stage_signal": maturity_score / 100.0,
            "active_months": active_signal,
            "volume": volume_signal,
        },
    )
    maturity_breakdown["score"] = round(maturity_score, 1)
    momentum_breakdown = _build_breakdown(
        "0.45 crecimiento + 0.25 share reciente + 0.15 meses activos + 0.15 volumen",
        {"growth": 0.45, "recent_share": 0.25, "active_months": 0.15, "volume": 0.15},
        {
            "growth": min(1.0, max(0.0, 0.5 + growth_ratio * 0.4)),
            "recent_share": recent_share,
            "active_months": active_signal,
            "volume": volume_signal,
        },
    )
    momentum_breakdown["score"] = round(momentum_score, 1)
    novelty_breakdown = _build_breakdown(
        "0.45 baja madurez + 0.30 recencia + 0.15 escala acotada + 0.10 foco emergente",
        {"low_maturity": 0.45, "recent_share": 0.30, "small_scale": 0.15, "growth": 0.10},
        {
            "low_maturity": 1.0 - min(1.0, maturity_score / 100.0),
            "recent_share": recent_share,
            "small_scale": 1.0 - volume_signal,
            "growth": min(1.0, max(0.0, 0.5 + growth_ratio * 0.3)),
        },
    )
    novelty_breakdown["score"] = round(novelty_score, 1)
    uncertainty_breakdown = _build_breakdown(
        "0.35 poca escala + 0.25 baja diversidad + 0.20 baja actividad + 0.20 score medio limitado",
        {"low_scale": 0.35, "low_diversity": 0.25, "low_activity": 0.20, "low_score": 0.20},
        {
            "low_scale": 1.0 - volume_signal,
            "low_diversity": 1.0 - source_signal,
            "low_activity": 1.0 - active_signal,
            "low_score": 1.0 - min(1.0, avg_score / 100.0),
        },
    )
    uncertainty_breakdown["score"] = round(uncertainty_score, 1)
    return {
        "impact": impact_breakdown,
        "maturity": maturity_breakdown,
        "momentum": momentum_breakdown,
        "novelty": novelty_breakdown,
        "uncertainty": uncertainty_breakdown,
    }


def _build_document_payload(
    original_doc: Any,
    *,
    article_id: str,
    cluster_id: str,
    cluster_label: str | None,
    category: str | None,
    x_embed: float,
    y_embed: float,
    window_months: int,
) -> dict[str, Any]:
    date = _document_date(original_doc)
    now = datetime.now(timezone.utc)
    recency_score = 0.0
    if date is not None:
        age_days = max(0.0, (now - date).total_seconds() / 86400.0)
        recency_score = round(max(0.0, 100.0 - min(age_days / max(window_months * 30, 1), 1.0) * 100.0), 1)
    return {
        "id": article_id,
        "title": _safe_text(getattr(original_doc, "title", "")),
        "source": _safe_text(getattr(original_doc, "source_id", "")),
        "source_type": _document_source_type(original_doc),
        "date": date.isoformat() if date else None,
        "score": float(getattr(original_doc, "relevance_score", 0) or 0),
        "url": _safe_text(getattr(original_doc, "url", "")),
        "x_embed": round(float(x_embed), 4),
        "y_embed": round(float(y_embed), 4),
        "cluster_id": cluster_id,
        "cluster_label": cluster_label,
        "summary": _safe_text(getattr(original_doc, "excerpt", "")) or _safe_text(getattr(original_doc, "title", "")),
        "category": category,
        "risk_type": getattr(original_doc, "risk_type", None),
        "taxonomy_matches": [],
        "source_weight": 86.0 if _document_source_type(original_doc) in {"paper", "pdf", "institutional_report", "patent"} else 55.0,
        "duplicate_signature": article_id,
        "duplicate_flag": False,
        "recency_score": recency_score,
        "unclustered": cluster_id == "sin_cluster",
        "unclustered_reason": "cluster_noise" if cluster_id == "sin_cluster" else None,
    }


def build_legacy_trendmap_payload(
    documents: list[Any],
    window_months: int,
    *,
    min_relevance_score: float = 40.0,
) -> dict[str, Any]:
    pipeline = TrendmapPipeline(min_year=1970, min_score=0)
    threshold = float(min_relevance_score)
    input_document_count = len(documents)
    eligible_documents = [
        doc
        for doc in documents
        if float(getattr(doc, "relevance_score", 0) or 0) > threshold
    ]
    filtered_document_count = input_document_count - len(eligible_documents)
    news_records: list[dict[str, Any]] = []
    paper_records: list[dict[str, Any]] = []
    original_by_article_id: dict[str, Any] = {}

    for doc in eligible_documents:
        article_id = _record_id(doc)
        original_by_article_id[article_id] = doc
        record = _doc_to_record(doc)
        if _document_source_type(doc) in {"paper", "pdf", "institutional_report", "patent"}:
            paper_records.append(record)
        else:
            news_records.append(record)

    response, artifacts = pipeline.generate_from_records(news_records, paper_records, persist_output=False)

    cluster_id_map: dict[str, str] = {"unclustered": "sin_cluster"}
    cluster_fingerprint_map: dict[str, str] = {}
    cluster_category_map: dict[str, str] = {}
    cluster_label_map: dict[str, str] = {}
    for cluster in response.clusters:
        label = _clean_legacy_label(cluster.label, cluster.category)
        cluster_id, fingerprint = _cluster_identity(label, cluster.category, list(cluster.keywords))
        cluster_id_map[cluster.cluster_id] = cluster_id
        cluster_fingerprint_map[cluster.cluster_id] = fingerprint
        cluster_category_map[cluster.cluster_id] = cluster.category or "Innovación General"
        cluster_label_map[cluster.cluster_id] = label

    documents_payload: list[dict[str, Any]] = []
    doc_payload_by_id: dict[str, dict[str, Any]] = {}
    for article in response.articles:
        original = original_by_article_id.get(article.id)
        if original is None:
            continue
        stable_cluster_id = cluster_id_map.get(article.cluster_id, "sin_cluster")
        category = cluster_category_map.get(article.cluster_id) or _safe_text(getattr(original, "category", None))
        payload = _build_document_payload(
            original,
            article_id=article.id,
            cluster_id=stable_cluster_id,
            cluster_label=cluster_label_map.get(article.cluster_id),
            category=category or None,
            x_embed=float(article.x_embed),
            y_embed=float(article.y_embed),
            window_months=window_months,
        )
        documents_payload.append(payload)
        doc_payload_by_id[payload["id"]] = payload

    clusters_payload: list[dict[str, Any]] = []
    taxonomy_breakdown = Counter()
    keyword_counter = Counter()
    for cluster in response.clusters:
        stable_cluster_id = cluster_id_map[cluster.cluster_id]
        label = cluster_label_map[cluster.cluster_id]
        cluster_docs = [doc_payload_by_id[article_id] for article_id in cluster.articles if article_id in doc_payload_by_id]
        if not cluster_docs:
            continue
        avg_score = round(mean(doc["score"] for doc in cluster_docs), 1)
        source_mix_counter = Counter(doc["source"] for doc in cluster_docs)
        source_count = len(source_mix_counter)
        temporal = _temporal_metrics(cluster_docs, window_months)
        maturity_score = _legacy_maturity_score(cluster.maturity_stage, cluster.horizon_score)
        momentum_score = round(min(100.0, max(0.0, 50.0 + temporal["growth_ratio"] * 35.0 + temporal["recent_share"] * 35.0)), 1)
        novelty_score = round(
            min(
                100.0,
                max(
                    0.0,
                    0.45 * (100.0 - maturity_score)
                    + 30.0 * temporal["recent_share"]
                    + 18.0 * (1.0 - min(1.0, len(cluster_docs) / 8.0))
                    + max(0.0, temporal["growth_ratio"]) * 12.0,
                ),
            ),
            1,
        )
        uncertainty_score = round(
            min(
                100.0,
                max(
                    0.0,
                    35.0 * (1.0 - min(1.0, len(cluster_docs) / 8.0))
                    + 25.0 * (1.0 - min(1.0, source_count / 5.0))
                    + 20.0 * (1.0 - min(1.0, temporal["active_months"] / 6.0))
                    + 20.0 * (1.0 - min(1.0, avg_score / 100.0)),
                ),
            ),
            1,
        )
        weak_signal_flag = len(cluster_docs) <= 3 and novelty_score >= 55.0
        hype_stage = _legacy_hype_stage(cluster.maturity_stage, momentum_score, weak_signal_flag)
        signal_state = _cluster_signal_state(len(cluster_docs), novelty_score / 100.0, temporal["growth_ratio"])
        taxonomy_matches = _taxonomy_matches(cluster.category or "Innovación General", list(cluster.keywords))
        cluster_quality = _cluster_quality(avg_score, source_count, temporal["active_months"], cluster.category or "Innovación General")
        impact_targets = _impact_targets(cluster.category or "Innovación General")
        top_documents = _top_documents(cluster_docs, limit=4)
        for doc in top_documents:
            doc["representative_reason"] = _representative_reason(doc)
            doc["taxonomy_matches"] = taxonomy_matches
            doc["cluster_quality_score"] = cluster_quality["score"]
            doc["hype_stage"] = hype_stage
        for doc in cluster_docs:
            doc["taxonomy_matches"] = taxonomy_matches
            doc["cluster_quality_score"] = cluster_quality["score"]
            doc["hype_stage"] = hype_stage
        coords = {
            "x": round(mean(doc["x_embed"] for doc in cluster_docs), 4),
            "y": round(mean(doc["y_embed"] for doc in cluster_docs), 4),
        }
        keywords = [keyword for keyword in list(cluster.keywords) if _safe_text(keyword)] or label.split()[:4]
        summary = _safe_text(cluster.summary) or _summary_line(label, cluster.category or "Innovación General", keywords, len(cluster_docs), source_count)
        evidence_line = (
            f"{len(cluster_docs)} documentos, {source_count} fuentes, {temporal['active_months']} meses activos; "
            f"crecimiento {round(temporal['growth_ratio'] * 100)}% con foco en {', '.join(keywords[:3]) or cluster.category.lower()}."
        )
        rationale = (
            f"Cluster generado por el pipeline build_trendmap usando {artifacts['embedding_method']} + {artifacts['cluster_method']}, "
            f"etiquetado con {artifacts['labeling_method']} y consolidado alrededor de {', '.join(keywords[:3]) or label}."
        )
        executive_takeaway = (
            f"{label} concentra evidencia relevante en {cluster.category.lower()} y ya amerita lectura ejecutiva por su "
            f"impacto {round(cluster.impact_score)} y momentum {round(momentum_score)}."
        )
        why_it_matters = (
            f"Importa por su efecto potencial sobre {', '.join(impact_targets[:2])}, con una señal {signal_state} "
            f"y soporte de {source_count} fuentes distintas."
        )
        decision_prompt = _decision_prompt(hype_stage, label, impact_targets)
        breakdowns = _score_breakdowns(
            impact_score=float(cluster.impact_score),
            maturity_score=maturity_score,
            momentum_score=momentum_score,
            novelty_score=novelty_score,
            uncertainty_score=uncertainty_score,
            avg_score=avg_score,
            item_count=len(cluster_docs),
            source_count=source_count,
            active_months=temporal["active_months"],
            recent_share=temporal["recent_share"],
            growth_ratio=temporal["growth_ratio"],
        )
        cluster_payload = {
            "cluster_id": stable_cluster_id,
            "lineage_id": stable_cluster_id,
            "cluster_fingerprint": cluster_fingerprint_map[cluster.cluster_id],
            "history_depth": 1,
            "label": label,
            "subtitle": f"{cluster.category} | {signal_state} | {', '.join(keywords[:2]) or label}",
            "category": cluster.category or "Innovación General",
            "summary": summary,
            "rationale": rationale,
            "keywords": keywords[:6],
            "top_keywords": keywords[:6],
            "relevance": cluster.relevance if cluster.relevance in {"alta", "media", "baja"} else ("alta" if avg_score >= 75 else "media" if avg_score >= 50 else "baja"),
            "item_count": len(cluster_docs),
            "documents": len(cluster_docs),
            "effective_documents": len(cluster_docs),
            "impact_score": round(float(cluster.impact_score), 1),
            "avg_score": avg_score,
            "maturity_score": maturity_score,
            "horizon_score": round(float(cluster.horizon_score), 3),
            "momentum_score": momentum_score,
            "novelty_score": novelty_score,
            "novelty_band": _score_band(novelty_score),
            "uncertainty_score": uncertainty_score,
            "maturity_stage": cluster.maturity_stage if cluster.maturity_stage in _GARTNER_STAGES else "innovation_trigger",
            "hype_stage": hype_stage,
            "direction": temporal["direction"],
            "growth_ratio": round(temporal["growth_ratio"], 2),
            "acceleration_ratio": round(temporal["acceleration_ratio"], 2),
            "weak_signal_flag": weak_signal_flag,
            "signal_state": signal_state,
            "taxonomy_matches": taxonomy_matches,
            "cluster_quality": cluster_quality,
            "maturity_score_breakdown": breakdowns["maturity"],
            "impact_score_breakdown": breakdowns["impact"],
            "momentum_score_breakdown": breakdowns["momentum"],
            "novelty_score_breakdown": breakdowns["novelty"],
            "uncertainty_score_breakdown": breakdowns["uncertainty"],
            "hull_polygon": [list(point) for point in cluster.hull_polygon],
            "coords": coords,
            "articles": [doc["id"] for doc in cluster_docs],
            "top_documents": top_documents[:3],
            "representative_documents": top_documents,
            "source_mix": [{"source": source, "count": count} for source, count in source_mix_counter.most_common()],
            "source_count": source_count,
            "active_months": temporal["active_months"],
            "impact_targets": impact_targets,
            "evidence_line": evidence_line,
            "insight_evidence": [
                {"type": "coverage", "detail": f"{len(cluster_docs)} documentos, {source_count} fuentes, {temporal['active_months']} meses activos"},
                {"type": "tempo", "detail": f"direccion {temporal['direction']}, crecimiento {round(temporal['growth_ratio'] * 100)}%, aceleracion {round(temporal['acceleration_ratio'] * 100)}%"},
                {"type": "methodology", "detail": f"maturity base {cluster.maturity_stage}, silhouette global {artifacts['silhouette_score']}"},
            ],
            "executive_takeaway": executive_takeaway,
            "what_is_happening": summary,
            "why_it_matters": why_it_matters,
            "decision_prompt": decision_prompt,
            "dominant_risk": None,
        }
        clusters_payload.append(cluster_payload)
        taxonomy_breakdown[cluster_payload["category"]] += len(cluster_docs)
        for keyword in keywords:
            keyword_counter[keyword.lower()] += 1

    clusters_payload.sort(key=lambda item: (item["impact_score"], item["momentum_score"], item["item_count"]), reverse=True)
    document_count = len(documents_payload)
    unclustered_count = sum(1 for doc in documents_payload if doc["cluster_id"] == "sin_cluster")
    clustered_count = document_count - unclustered_count
    cluster_coverage = round((clustered_count / max(document_count, 1)) * 100, 1)
    unclustered_ratio = round((unclustered_count / max(document_count, 1)) * 100, 1)
    quality_avg = round(mean(cluster["cluster_quality"]["score"] for cluster in clusters_payload), 1) if clusters_payload else 0.0
    coherence_avg = round(mean(cluster["cluster_quality"]["coherence"] for cluster in clusters_payload), 1) if clusters_payload else 0.0
    taxonomy_coverage = round((sum(taxonomy_breakdown.values()) / max(document_count, 1)) * 100, 1)
    keyword_usefulness_ratio = round(
        (
            sum(1 for keyword in keyword_counter if keyword not in _GENERIC_KEYWORDS)
            / max(len(keyword_counter), 1)
        )
        * 100,
        1,
    )
    duplicate_pressure_avg = round(mean(cluster["cluster_quality"]["duplicate_pressure"] for cluster in clusters_payload), 1) if clusters_payload else 0.0
    weak_signal_clusters = [cluster for cluster in clusters_payload if cluster["weak_signal_flag"]][:6]
    source_mix = Counter(doc["source"] for doc in documents_payload)
    monthly_volume = Counter((_safe_text(doc["date"])[:7] if _safe_text(doc["date"]) else "unknown") for doc in documents_payload)

    timeline: list[dict[str, Any]] = []
    for cluster in clusters_payload:
        cluster_months = Counter(
            (_safe_text(doc["date"])[:7] if _safe_text(doc["date"]) else "unknown")
            for doc in documents_payload
            if doc["cluster_id"] == cluster["cluster_id"]
        )
        for bucket, count in sorted(cluster_months.items()):
            timeline.append(
                {
                    "date": bucket,
                    "bucket": bucket,
                    "topic": cluster["label"],
                    "cluster_id": cluster["cluster_id"],
                    "count": count,
                    "avg_score": cluster["avg_score"],
                    "momentum_score": cluster["momentum_score"],
                }
            )

    top_documents = _top_documents(documents_payload, limit=10)
    for doc in top_documents:
        doc["representative_reason"] = _representative_reason(doc)

    cluster_cards = [
        {
            "cluster_id": cluster["cluster_id"],
            "label": cluster["label"],
            "subtitle": cluster["subtitle"],
            "category": cluster["category"],
            "summary": cluster["summary"],
            "executive_takeaway": cluster["executive_takeaway"],
            "why_it_matters": cluster["why_it_matters"],
            "decision_prompt": cluster["decision_prompt"],
            "evidence_line": cluster["evidence_line"],
            "signal_state": cluster["signal_state"],
            "source_count": cluster["source_count"],
            "active_months": cluster["active_months"],
            "impact_targets": cluster["impact_targets"],
            "impact_score": cluster["impact_score"],
            "maturity_score": cluster["maturity_score"],
            "momentum_score": cluster["momentum_score"],
            "novelty_score": cluster["novelty_score"],
            "hype_stage": cluster["hype_stage"],
            "weak_signal_flag": cluster["weak_signal_flag"],
            "item_count": cluster["item_count"],
            "quality_score": cluster["cluster_quality"]["score"],
            "top_keywords": cluster["top_keywords"][:5],
        }
        for cluster in clusters_payload
    ]

    trend_cards = [
        {
            "label": cluster["label"],
            "category": cluster["category"],
            "stage": cluster["hype_stage"],
            "impact_score": cluster["impact_score"],
            "momentum_score": cluster["momentum_score"],
            "why_it_matters": cluster["why_it_matters"],
            "decision_prompt": cluster["decision_prompt"],
        }
        for cluster in clusters_payload[:8]
    ]

    insights = [
        f"{cluster['label']}: {cluster['summary']} Impacto {round(cluster['impact_score'])}, madurez {round(cluster['maturity_score'])} y momentum {round(cluster['momentum_score'])}."
        for cluster in clusters_payload[:4]
    ]
    if weak_signal_clusters:
        insights.append("Weak signals priorizados: " + ", ".join(cluster["label"] for cluster in weak_signal_clusters[:3]) + ".")
    if unclustered_ratio >= 20:
        insights.append(f"El {unclustered_ratio}% del corpus quedo sin cluster y requiere revision de ruido o dispersion tematica.")

    recommendations = [cluster["decision_prompt"] for cluster in clusters_payload[:3]]
    if weak_signal_clusters:
        recommendations.append("Separar weak signals del resto del portafolio para evitar que pierdan visibilidad frente al volumen dominante.")

    executive_summary = (
        f"El analisis build_trendmap procesó {document_count} documentos en {window_months} meses y consolidó "
        f"{len(clusters_payload)} clusters utiles. Destacan {', '.join(cluster['label'] for cluster in clusters_payload[:3]) or 'senales dispersas'}, "
        f"con cobertura {cluster_coverage}%, calidad media {quality_avg}/100 y silhouette {artifacts['silhouette_score']}."
    )

    risk_signals = [
        {
            "type": cluster["label"],
            "description": cluster["executive_takeaway"],
            "severity": "H" if cluster["impact_score"] >= 75 else "M" if cluster["impact_score"] >= 55 else "L",
            "related_clusters": [cluster["cluster_id"]],
        }
        for cluster in clusters_payload[:6]
    ]

    super_clusters = []
    for super_cluster in response.super_clusters:
        mapped_clusters = [cluster_id_map.get(cluster_id, cluster_id) for cluster_id in super_cluster.clusters]
        related = [cluster for cluster in clusters_payload if cluster["cluster_id"] in mapped_clusters]
        super_clusters.append(
            {
                "category": super_cluster.category,
                "clusters": mapped_clusters,
                "hull_polygon": [list(point) for point in super_cluster.hull_polygon],
                "total_items": super_cluster.total_items,
                "avg_impact": round(float(super_cluster.avg_impact), 1),
                "avg_momentum": round(mean(cluster["momentum_score"] for cluster in related), 1) if related else 0.0,
            }
        )

    return {
        "report_type": "trend_mapping",
        "generated_at": response.meta.generated_at,
        "window_months": window_months,
        "version": 3,
        "methodology_version": _METHOD_VERSION,
        "meta": {
            "generated_at": response.meta.generated_at,
            "total_articles": response.meta.total_articles,
            "total_papers": response.meta.total_papers,
            "total_filtered": document_count,
            "total_clusters": len(clusters_payload),
            "clustered_documents": clustered_count,
            "unclustered_documents": unclustered_count,
            "input_documents": input_document_count,
            "relevance_filtered_documents": filtered_document_count,
            "min_relevance_score": threshold,
            "total_categories": len(super_clusters),
            "silhouette_score": artifacts["silhouette_score"],
            "methodology_version": _METHOD_VERSION,
        },
        "summary": {
            "total_documents": document_count,
            "input_documents": input_document_count,
            "relevance_filtered_documents": filtered_document_count,
            "min_relevance_score": threshold,
            "total_clusters": len(clusters_payload),
            "clustered_documents": clustered_count,
            "unclustered_documents": unclustered_count,
            "dominant_topics": [cluster["label"] for cluster in clusters_payload[:5]],
            "emerging_topics": [cluster["label"] for cluster in clusters_payload if cluster["hype_stage"] in {"weak_signal", "innovation_trigger", "rising_attention"}][:4],
            "consolidating_topics": [cluster["label"] for cluster in clusters_payload if cluster["hype_stage"] in {"consolidation", "productive_adoption"}][:4],
            "weak_signal_topics": [cluster["label"] for cluster in weak_signal_clusters],
            "source_diversity": len(source_mix),
            "avg_relevance": round(mean(doc["score"] for doc in documents_payload), 1) if documents_payload else 0.0,
            "silhouette_score": artifacts["silhouette_score"],
            "cluster_quality_avg": quality_avg,
            "taxonomy_coverage": taxonomy_coverage,
            "methodology_version": _METHOD_VERSION,
            "executive_summary": executive_summary,
        },
        "clusters": clusters_payload,
        "super_clusters": super_clusters,
        "articles": documents_payload,
        "documents": documents_payload,
        "trends": timeline,
        "charts": {
            "embedding_scatter": documents_payload,
            "cluster_scatter": [
                {
                    "label": cluster["label"],
                    "category": cluster["category"],
                    "x": cluster["impact_score"],
                    "y": cluster["maturity_score"],
                    "size": cluster["item_count"],
                }
                for cluster in clusters_payload
            ],
            "cluster_sizes": [{"label": cluster["label"], "count": cluster["item_count"]} for cluster in clusters_payload],
            "source_mix": [{"source": source, "count": count} for source, count in source_mix.most_common()],
            "timeline": timeline,
            "hype_cycle": [
                {
                    "label": cluster["label"],
                    "stage": cluster["hype_stage"],
                    "x": round(cluster["maturity_score"], 2),
                    "y": cluster["impact_score"],
                    "momentum": cluster["momentum_score"],
                }
                for cluster in clusters_payload
            ],
            "monthly_volume": [{"bucket": bucket, "count": count} for bucket, count in sorted(monthly_volume.items())],
        },
        "insights": insights,
        "recommendations": recommendations,
        "risk_signals": risk_signals,
        "top_documents": top_documents,
        "cluster_cards": cluster_cards,
        "trend_cards": trend_cards,
        "taxonomy_breakdown": [{"name": name, "score": round(count / max(document_count, 1), 3)} for name, count in taxonomy_breakdown.most_common(12)],
        "quality_checks": {
            "methodology_version": _METHOD_VERSION,
            "cluster_coherence_avg": coherence_avg,
            "cluster_quality_avg": quality_avg,
            "cluster_coverage": cluster_coverage,
            "noise_ratio": unclustered_ratio,
            "unclustered_ratio": unclustered_ratio,
            "taxonomy_coverage": taxonomy_coverage,
            "keyword_usefulness_ratio": keyword_usefulness_ratio,
            "weak_signal_clusters": len(weak_signal_clusters),
            "input_documents": input_document_count,
            "relevance_filtered_documents": filtered_document_count,
            "min_relevance_score": threshold,
            "low_quality_clusters": len([cluster for cluster in clusters_payload if cluster["cluster_quality"]["score"] < 55]),
            "duplicate_pressure_avg": duplicate_pressure_avg,
            "stability_score_avg": 0.0,
        },
        "filters_metadata": {
            "categories": sorted({cluster["category"] for cluster in clusters_payload}),
            "source_types": sorted({_document_source_type(doc) for doc in eligible_documents}),
            "sources": [source for source, _ in source_mix.most_common(20)],
            "maturity_stages": list(_GARTNER_STAGES),
            "hype_stages": list(_HYPE_STAGE_ORDER),
            "signal_states": sorted({cluster["signal_state"] for cluster in clusters_payload}),
            "comparative_statuses": ["new", "accelerating", "cooling", "stable"],
            "severity_bands": [],
            "novelty_bands": ["low", "medium", "high"],
            "recommended_sort_orders": ["impact", "momentum", "novelty", "size", "quality"],
            "date_range": {
                "start": min((doc["date"] for doc in documents_payload if doc.get("date")), default=None),
                "end": max((doc["date"] for doc in documents_payload if doc.get("date")), default=None),
            },
        },
        "weak_signals": [card for card in cluster_cards if card["weak_signal_flag"]][:6],
        "methodology": {
            "methodology_version": _METHOD_VERSION,
            "representation": {
                "document_text": "titulo + excerpt/texto sobre documentos persistidos del flujo actual",
                "feature_space": artifacts["embedding_method"],
                "projection_method": artifacts["projection_method"],
                "labeling_method": artifacts["labeling_method"],
            },
            "clustering": {
                "cluster_method": artifacts["cluster_method"],
                "noise_label": "sin_cluster",
                "source": "build_trendmap adapter integrado a snapshots v3",
            },
            "scoring": {
                "impact": "heuristica build_trendmap basada en score medio, volumen, recencia y diversidad",
                "maturity": "stage base + horizonte + actividad temporal",
                "momentum": "crecimiento observado sobre meses activos del cluster",
                "novelty": "baja madurez + recencia + escala acotada",
                "uncertainty": "poca escala + baja diversidad + actividad limitada",
            },
        },
        "sources_used": [source for source, _ in source_mix.most_common()],
        "parameters": {
            "window_months": window_months,
            "analysis_engine": "build_trendmap_adapter",
            "cluster_method": artifacts["cluster_method"],
            "vectorizer": "build_trendmap_tfidf_fallback_or_bedrock",
            "projection_method": artifacts["projection_method"],
            "feature_space": artifacts["embedding_method"],
            "representation_mode": "build_trendmap_title_excerpt_text",
            "min_relevance_score": threshold,
            "relevance_filter_operator": ">",
            "input_documents": input_document_count,
            "relevance_filtered_documents": filtered_document_count,
            "embedding_provider": "bedrock" if artifacts["embedding_method"] == "bedrock_titan_v2" else None,
            "embedding_model_id": "build_trendmap_bedrock_titan_v2" if artifacts["embedding_method"] == "bedrock_titan_v2" else None,
            "embedding_attempted": artifacts["embedding_method"] == "bedrock_titan_v2",
            "embedding_error": None,
            "noise_label": "sin_cluster",
            "clustered_documents": clustered_count,
            "unclustered_documents": unclustered_count,
            "cluster_input_dim": 0,
            "methodology_version": _METHOD_VERSION,
            "labeling_method": artifacts["labeling_method"],
            "noise_items": artifacts["noise_items"],
        },
    }
