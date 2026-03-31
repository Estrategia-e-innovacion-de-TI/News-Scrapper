"""Advanced analytics engine for trend and risk mapping snapshots."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import math
import os
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

from newsradar_api.application.config import ApiConfig
from newsradar_api.infrastructure.driven_adapters.bedrock_adapter import BedrockAdapter

try:
    import hdbscan  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    hdbscan = None

try:
    import umap  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    umap = None


_STOPWORDS = {
    "a", "al", "algo", "ante", "antes", "como", "con", "contra", "cuando", "de", "del",
    "desde", "donde", "dos", "el", "ella", "ellas", "ellos", "en", "entre", "era", "es",
    "esa", "ese", "eso", "esta", "este", "esto", "for", "from", "ha", "hasta", "hay",
    "into", "la", "las", "lo", "los", "mas", "more", "muy", "no", "of", "para", "pero",
    "por", "que", "se", "sin", "sobre", "son", "su", "sus", "that", "the", "their", "them",
    "they", "this", "to", "un", "una", "uno", "with", "y",
}


def _credential_hints_present() -> bool:
    hints = [
        "AWS_ACCESS_KEY_ID",
        "AWS_PROFILE",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        "AWS_SESSION_TOKEN",
    ]
    return any(os.getenv(name) for name in hints)


def _embeddings_mode() -> str:
    return os.getenv("NEWSRADAR_ANALYTICS_EMBEDDINGS_MODE", "auto").strip().lower()


def _should_attempt_embeddings() -> bool:
    mode = _embeddings_mode()
    if mode == "disabled":
        return False
    if mode == "enabled":
        return True
    return _credential_hints_present()


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)


def _month_bucket(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    return _as_utc(value).strftime("%Y-%m")


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _document_text(doc: Any) -> str:
    fragments = [
        _safe_text(getattr(doc, "title", "")),
        _safe_text(getattr(doc, "excerpt", "")),
        _safe_text(getattr(doc, "category", "")),
        _safe_text(getattr(doc, "risk_type", "")),
        " ".join(getattr(doc, "matched_keywords", []) or []),
        " ".join(getattr(doc, "materialized_events", []) or []),
        _safe_text(getattr(doc, "source_id", "")),
        _safe_text(getattr(doc, "source_type", "")),
        _safe_text(getattr(doc, "text", ""))[:4000],
    ]
    return " ".join(part for part in fragments if part).strip()


def _embedding_text(doc: Any) -> str:
    fragments = [
        _safe_text(getattr(doc, "title", "")),
        _safe_text(getattr(doc, "excerpt", "")),
        _safe_text(getattr(doc, "category", "")),
        _safe_text(getattr(doc, "risk_type", "")),
        " ".join(getattr(doc, "matched_keywords", []) or []),
        " ".join(getattr(doc, "materialized_events", []) or []),
        _safe_text(getattr(doc, "text", ""))[:2500],
    ]
    return " ".join(part for part in fragments if part).strip()


def _document_category(doc: Any, report_type: str) -> str:
    if report_type == "risk_mapping":
        return _safe_text(getattr(doc, "risk_type", None) or getattr(doc, "category", None) or "Otros riesgos")
    return _safe_text(getattr(doc, "category", None) or getattr(doc, "risk_type", None) or "Otros temas")


def _document_source_kind(doc: Any) -> str:
    source_type = _safe_text(getattr(doc, "source_type", "")).lower()
    if source_type in {"paper", "patent"}:
        return source_type
    if source_type in {"pdf", "institutional_report"}:
        return "paper"
    return "news"


def _select_cluster_count(document_count: int) -> int:
    if document_count <= 2:
        return 1
    heuristic = int(round(math.sqrt(document_count))) or 2
    return max(2, min(heuristic, min(10, document_count)))


def _select_hdbscan_params(document_count: int) -> tuple[int, int]:
    min_cluster_size = max(4, min(18, int(round(math.sqrt(document_count))) or 4))
    min_samples = max(2, min(min_cluster_size - 1, int(round(min_cluster_size * 0.6)) or 2))
    return min_cluster_size, min_samples


def _build_lexical_features(documents: list[Any]) -> tuple[list[str], Any, np.ndarray, np.ndarray]:
    corpus = [_document_text(doc) for doc in documents]
    vectorizer = TfidfVectorizer(
        max_features=1500,
        ngram_range=(1, 2),
        min_df=1,
        stop_words=sorted(_STOPWORDS),
    )
    try:
        matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 1), min_df=1)
        matrix = vectorizer.fit_transform(
            [text or f"documento {index + 1}" for index, text in enumerate(corpus)]
        )
    feature_names = vectorizer.get_feature_names_out()
    reduced = _reduce_matrix(matrix, target_components=32)
    return corpus, matrix, feature_names, np.asarray(reduced, dtype=float)


def _reduce_dense_features(features: np.ndarray, target_components: int = 50) -> np.ndarray:
    rows, cols = features.shape
    if rows <= 1:
        return np.zeros((rows, 2))
    if rows <= 3 or cols <= 2:
        return np.asarray(features, dtype=float)
    max_components = min(target_components, rows - 1, cols)
    if max_components < 2:
        return np.asarray(features, dtype=float)
    reducer = PCA(n_components=max_components, random_state=42)
    return reducer.fit_transform(features)


def _embedding_cache_dir() -> Path:
    return Path("data") / "embeddings_cache" / "analytics"


def _build_embedding_features(documents: list[Any]) -> tuple[np.ndarray | None, dict[str, Any]]:
    metadata = {
        "feature_space": "tfidf_lexical",
        "embedding_provider": None,
        "embedding_model_id": None,
        "embedding_attempted": False,
        "embedding_error": None,
    }
    if not documents or not _should_attempt_embeddings():
        return None, metadata

    cfg = ApiConfig.load()
    texts = [_embedding_text(doc) or _document_text(doc)[:2500] for doc in documents]
    metadata["embedding_attempted"] = True

    try:
        adapter = BedrockAdapter(
            region=cfg.aws_region,
            embed_model=cfg.bedrock_embed_model_id,
            cache_dir=_embedding_cache_dir(),
        )
        embeddings = adapter.get_embeddings(texts)
        features = np.asarray(embeddings, dtype=float)
        if features.ndim != 2 or features.shape[0] != len(documents):
            raise ValueError("unexpected embedding matrix shape")
        if not np.isfinite(features).all():
            raise ValueError("non-finite embedding values")
        if np.allclose(features, 0.0):
            raise ValueError("all embeddings are zero")
        unique_rows = np.unique(np.round(features, decimals=6), axis=0)
        if unique_rows.shape[0] <= 1:
            raise ValueError("embeddings collapsed to a single vector")

        reduced = _reduce_dense_features(features, target_components=50)
        metadata.update(
            {
                "feature_space": "bedrock_embeddings",
                "embedding_provider": "bedrock",
                "embedding_model_id": cfg.bedrock_embed_model_id,
                "embedding_vector_dim": int(features.shape[1]),
                "cluster_input_dim": int(reduced.shape[1]) if reduced.ndim == 2 else 0,
            }
        )
        return np.asarray(reduced, dtype=float), metadata
    except Exception as exc:  # noqa: BLE001
        metadata["embedding_error"] = str(exc)
        return None, metadata


def _reduce_matrix(matrix: Any, target_components: int) -> np.ndarray:
    rows, cols = matrix.shape
    if rows <= 1:
        return np.zeros((rows, 2))
    if rows <= 3 or cols <= 2:
        return np.asarray(matrix.toarray(), dtype=float)
    max_components = min(target_components, rows - 1, cols - 1)
    if max_components < 2:
        return np.asarray(matrix.toarray(), dtype=float)
    reducer = TruncatedSVD(n_components=max_components, random_state=42)
    return reducer.fit_transform(matrix)


def _project_coordinates(features: np.ndarray) -> tuple[np.ndarray, str]:
    rows = len(features)
    if rows == 0:
        return np.zeros((0, 2)), "none"
    if rows == 1:
        return np.zeros((1, 2)), "degenerate"
    if rows == 2:
        return np.array([[0.0, 0.0], [1.0, 0.0]]), "pair_projection"

    if umap is not None:
        try:
            reducer = umap.UMAP(
                n_components=2,
                n_neighbors=max(2, min(15, rows - 1)),
                min_dist=0.15,
                random_state=42,
            )
            return np.asarray(reducer.fit_transform(features), dtype=float), "umap"
        except Exception:
            pass

    if features.shape[1] >= 2:
        return np.asarray(features[:, :2], dtype=float), "svd"

    padding = np.zeros((rows, 2))
    padding[:, 0] = features[:, 0]
    return padding, "padded"


def _cluster_features(features: np.ndarray) -> tuple[np.ndarray, str]:
    rows = len(features)
    if rows == 0:
        return np.array([], dtype=int), "none"
    if rows <= 3:
        return np.zeros(rows, dtype=int), "single_cluster"

    if hdbscan is not None and rows >= 8:
        try:
            min_cluster_size, min_samples = _select_hdbscan_params(rows)
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric="euclidean",
                cluster_selection_method="eom",
            )
            labels = np.asarray(clusterer.fit_predict(features), dtype=int)
            non_noise = {int(label) for label in labels if label >= 0}
            if non_noise:
                return labels, "hdbscan"
        except Exception:
            pass

    cluster_count = _select_cluster_count(rows)
    model = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
    return np.asarray(model.fit_predict(features), dtype=int), "kmeans"


def _normalize_labels(labels: np.ndarray) -> np.ndarray:
    if labels.size == 0:
        return labels
    mapped: dict[int, int] = {}
    next_label = 0
    normalized: list[int] = []
    for raw_label in labels.tolist():
        if raw_label < 0:
            normalized.append(-1)
            continue
        if raw_label not in mapped:
            mapped[raw_label] = next_label
            next_label += 1
        normalized.append(mapped[raw_label])
    return np.asarray(normalized, dtype=int)


def _cluster_terms(matrix: Any, indices: list[int], feature_names: np.ndarray) -> list[str]:
    if not indices:
        return []
    row = np.asarray(matrix[indices].mean(axis=0)).ravel()
    if row.size == 0:
        return []
    top_indices = row.argsort()[-6:][::-1]
    terms = [feature_names[idx] for idx in top_indices if row[idx] > 0]
    return [term for term in terms if term]


def _cluster_label(docs: list[Any], report_type: str, terms: list[str]) -> str:
    counter = Counter(
        _document_category(doc, report_type)
        for doc in docs
        if _document_category(doc, report_type)
    )
    dominant = counter.most_common(1)
    if dominant and dominant[0][0] not in {"Otros temas", "Otros riesgos"}:
        return dominant[0][0]
    if terms:
        return " / ".join(term.title() for term in terms[:2])
    title = _safe_text(getattr(docs[0], "title", "")).strip()
    return title[:80] if title else "Cluster sin etiqueta"


def _top_documents(docs: list[Any], limit: int = 3) -> list[Any]:
    return sorted(docs, key=lambda item: getattr(item, "relevance_score", 0) or 0, reverse=True)[:limit]


def _document_date(doc: Any) -> datetime | None:
    published = getattr(doc, "published_at", None)
    fetched = getattr(doc, "fetched_at", None)
    if isinstance(published, datetime):
        return _as_utc(published)
    if isinstance(fetched, datetime):
        return _as_utc(fetched)
    return None


def _novelty_ratio(docs: list[Any], window_months: int) -> float:
    if not docs:
        return 0.0
    now = datetime.now(timezone.utc)
    window_days = max(window_months, 1) * 30
    recencies: list[float] = []
    for doc in docs:
        doc_date = _document_date(doc) or now
        age_days = max(0.0, (now - doc_date).total_seconds() / 86400.0)
        recencies.append(max(0.0, 1.0 - min(age_days / window_days, 1.0)))
    return round(mean(recencies), 3)


def _growth_direction(month_counter: Counter[str]) -> tuple[str, float]:
    ordered = [count for _, count in sorted(month_counter.items())]
    if len(ordered) <= 1:
        return "stable", 0.0
    delta = ordered[-1] - ordered[0]
    base = max(ordered[0], 1)
    ratio = delta / base
    if ratio > 0.25:
        return "up", round(ratio, 2)
    if ratio < -0.25:
        return "down", round(ratio, 2)
    return "stable", round(ratio, 2)


def _maturity_stage(item_count: int, novelty: float, growth: float) -> str:
    if novelty >= 0.75 and item_count <= 4:
        return "innovation_trigger"
    if growth >= 0.5:
        return "peak_of_inflated_expectations"
    if growth < 0 and item_count <= 4:
        return "trough_of_disillusionment"
    if item_count >= 6:
        return "slope_of_enlightenment"
    return "plateau_of_productivity"


def _cluster_summary(label: str, docs: list[Any], growth_direction: str, avg_score: float) -> str:
    return (
        f"{label} agrupa {len(docs)} documentos con score promedio {avg_score} "
        f"y una senal {growth_direction} en la ventana analizada."
    )


def _base_document_payload(doc: Any, cluster_id: str | None = None, x: float | None = None, y: float | None = None) -> dict[str, Any]:
    doc_date = _document_date(doc)
    payload = {
        "id": str(getattr(doc, "id", getattr(doc, "hash", ""))),
        "title": _safe_text(getattr(doc, "title", "")),
        "source": _safe_text(getattr(doc, "source_id", "")),
        "source_type": _document_source_kind(doc),
        "date": doc_date.isoformat() if doc_date else None,
        "score": getattr(doc, "relevance_score", 0) or 0,
        "url": _safe_text(getattr(doc, "url", "")),
        "summary": _safe_text(getattr(doc, "excerpt", "")) or _safe_text(getattr(doc, "title", "")),
        "category": getattr(doc, "category", None),
        "risk_type": getattr(doc, "risk_type", None),
    }
    if cluster_id is not None:
        payload["cluster_id"] = cluster_id
    if x is not None:
        payload["x_embed"] = round(float(x), 3)
    if y is not None:
        payload["y_embed"] = round(float(y), 3)
    return payload


def generate_report_analysis(
    documents: list[Any],
    report_type: str,
    window_months: int,
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    if not documents:
        empty_summary = {
            "total_documents": 0,
            "total_clusters": 0,
            "clustered_documents": 0,
            "unclustered_documents": 0,
            "dominant_topics": [],
            "dominant_risks": [],
            "source_diversity": 0,
            "avg_relevance": 0.0,
            "silhouette_score": 0.0,
        }
        return {
            "generated_at": generated_at,
            "summary": empty_summary,
            "meta": {
                "generated_at": generated_at,
                "total_filtered": 0,
                "total_clusters": 0,
                "total_categories": 0,
                "total_articles": 0,
                "total_papers": 0,
                "silhouette_score": 0.0,
            },
            "documents": [],
            "clusters": [],
            "super_clusters": [],
            "timeline": [],
            "monthly_volume": [],
            "source_mix": [],
            "top_documents": [],
            "insights": ["No hay documentos persistidos para la ventana solicitada."],
            "executive_summary": "No hay evidencia suficiente para construir un mapa analitico.",
            "recommendations": ["Ejecutar una nueva corrida de ingesta antes de recalcular el reporte."],
            "risk_signals": [],
            "parameters": {
                "window_months": window_months,
                "cluster_method": "none",
                "vectorizer": "tfidf",
                "projection_method": "none",
                "feature_space": "none",
            },
        }

    _, matrix, feature_names, lexical_features = _build_lexical_features(documents)
    embedding_features, embedding_meta = _build_embedding_features(documents)
    clustering_features = embedding_features if embedding_features is not None else lexical_features
    raw_labels, cluster_method = _cluster_features(clustering_features)
    labels = _normalize_labels(raw_labels)
    coordinates, projection_method = _project_coordinates(clustering_features)

    unique_labels = sorted(label for label in set(labels.tolist()) if label >= 0)
    unclustered_indices = [index for index, label in enumerate(labels.tolist()) if label < 0]
    silhouette = 0.0
    if len(unique_labels) >= 2 and len(documents) > len(unique_labels):
        try:
            clustered_rows = [index for index, label in enumerate(labels.tolist()) if label >= 0]
            if len(clustered_rows) > len(unique_labels):
                clustered_features = clustering_features[clustered_rows]
                clustered_labels = labels[clustered_rows]
                silhouette = round(float(silhouette_score(clustered_features, clustered_labels)), 4)
        except Exception:
            silhouette = 0.0

    grouped_indices: dict[int, list[int]] = defaultdict(list)
    for index, label in enumerate(labels.tolist()):
        if label >= 0:
            grouped_indices[int(label)].append(index)

    clusters: list[dict[str, Any]] = []
    document_points: list[dict[str, Any]] = []
    super_cluster_index: dict[str, list[str]] = defaultdict(list)
    timeline: list[dict[str, Any]] = []
    source_mix = Counter(_safe_text(getattr(doc, "source_id", "")) for doc in documents)
    monthly_volume = Counter(_month_bucket(_document_date(doc)) for doc in documents)

    for label_index in unique_labels:
        indices = grouped_indices[label_index]
        docs = [documents[index] for index in indices]
        terms = _cluster_terms(matrix, indices, feature_names)
        label = _cluster_label(docs, report_type, terms)
        cluster_id = f"{report_type}_cluster_{label_index + 1}"
        category = _document_category(docs[0], report_type)
        avg_score = round(mean((getattr(doc, "relevance_score", 0) or 0) for doc in docs), 1)
        month_counter: Counter[str] = Counter()
        cluster_sources = Counter()

        for index, doc in zip(indices, docs, strict=False):
            x_value = round(float(coordinates[index][0]), 3)
            y_value = round(float(coordinates[index][1]), 3)
            document_points.append(
                {
                    **_base_document_payload(doc, cluster_id=cluster_id, x=x_value, y=y_value),
                    "cluster_label": label,
                    "keywords": list(getattr(doc, "matched_keywords", []) or [])[:5],
                    "unclustered": False,
                }
            )
            doc_date = _document_date(doc)
            bucket = _month_bucket(doc_date)
            month_counter[bucket] += 1
            source_id = _safe_text(getattr(doc, "source_id", ""))
            cluster_sources.update([source_id])

        growth_direction, growth_ratio = _growth_direction(month_counter)
        novelty = _novelty_ratio(docs, window_months)
        maturity = _maturity_stage(len(docs), novelty, growth_ratio)
        cluster_x = round(float(np.mean([coordinates[index][0] for index in indices])), 3)
        cluster_y = round(float(np.mean([coordinates[index][1] for index in indices])), 3)
        top_docs = _top_documents(docs)
        cluster_payload = {
            "cluster_id": cluster_id,
            "label": label,
            "category": category,
            "summary": _cluster_summary(label, docs, growth_direction, avg_score),
            "keywords": terms or [label],
            "top_keywords": terms or [label],
            "relevance": "alta" if avg_score >= 75 else "media" if avg_score >= 45 else "baja",
            "item_count": len(docs),
            "documents": len(docs),
            "impact_score": avg_score,
            "avg_score": avg_score,
            "horizon_score": novelty,
            "maturity_stage": maturity,
            "direction": growth_direction,
            "growth_ratio": growth_ratio,
            "hull_polygon": [
                [round(cluster_x - 0.25, 3), round(cluster_y - 0.15, 3)],
                [round(cluster_x + 0.25, 3), round(cluster_y - 0.15, 3)],
                [round(cluster_x + 0.25, 3), round(cluster_y + 0.15, 3)],
                [round(cluster_x - 0.25, 3), round(cluster_y + 0.15, 3)],
            ],
            "coords": {"x": cluster_x, "y": cluster_y},
            "articles": [str(getattr(doc, "id", getattr(doc, "hash", ""))) for doc in docs],
            "top_documents": [_base_document_payload(doc) for doc in top_docs],
            "source_mix": [{"source": source, "count": count} for source, count in cluster_sources.most_common()],
            "executive_takeaway": (
                f"{label} combina {len(cluster_sources)} fuentes y una novedad de {round(novelty * 100)}%."
            ),
            "dominant_risk": category if report_type == "risk_mapping" else None,
        }
        clusters.append(cluster_payload)
        super_cluster_index[category].append(cluster_id)

        for bucket, count in sorted(month_counter.items()):
            timeline.append(
                {
                    "date": bucket,
                    "bucket": bucket,
                    "topic": label,
                    "risk": label,
                    "cluster_id": cluster_id,
                    "count": count,
                    "avg_score": avg_score,
                }
            )

    for index in unclustered_indices:
        doc = documents[index]
        x_value = round(float(coordinates[index][0]), 3)
        y_value = round(float(coordinates[index][1]), 3)
        document_points.append(
            {
                **_base_document_payload(doc, cluster_id="sin_cluster", x=x_value, y=y_value),
                "cluster_label": "Sin cluster",
                "keywords": list(getattr(doc, "matched_keywords", []) or [])[:5],
                "unclustered": True,
            }
        )

    clusters.sort(key=lambda item: (item["item_count"], item["impact_score"]), reverse=True)
    document_points.sort(key=lambda item: item["score"], reverse=True)

    super_clusters: list[dict[str, Any]] = []
    for category, cluster_ids in sorted(super_cluster_index.items(), key=lambda item: len(item[1]), reverse=True):
        related = [cluster for cluster in clusters if cluster["cluster_id"] in cluster_ids]
        super_clusters.append(
            {
                "category": category,
                "clusters": cluster_ids,
                "hull_polygon": [[cluster["coords"]["x"], cluster["coords"]["y"]] for cluster in related],
                "total_items": sum(cluster["item_count"] for cluster in related),
                "avg_impact": round(mean(cluster["impact_score"] for cluster in related), 1),
            }
        )

    total_articles = sum(1 for doc in documents if _document_source_kind(doc) == "news")
    total_papers = sum(1 for doc in documents if _document_source_kind(doc) == "paper")
    top_documents = [_base_document_payload(doc) for doc in _top_documents(documents, limit=10)]
    dominant_labels = [cluster["label"] for cluster in clusters[:5]]
    unclustered_count = len(unclustered_indices)
    clustered_count = len(documents) - unclustered_count

    insights = [
        (
            f"{cluster['label']} lidera con {cluster['item_count']} documentos, "
            f"score {cluster['impact_score']} y tendencia {cluster['direction']}."
        )
        for cluster in clusters[:5]
    ]
    if source_mix:
        main_source, main_count = source_mix.most_common(1)[0]
        source_share = round((main_count / max(len(documents), 1)) * 100, 1)
        insights.append(f"La fuente {main_source} aporta {source_share}% del corpus analizado.")
    if unclustered_count:
        insights.append(
            f"{unclustered_count} documentos quedaron sin cluster por baja densidad semantica."
        )

    executive_summary = (
        f"Se analizaron {len(documents)} documentos; {clustered_count} quedaron agrupados en "
        f"{len(clusters)} clusters coherentes y {unclustered_count} permanecen sin cluster. "
        f"Silhouette {silhouette} y predominio de "
        f"{', '.join(dominant_labels[:3]) or 'sin patrones dominantes'}."
    )

    recommendations = [
        f"Profundizar monitoreo sobre {cluster['label']} y validar si su tendencia {cluster['direction']} persiste."
        for cluster in clusters[:3]
    ] or ["No hay recomendaciones analiticas disponibles."]
    if unclustered_count and (unclustered_count / max(len(documents), 1)) >= 0.35:
        recommendations.append(
            "Revisar el corpus sin cluster para detectar ruido editorial o temas demasiado dispersos."
        )

    risk_signals = [
        {
            "type": cluster["label"],
            "description": cluster["summary"],
            "severity": "H" if cluster["impact_score"] >= 75 else "M" if cluster["impact_score"] >= 45 else "L",
            "related_clusters": [cluster["cluster_id"]],
        }
        for cluster in clusters[:5]
    ]

    summary = {
        "total_documents": len(documents),
        "total_clusters": len(clusters),
        "clustered_documents": clustered_count,
        "unclustered_documents": unclustered_count,
        "dominant_topics": dominant_labels if report_type == "trend_mapping" else [],
        "dominant_risks": dominant_labels if report_type == "risk_mapping" else [],
        "source_diversity": len(source_mix),
        "avg_relevance": round(mean((getattr(doc, "relevance_score", 0) or 0) for doc in documents), 1),
        "silhouette_score": silhouette,
    }

    meta = {
        "generated_at": generated_at,
        "total_articles": total_articles,
        "total_papers": total_papers,
        "total_filtered": len(documents),
        "total_clusters": len(clusters),
        "clustered_documents": clustered_count,
        "unclustered_documents": unclustered_count,
        "total_categories": len(super_clusters),
        "silhouette_score": silhouette,
    }

    return {
        "generated_at": generated_at,
        "summary": summary,
        "meta": meta,
        "documents": document_points,
        "clusters": clusters,
        "super_clusters": super_clusters,
        "timeline": timeline,
        "monthly_volume": [
            {"bucket": bucket, "count": count}
            for bucket, count in sorted(monthly_volume.items())
        ],
        "source_mix": [{"source": source, "count": count} for source, count in source_mix.most_common()],
        "top_documents": top_documents,
        "insights": insights,
        "executive_summary": executive_summary,
        "recommendations": recommendations,
        "risk_signals": risk_signals,
        "parameters": {
            "window_months": window_months,
            "cluster_method": cluster_method,
            "vectorizer": "tfidf_ngram_v1",
            "projection_method": projection_method,
            "feature_space": embedding_meta["feature_space"],
            "embedding_provider": embedding_meta["embedding_provider"],
            "embedding_model_id": embedding_meta["embedding_model_id"],
            "embedding_attempted": embedding_meta["embedding_attempted"],
            "embedding_error": embedding_meta["embedding_error"],
            "noise_label": "sin_cluster",
            "clustered_documents": clustered_count,
            "unclustered_documents": unclustered_count,
            "cluster_input_dim": int(clustering_features.shape[1]) if clustering_features.ndim == 2 else 0,
            **(
                {
                    "hdbscan_min_cluster_size": _select_hdbscan_params(len(documents))[0],
                    "hdbscan_min_samples": _select_hdbscan_params(len(documents))[1],
                }
                if cluster_method == "hdbscan"
                else {}
            ),
            **(
                {
                    "embedding_vector_dim": embedding_meta["embedding_vector_dim"],
                }
                if embedding_meta.get("embedding_vector_dim")
                else {}
            ),
        },
    }
