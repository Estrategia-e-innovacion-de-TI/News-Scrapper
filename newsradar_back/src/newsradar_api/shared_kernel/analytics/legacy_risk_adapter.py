"""Build-riskmap adapter aligned with the build_trendmap clustering flow."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from newsradar_api.shared_kernel.config.paths import load_yaml_file, shared_path

from .advanced_engine import _build_breakdown, _score_band
from .legacy_trend_adapter import build_legacy_trendmap_payload

_METHOD_VERSION = "build_riskmap_adapter_v1"
_GENERIC_RISKS = {
    "",
    "otro",
    "otros",
    "otros riesgos",
    "riesgo",
    "riesgos",
    "general",
    "sin categoria",
    "sin categoría",
    "unknown",
    "none",
}
_GENERIC_KEYWORDS = {
    "news",
    "report",
    "reports",
    "risk",
    "risks",
    "riesgo",
    "riesgos",
    "emerging",
    "emergente",
    "market",
    "markets",
    "company",
    "companies",
    "update",
    "latest",
}
_SEVERITY_MAP = {"H": 0.95, "M": 0.68, "L": 0.38}


def _safe_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _safe_text(value).lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/ ]+", " ", text)).strip()


def _risk_taxonomy() -> list[dict[str, Any]]:
    try:
        data = load_yaml_file(shared_path("topics", "analytics_taxonomy.yaml"))
    except Exception:
        return []
    categories = data.get("risk_categories")
    return categories if isinstance(categories, list) else []


def _display_name(value: str) -> str:
    text = _safe_text(value) or "riesgos emergentes"
    return text[0].upper() + text[1:]


def _normalized_cluster_method(value: Any) -> str:
    normalized = _normalize(value)
    if "hdbscan" in normalized:
        return "hdbscan"
    if "kmeans" in normalized:
        return "kmeans"
    if "single" in normalized:
        return "single_cluster"
    return _safe_text(value) or "unknown"


def _useful_keywords(keywords: list[str], category: str, matched_terms: list[str]) -> list[str]:
    category_tokens = set(_normalize(category).replace("/", " ").split())
    values = [*matched_terms, *keywords]
    selected: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = _safe_text(value)
        normalized = _normalize(clean)
        if not normalized or normalized in seen or normalized in _GENERIC_KEYWORDS:
            continue
        tokens = set(normalized.replace("/", " ").split())
        if tokens and tokens <= category_tokens:
            continue
        seen.add(normalized)
        selected.append(clean)
        if len(selected) >= 8:
            break
    return selected or keywords[:6] or [_display_name(category)]


def _risk_category(cluster: dict[str, Any], docs: list[dict[str, Any]], taxonomy: list[dict[str, Any]]) -> dict[str, Any]:
    text_parts = [
        cluster.get("label"),
        cluster.get("summary"),
        " ".join(cluster.get("keywords") or []),
        " ".join(_safe_text(doc.get("title")) for doc in docs),
        " ".join(_safe_text(doc.get("summary")) for doc in docs),
        " ".join(_safe_text(doc.get("risk_type")) for doc in docs),
    ]
    normalized_text = _normalize(" ".join(_safe_text(part) for part in text_parts))

    explicit_counts = Counter(
        _normalize(doc.get("risk_type"))
        for doc in docs
        if _normalize(doc.get("risk_type")) not in _GENERIC_RISKS
    )

    best: dict[str, Any] | None = None
    best_score = 0.0
    for category in taxonomy:
        name = _safe_text(category.get("name"))
        if not name:
            continue
        normalized_name = _normalize(name)
        score = 0.0
        if normalized_name in normalized_text:
            score += 1.5
        score += explicit_counts.get(normalized_name, 0) * 2.5
        for keyword in category.get("keywords") or []:
            normalized_keyword = _normalize(keyword)
            if normalized_keyword and normalized_keyword in normalized_text:
                score += 1.0
        if score > best_score:
            best = category
            best_score = score

    if best is not None and best_score > 0:
        return {**best, "_score": min(1.0, 0.45 + best_score / 10.0)}

    if explicit_counts:
        name = explicit_counts.most_common(1)[0][0]
        return {"name": name, "keywords": [], "impact_areas": ["continuidad", "cumplimiento", "reputacion"], "_score": 0.62}

    return {"name": "riesgos emergentes", "keywords": [], "impact_areas": ["continuidad", "cumplimiento", "reputacion"], "_score": 0.45}


def _matched_terms(category: dict[str, Any], cluster: dict[str, Any], docs: list[dict[str, Any]]) -> list[str]:
    normalized_text = _normalize(
        " ".join(
            [
                _safe_text(cluster.get("label")),
                _safe_text(cluster.get("summary")),
                " ".join(cluster.get("keywords") or []),
                " ".join(_safe_text(doc.get("title")) for doc in docs),
                " ".join(_safe_text(doc.get("summary")) for doc in docs),
            ]
        )
    )
    matched = []
    for keyword in category.get("keywords") or []:
        if _normalize(keyword) in normalized_text:
            matched.append(str(keyword))
    return matched[:8]


def _risk_label(category: str, keywords: list[str], fallback: str) -> str:
    category_display = _display_name(category)
    focus_terms = [term for term in keywords if _normalize(term) not in _normalize(category)]
    if focus_terms:
        return f"{category_display}: {' / '.join(focus_terms[:2])}"
    fallback_clean = _safe_text(fallback)
    if fallback_clean and _normalize(fallback_clean) != _normalize(category):
        return f"{category_display}: {fallback_clean}"
    return category_display


def _severity_from_docs(cluster: dict[str, Any], docs: list[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    severity_signal = max((_SEVERITY_MAP.get(_safe_text(doc.get("severity")).upper(), 0.0) for doc in docs), default=0.0)
    if severity_signal == 0.0:
        severity_signal = min(1.0, float(cluster.get("impact_score") or 0) / 100.0)
    relevance = min(1.0, float(cluster.get("avg_score") or 0) / 100.0)
    impact = min(1.0, float(cluster.get("impact_score") or 0) / 100.0)
    momentum = min(1.0, float(cluster.get("momentum_score") or 0) / 100.0)
    source_diversity = min(1.0, float(cluster.get("source_count") or 0) / 5.0)
    breakdown = _build_breakdown(
        "0.40 severidad documental + 0.25 relevancia + 0.20 impacto base + 0.10 momentum + 0.05 diversidad",
        {"document_severity": 0.40, "relevance": 0.25, "base_impact": 0.20, "momentum": 0.10, "source_diversity": 0.05},
        {
            "document_severity": severity_signal,
            "relevance": relevance,
            "base_impact": impact,
            "momentum": momentum,
            "source_diversity": source_diversity,
        },
    )
    return breakdown["score"], breakdown


def _persistence_from_cluster(cluster: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    active_months = min(1.0, float(cluster.get("active_months") or 0) / 6.0)
    volume = min(1.0, float(cluster.get("item_count") or 0) / 12.0)
    source_diversity = min(1.0, float(cluster.get("source_count") or 0) / 5.0)
    quality = min(1.0, float((cluster.get("cluster_quality") or {}).get("coherence") or 0) / 100.0)
    breakdown = _build_breakdown(
        "0.40 meses activos + 0.25 volumen + 0.20 diversidad de fuentes + 0.15 coherencia",
        {"active_months": 0.40, "volume": 0.25, "source_diversity": 0.20, "coherence": 0.15},
        {
            "active_months": active_months,
            "volume": volume,
            "source_diversity": source_diversity,
            "coherence": quality,
        },
    )
    return breakdown["score"], breakdown


def _risk_decision(cluster: dict[str, Any], impact_areas: list[str]) -> str:
    target_text = ", ".join(impact_areas[:2]) or "frentes criticos"
    severity = float(cluster.get("risk_severity") or 0)
    momentum = float(cluster.get("momentum_score") or 0)
    persistence = float(cluster.get("persistence_score") or 0)
    if severity >= 75 and momentum >= 55:
        return f"Escalar a revision de riesgo emergente: asignar owner, escenario de impacto y controles candidatos sobre {target_text}."
    if severity >= 65 or persistence >= 60:
        return f"Monitorear con cadencia ejecutiva y validar exposicion interna sobre {target_text}."
    if cluster.get("weak_signal_flag"):
        return f"Mantener como weak signal: buscar evidencia adicional y definir umbral de escalamiento sobre {target_text}."
    return f"Conservar en vigilancia y revisar si aumenta volumen, severidad o recurrencia sobre {target_text}."


def build_legacy_riskmap_payload(
    documents: list[Any],
    window_months: int,
    *,
    min_relevance_score: float = 40.0,
) -> dict[str, Any]:
    payload = build_legacy_trendmap_payload(
        documents,
        window_months,
        min_relevance_score=min_relevance_score,
    )
    taxonomy = _risk_taxonomy()
    docs_by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in payload.get("documents") or []:
        docs_by_cluster[_safe_text(doc.get("cluster_id"))].append(doc)

    id_map: dict[str, str] = {}
    risk_counts = Counter()
    for cluster in payload.get("clusters") or []:
        old_id = _safe_text(cluster.get("cluster_id"))
        new_id = old_id.replace("trend-", "risk-", 1) if old_id.startswith("trend-") else f"risk-{old_id}"
        id_map[old_id] = new_id
        cluster_docs = docs_by_cluster.get(old_id, [])
        risk_category = _risk_category(cluster, cluster_docs, taxonomy)
        category_name = _safe_text(risk_category.get("name")) or "riesgos emergentes"
        matched_terms = _matched_terms(risk_category, cluster, cluster_docs)
        keywords = _useful_keywords(list(cluster.get("keywords") or []), category_name, matched_terms)
        impact_areas = list(risk_category.get("impact_areas") or ["continuidad", "cumplimiento", "reputacion"])
        risk_severity, severity_breakdown = _severity_from_docs(cluster, cluster_docs)
        persistence_score, persistence_breakdown = _persistence_from_cluster(cluster)
        base_impact = float(cluster.get("impact_score") or 0)
        impact_breakdown = _build_breakdown(
            "0.55 severidad de riesgo + 0.45 impacto documental base",
            {"risk_severity": 0.55, "base_impact": 0.45},
            {"risk_severity": risk_severity / 100.0, "base_impact": base_impact / 100.0},
        )
        impact_score = impact_breakdown["score"]
        label = _risk_label(category_name, keywords, _safe_text(cluster.get("label")))
        signal_state = _safe_text(cluster.get("signal_state")) or "active"
        evidence_line = (
            f"{len(cluster_docs)} documentos, {cluster.get('source_count') or 0} fuentes, "
            f"persistencia {round(persistence_score)} y severidad {round(risk_severity)}; foco en {', '.join(keywords[:3])}."
        )
        executive_takeaway = (
            f"{label} concentra una senal de {category_name} con severidad {round(risk_severity)}, "
            f"momentum {round(float(cluster.get('momentum_score') or 0))} y persistencia {round(persistence_score)}."
        )
        why_it_matters = (
            f"Importa por exposicion potencial sobre {', '.join(impact_areas[:3])}, con evidencia documental "
            f"y recurrencia suficiente para seguimiento."
        )
        decision_prompt = _risk_decision({**cluster, "risk_severity": risk_severity, "persistence_score": persistence_score}, impact_areas)
        taxonomy_match = {
            "name": category_name,
            "score": round(float(risk_category.get("_score") or 0.45), 3),
            "matched_terms": keywords[:6],
            "matched_fields": ["risk_type", "cluster_keywords", "title", "summary"],
            "sector_tags": impact_areas,
            "capability_tags": [],
        }

        cluster.update(
            {
                "cluster_id": new_id,
                "lineage_id": new_id,
                "label": label,
                "subtitle": f"{_display_name(category_name)} | {signal_state} | severidad {round(risk_severity)}",
                "category": category_name,
                "dominant_risk": category_name,
                "keywords": keywords[:8],
                "top_keywords": keywords[:8],
                "summary": (
                    f"{label} agrupa {len(cluster_docs)} registros con evidencia de riesgo sobre "
                    f"{', '.join(keywords[:3]) or category_name}."
                ),
                "rationale": (
                    "Cluster generado con el mismo proceso build_trendmap_adapter usado por Trend Mapping "
                    f"y reinterpretado contra taxonomia de riesgos: {category_name}."
                ),
                "impact_score": impact_score,
                "risk_severity": risk_severity,
                "severity_band": _score_band(risk_severity),
                "risk_severity_breakdown": severity_breakdown,
                "persistence_score": persistence_score,
                "persistence_score_breakdown": persistence_breakdown,
                "impact_score_breakdown": impact_breakdown,
                "taxonomy_matches": [taxonomy_match],
                "impact_targets": impact_areas,
                "evidence_line": evidence_line,
                "executive_takeaway": executive_takeaway,
                "what_is_happening": (
                    f"Se observa una agrupacion documental alrededor de {category_name}, "
                    f"con enfasis en {', '.join(keywords[:3])}."
                ),
                "why_it_matters": why_it_matters,
                "decision_prompt": decision_prompt,
            }
        )
        risk_counts[category_name] += int(cluster.get("item_count") or len(cluster_docs))
        for doc in cluster_docs:
            doc["cluster_id"] = new_id
            doc["cluster_label"] = label
            doc["category"] = category_name
            doc["risk_type"] = category_name
            doc["dominant_risk"] = category_name
            doc["taxonomy_matches"] = [taxonomy_match]
            doc["hype_stage"] = cluster.get("hype_stage")

    for key in ("articles", "documents", "top_documents"):
        for doc in payload.get(key) or []:
            old_cluster_id = _safe_text(doc.get("cluster_id"))
            if old_cluster_id in id_map:
                doc["cluster_id"] = id_map[old_cluster_id]

    for cluster in payload.get("clusters") or []:
        cluster["articles"] = [id_map.get(article_id, article_id) for article_id in cluster.get("articles", [])]

    for item in payload.get("trends") or []:
        old_cluster_id = _safe_text(item.get("cluster_id"))
        if old_cluster_id in id_map:
            item["cluster_id"] = id_map[old_cluster_id]
        cluster = next((c for c in payload.get("clusters", []) if c["cluster_id"] == item.get("cluster_id")), None)
        if cluster:
            item["topic"] = cluster["label"]
            item["risk"] = cluster["category"]

    clusters = payload.get("clusters") or []
    clusters.sort(key=lambda item: (item.get("risk_severity") or 0, item.get("momentum_score") or 0, item.get("item_count") or 0), reverse=True)
    total_documents = len(payload.get("documents") or [])
    severity_avg = round(mean(float(cluster.get("risk_severity") or 0) for cluster in clusters), 1) if clusters else 0.0
    persistence_avg = round(mean(float(cluster.get("persistence_score") or 0) for cluster in clusters), 1) if clusters else 0.0

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
            "signal_state": cluster.get("signal_state"),
            "source_count": cluster.get("source_count"),
            "active_months": cluster.get("active_months"),
            "impact_targets": cluster.get("impact_targets") or [],
            "impact_score": cluster["impact_score"],
            "maturity_score": cluster["maturity_score"],
            "momentum_score": cluster["momentum_score"],
            "novelty_score": cluster["novelty_score"],
            "hype_stage": cluster["hype_stage"],
            "weak_signal_flag": cluster["weak_signal_flag"],
            "item_count": cluster["item_count"],
            "quality_score": cluster["cluster_quality"]["score"],
            "top_keywords": cluster["top_keywords"][:5],
            "risk_severity": cluster["risk_severity"],
            "persistence_score": cluster["persistence_score"],
        }
        for cluster in clusters
    ]
    risk_signals = [
        {
            "type": cluster["label"],
            "description": cluster["executive_takeaway"],
            "severity": "H" if cluster["risk_severity"] >= 75 else "M" if cluster["risk_severity"] >= 55 else "L",
            "related_clusters": [cluster["cluster_id"]],
        }
        for cluster in clusters[:8]
    ]
    insights = [
        (
            f"{cluster['label']}: severidad {round(cluster['risk_severity'])}, "
            f"momentum {round(cluster['momentum_score'])}, persistencia {round(cluster['persistence_score'])}. "
            f"{cluster['why_it_matters']}"
        )
        for cluster in clusters[:5]
    ]
    recommendations = [cluster["decision_prompt"] for cluster in clusters[:4]]
    weak_signals = [card for card in cluster_cards if card["weak_signal_flag"]][:6]
    if weak_signals:
        insights.append("Weak signals de riesgo priorizados: " + ", ".join(card["label"] for card in weak_signals[:3]) + ".")
        recommendations.append("Separar weak signals de riesgo de los clusters voluminosos para no perder senales tempranas.")

    payload["report_type"] = "risk_mapping"
    payload["methodology_version"] = _METHOD_VERSION
    payload["clusters"] = clusters
    payload["cluster_cards"] = cluster_cards
    payload["trend_cards"] = [
        {
            "label": cluster["label"],
            "category": cluster["category"],
            "stage": cluster["hype_stage"],
            "impact_score": cluster["risk_severity"],
            "momentum_score": cluster["momentum_score"],
            "why_it_matters": cluster["why_it_matters"],
            "decision_prompt": cluster["decision_prompt"],
        }
        for cluster in clusters[:8]
    ]
    payload["insights"] = insights
    payload["recommendations"] = recommendations
    payload["risk_signals"] = risk_signals
    payload["weak_signals"] = weak_signals
    payload["taxonomy_breakdown"] = [
        {"name": name, "score": round(count / max(total_documents, 1), 3)}
        for name, count in risk_counts.most_common(12)
    ]
    payload["super_clusters"] = [
        {
            "category": category,
            "clusters": [cluster["cluster_id"] for cluster in related],
            "hull_polygon": [[cluster["coords"]["x"], cluster["coords"]["y"]] for cluster in related],
            "total_items": sum(int(cluster.get("item_count") or 0) for cluster in related),
            "avg_impact": round(mean(float(cluster.get("risk_severity") or 0) for cluster in related), 1),
            "avg_momentum": round(mean(float(cluster.get("momentum_score") or 0) for cluster in related), 1),
        }
        for category, related in (
            (category, [cluster for cluster in clusters if cluster["category"] == category])
            for category in risk_counts
        )
    ]
    payload["summary"].update(
        {
            "dominant_risks": [cluster["label"] for cluster in clusters[:5]],
            "dominant_topics": [],
            "emerging_topics": [],
            "consolidating_topics": [],
            "weak_signal_topics": [card["label"] for card in weak_signals],
            "methodology_version": _METHOD_VERSION,
            "executive_summary": (
                f"El build_riskmap_adapter proceso {total_documents} documentos y consolido {len(clusters)} "
                f"clusters de riesgo. Destacan {', '.join(cluster['label'] for cluster in clusters[:3]) or 'senales dispersas'}, "
                f"con severidad media {severity_avg}/100 y persistencia media {persistence_avg}/100."
            ),
        }
    )
    payload["meta"]["methodology_version"] = _METHOD_VERSION
    payload["quality_checks"].update(
        {
            "methodology_version": _METHOD_VERSION,
            "risk_severity_avg": severity_avg,
            "persistence_score_avg": persistence_avg,
        }
    )
    payload["filters_metadata"].update(
        {
            "categories": sorted(risk_counts),
            "severity_bands": ["low", "medium", "high"],
            "recommended_sort_orders": ["severity", "momentum", "persistence", "impact", "novelty", "size"],
        }
    )
    payload["charts"]["cluster_scatter"] = [
        {
            "label": cluster["label"],
            "category": cluster["category"],
            "x": cluster["risk_severity"],
            "y": cluster["persistence_score"],
            "size": cluster["item_count"],
        }
        for cluster in clusters
    ]
    payload["charts"]["hype_cycle"] = [
        {
            "label": cluster["label"],
            "stage": cluster["hype_stage"],
            "x": round(cluster["persistence_score"], 2),
            "y": cluster["risk_severity"],
            "momentum": cluster["momentum_score"],
        }
        for cluster in clusters
    ]
    raw_cluster_method = payload["parameters"].get("cluster_method")
    payload["parameters"].update(
        {
            "analysis_engine": "build_riskmap_adapter",
            "methodology_version": _METHOD_VERSION,
            "report_type": "risk_mapping",
            "risk_taxonomy": "analytics_taxonomy.risk_categories",
            "cluster_method_detail": raw_cluster_method,
            "cluster_method": _normalized_cluster_method(raw_cluster_method),
        }
    )
    payload["methodology"]["methodology_version"] = _METHOD_VERSION
    payload["methodology"]["clustering"]["source"] = "build_trendmap clustering flow adapted for risk mapping snapshots v3"
    payload["methodology"]["scoring"] = {
        "risk_severity": "severidad documental + relevancia + impacto base + momentum + diversidad",
        "persistence": "meses activos + volumen + diversidad de fuentes + coherencia",
        "impact": "severidad de riesgo + impacto documental base",
        "momentum": "crecimiento observado sobre meses activos del cluster",
        "novelty": "baja madurez + recencia + escala acotada",
    }
    return payload
