"""Advanced analytics engine for trend and risk mapping snapshots.

This module keeps the backend as the analytical source of truth. The frontend
only receives prepared snapshots and chart payloads.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import math
import os
from pathlib import Path
import re
from statistics import mean
from typing import Any
import unicodedata

import numpy as np
from scipy.spatial import ConvexHull
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity

from newsradar_api.application.config import ApiConfig
from newsradar_api.infrastructure.driven_adapters.bedrock_adapter import BedrockAdapter
from newsradar_api.shared_kernel.config.paths import load_yaml_file, shared_path

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
    "they", "this", "to", "un", "una", "uno", "with", "y", "you", "your", "ours", "ourselves",
    "we", "our", "us", "said", "says", "according", "today", "new", "will", "can", "could",
    "would", "may", "might", "also", "via", "among", "across", "around", "after", "before",
    "during", "including", "based", "using", "used", "use",
}

_GENERIC_TERMS = {
    "news", "report", "reports", "latest", "breaking", "update", "updates", "global", "world",
    "market", "markets", "sector", "industry", "company", "companies", "group", "groups",
    "technology", "technologies", "tech", "business", "services", "service", "analysis",
    "insight", "insights", "article", "articles", "source", "sources", "year", "years",
    "week", "weeks", "month", "months", "today", "new",
}

_DISPLAY_TOKEN_MAP = {
    "ai": "AI",
    "ia": "IA",
    "llm": "LLM",
    "ml": "ML",
    "nlp": "NLP",
    "api": "API",
    "gpu": "GPU",
    "iot": "IoT",
    "5g": "5G",
    "vr": "VR",
    "ar": "AR",
    "fintech": "Fintech",
    "blockchain": "Blockchain",
    "pqc": "PQC",
}

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

_DEFAULT_TAXONOMY = {
    "version": "analytics_taxonomy_fallback_v1",
    "generic_terms": sorted(_GENERIC_TERMS),
    "adoption_terms": ["deployment", "launch", "implementation", "production", "adoption"],
    "exploration_terms": ["pilot", "prototype", "proof of concept", "research", "study", "paper"],
    "strong_source_weights": {
        "news": 0.48,
        "rss": 0.52,
        "paper": 0.82,
        "patent": 0.85,
        "pdf": 0.75,
        "institutional_report": 0.86,
    },
    "strong_source_ids": {"arxiv": 0.8, "wef": 0.95, "allianz": 0.92, "marsh": 0.92, "zurich": 0.9},
    "trend_categories": [
        {"name": "Inteligencia Artificial", "keywords": ["ai", "ia", "llm", "agent", "copilot", "generative ai"], "sector_tags": ["operaciones"], "capability_tags": ["automatizacion"]},
        {"name": "Ciberseguridad", "keywords": ["cyber", "ciber", "ransomware", "phishing", "malware", "zero trust"], "sector_tags": ["continuidad"], "capability_tags": ["proteccion"]},
        {"name": "Blockchain / Cripto", "keywords": ["blockchain", "tokenization", "tokenizacion", "stablecoin", "crypto"], "sector_tags": ["pagos"], "capability_tags": ["tokenizacion"]},
        {"name": "Cloud / Data", "keywords": ["cloud", "data", "datos", "lakehouse", "gpu", "observability"], "sector_tags": ["arquitectura"], "capability_tags": ["datos"]},
        {"name": "Fintech / Banca Digital", "keywords": ["banking", "banca", "payments", "wallet", "lending"], "sector_tags": ["clientes"], "capability_tags": ["servicio"]},
        {"name": "Regulacion", "keywords": ["regulation", "regulatory", "compliance", "governance"], "sector_tags": ["cumplimiento"], "capability_tags": ["control"]},
        {"name": "Computacion Cuantica", "keywords": ["quantum", "cuantica", "qubit", "pqc"], "sector_tags": ["seguridad"], "capability_tags": ["experimentacion"]},
        {"name": "Innovacion General", "keywords": ["modernization", "modernizacion", "microservices", "enterprise architecture"], "sector_tags": ["transformacion"], "capability_tags": ["modernizacion"]},
    ],
    "risk_categories": [
        {"name": "ciberseguridad", "keywords": ["cyber", "ciber", "ransomware", "phishing", "malware", "breach"], "impact_areas": ["datos", "continuidad"]},
        {"name": "desinformacion / malinformacion", "keywords": ["disinformation", "misinformation", "deepfake", "fraud"], "impact_areas": ["reputacion", "fraude"]},
        {"name": "clima / naturaleza", "keywords": ["climate", "clima", "flood", "wildfire", "drought"], "impact_areas": ["infraestructura"]},
        {"name": "geopolitica / geoeconomia", "keywords": ["geopolitics", "sanctions", "trade war", "supply chain"], "impact_areas": ["cadena de suministro"]},
        {"name": "riesgo de IA", "keywords": ["ai risk", "model risk", "jailbreak", "prompt injection"], "impact_areas": ["modelo", "cumplimiento"]},
        {"name": "regulacion / cumplimiento", "keywords": ["regulation", "compliance", "aml", "sanction"], "impact_areas": ["cumplimiento"]},
        {"name": "terceros / cadena de suministro", "keywords": ["third party", "vendor risk", "dependency", "outsourc"], "impact_areas": ["continuidad"]},
        {"name": "fraude / crimen financiero", "keywords": ["fraud", "laundering", "scam", "mule"], "impact_areas": ["perdida financiera"]},
        {"name": "reputacional", "keywords": ["reputation", "reputational", "trust erosion"], "impact_areas": ["marca"]},
        {"name": "resiliencia operacional", "keywords": ["outage", "downtime", "operational resilience", "business continuity"], "impact_areas": ["continuidad"]},
        {"name": "riesgos sistemicos emergentes", "keywords": ["systemic risk", "contagion", "structural vulnerability"], "impact_areas": ["sistema"]},
    ],
}


@dataclass(slots=True)
class DocumentProfile:
    document_id: str
    normalized_title: str
    normalized_excerpt: str
    normalized_text: str
    normalized_keywords: str
    month_bucket: str
    source_kind: str
    source_weight: float
    taxonomy_matches: list[dict[str, Any]]
    primary_taxonomy: str
    primary_taxonomy_score: float
    adoption_signal: float
    exploration_signal: float
    materiality_signal: float
    recency_signal: float
    relevance_signal: float
    boilerplate_penalty: float
    duplicate_signature: str


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


@lru_cache(maxsize=1)
def _taxonomy_config() -> dict[str, Any]:
    path = shared_path("topics", "analytics_taxonomy.yaml")
    if path.exists():
        data = load_yaml_file(path)
        merged = dict(_DEFAULT_TAXONOMY)
        merged.update({key: value for key, value in data.items() if value is not None})
        return merged
    return dict(_DEFAULT_TAXONOMY)


def _taxonomy_categories(report_type: str) -> list[dict[str, Any]]:
    config = _taxonomy_config()
    key = "risk_categories" if report_type == "risk_mapping" else "trend_categories"
    categories = config.get(key)
    return categories if isinstance(categories, list) else []


def _adoption_terms() -> tuple[str, ...]:
    value = _taxonomy_config().get("adoption_terms") or []
    return tuple(str(item).lower() for item in value)


def _exploration_terms() -> tuple[str, ...]:
    value = _taxonomy_config().get("exploration_terms") or []
    return tuple(str(item).lower() for item in value)


def _configured_generic_terms() -> set[str]:
    value = _taxonomy_config().get("generic_terms") or []
    return _GENERIC_TERMS | {str(item).lower() for item in value}


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


def _normalize_text(value: str) -> str:
    stripped = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    lowered = stripped.lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _tokenize(value: str) -> list[str]:
    generic_terms = _configured_generic_terms()
    return [
        token
        for token in _normalize_text(value).split()
        if len(token) >= 3 and token not in _STOPWORDS and token not in generic_terms
    ]


def _clean_term(term: str) -> str | None:
    tokens = _tokenize(term)
    if not tokens:
        return None
    return " ".join(tokens[:4])


def _display_term(term: str) -> str:
    return " ".join(_DISPLAY_TOKEN_MAP.get(token, token.title()) for token in term.split())


def _meaningful_terms(terms: list[str], limit: int = 6) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in terms:
        cleaned_term = _clean_term(term)
        if not cleaned_term:
            continue
        normalized = cleaned_term.replace(" ", "")
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(cleaned_term)
        if len(cleaned) >= limit:
            break
    return cleaned


def _fallback_terms_from_docs(docs: list[Any], limit: int = 6) -> list[str]:
    counter: Counter[str] = Counter()
    for doc in docs:
        for keyword in getattr(doc, "matched_keywords", []) or []:
            cleaned = _clean_term(_safe_text(keyword))
            if cleaned:
                counter[cleaned] += 2.5

        title_tokens = _tokenize(_safe_text(getattr(doc, "title", "")))
        for size, weight in ((3, 2.0), (2, 1.6), (1, 0.8)):
            if len(title_tokens) < size:
                continue
            for index in range(len(title_tokens) - size + 1):
                phrase = " ".join(title_tokens[index:index + size])
                cleaned = _clean_term(phrase)
                if cleaned:
                    counter[cleaned] += weight
    return [term for term, _ in counter.most_common(limit)]


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
        _safe_text(getattr(doc, "text", ""))[:5000],
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


def _document_source_kind(doc: Any) -> str:
    source_type = _safe_text(getattr(doc, "source_type", "")).lower()
    if source_type in {"paper", "patent"}:
        return source_type
    if source_type in {"pdf", "institutional_report"}:
        return source_type
    if source_type == "rss":
        return "rss"
    return "news"


def _document_date(doc: Any) -> datetime | None:
    published = getattr(doc, "published_at", None)
    fetched = getattr(doc, "fetched_at", None)
    if isinstance(published, datetime):
        return _as_utc(published)
    if isinstance(fetched, datetime):
        return _as_utc(fetched)
    return None


def _source_weight(doc: Any) -> float:
    config = _taxonomy_config()
    source_id = _normalize_text(_safe_text(getattr(doc, "source_id", ""))).replace(" ", "_")
    strong_source_ids = {
        _normalize_text(str(key)).replace(" ", "_"): float(value)
        for key, value in (config.get("strong_source_ids") or {}).items()
    }
    for key, weight in strong_source_ids.items():
        if key and key in source_id:
            return max(0.35, min(weight, 1.0))
    source_kind = _document_source_kind(doc)
    weight = float((config.get("strong_source_weights") or {}).get(source_kind, 0.5))
    return max(0.35, min(weight, 1.0))


def _term_signal(text: str, terms: tuple[str, ...]) -> float:
    if not text or not terms:
        return 0.0
    hits = 0
    for term in terms:
        norm_term = _normalize_text(term)
        if norm_term and norm_term in text:
            hits += 1
    if hits == 0:
        return 0.0
    return min(1.0, hits / max(3, len(terms) / 2))


def _materiality_signal(doc: Any, normalized_text: str, report_type: str) -> float:
    severity_map = {"H": 0.95, "M": 0.7, "L": 0.4}
    severity = severity_map.get(_safe_text(getattr(doc, "severity", "")).upper(), 0.0)
    impact_terms = (
        ("critical", "disruption", "systemic", "loss", "fraud", "breach", "outage", "sanction", "contagion")
        if report_type == "risk_mapping"
        else ("banking", "banca", "payments", "compliance", "fraud", "customer", "regulation", "credit", "security")
    )
    lexical = _term_signal(normalized_text, impact_terms)
    relevance = float(getattr(doc, "relevance_score", 0) or 0) / 100.0
    return max(severity, min(1.0, 0.45 * lexical + 0.55 * relevance))


def _boilerplate_penalty(normalized_title: str, normalized_excerpt: str) -> float:
    title_tokens = normalized_title.split()
    excerpt_tokens = normalized_excerpt.split()[:20]
    if not title_tokens:
        return 0.0
    generic_terms = _configured_generic_terms()
    title_generic = sum(1 for token in title_tokens if token in generic_terms)
    excerpt_generic = sum(1 for token in excerpt_tokens if token in generic_terms)
    ratio = (title_generic + excerpt_generic * 0.35) / max(len(title_tokens) + len(excerpt_tokens) * 0.35, 1)
    return round(min(1.0, ratio), 3)


def _match_taxonomy(doc: Any, report_type: str) -> list[dict[str, Any]]:
    categories = _taxonomy_categories(report_type)
    if not categories:
        fallback = _safe_text(getattr(doc, "risk_type", None) if report_type == "risk_mapping" else getattr(doc, "category", None))
        return [{"name": fallback or ("Otros riesgos" if report_type == "risk_mapping" else "Innovacion general"), "score": 0.4, "matched_terms": []}]

    title = _normalize_text(_safe_text(getattr(doc, "title", "")))
    excerpt = _normalize_text(_safe_text(getattr(doc, "excerpt", "")))
    text = _normalize_text(_safe_text(getattr(doc, "text", ""))[:1800])
    keywords = _normalize_text(" ".join(getattr(doc, "matched_keywords", []) or []))
    explicit = _normalize_text(_safe_text(getattr(doc, "risk_type", None) if report_type == "risk_mapping" else getattr(doc, "category", None)))

    results: list[dict[str, Any]] = []
    for category in categories:
        name = str(category.get("name") or "").strip()
        keywords_list = [str(item).strip().lower() for item in category.get("keywords") or []]
        if not name or not keywords_list:
            continue
        score = 0.0
        matched_terms: list[str] = []
        for keyword in keywords_list:
            norm_kw = _normalize_text(keyword)
            if not norm_kw:
                continue
            matched = False
            if norm_kw in explicit:
                score += 3.2
                matched = True
            if norm_kw in keywords:
                score += 2.8
                matched = True
            if norm_kw in title:
                score += 2.7
                matched = True
            if norm_kw in excerpt:
                score += 1.8
                matched = True
            if norm_kw in text:
                score += 1.0
                matched = True
            if matched and norm_kw not in matched_terms:
                matched_terms.append(norm_kw)
        if score > 0:
            results.append(
                {
                    "name": name,
                    "score": round(min(1.0, score / 8.0), 3),
                    "matched_terms": matched_terms[:6],
                    "sector_tags": list(category.get("sector_tags") or category.get("impact_areas") or []),
                    "capability_tags": list(category.get("capability_tags") or []),
                }
            )

    if results:
        results.sort(key=lambda item: (item["score"], len(item["matched_terms"])), reverse=True)
        return results[:3]

    explicit_value = _safe_text(getattr(doc, "risk_type", None) if report_type == "risk_mapping" else getattr(doc, "category", None)).strip()
    if explicit_value:
        return [{"name": explicit_value, "score": 0.45, "matched_terms": []}]
    return [{"name": "Otros riesgos" if report_type == "risk_mapping" else "Innovacion general", "score": 0.35, "matched_terms": []}]


def _document_profile(doc: Any, report_type: str, window_months: int) -> DocumentProfile:
    doc_date = _document_date(doc)
    now = datetime.now(timezone.utc)
    window_days = max(window_months, 1) * 30
    normalized_title = _normalize_text(_safe_text(getattr(doc, "title", "")))
    normalized_excerpt = _normalize_text(_safe_text(getattr(doc, "excerpt", "")))
    normalized_text = _normalize_text(_document_text(doc))
    normalized_keywords = _normalize_text(" ".join(getattr(doc, "matched_keywords", []) or []))
    age_days = max(0.0, (now - (doc_date or now)).total_seconds() / 86400.0)
    recency_signal = max(0.0, 1.0 - min(age_days / window_days, 1.0))
    taxonomy_matches = _match_taxonomy(doc, report_type)
    primary = taxonomy_matches[0] if taxonomy_matches else {"name": "", "score": 0.0}
    duplicate_tokens = _tokenize(_safe_text(getattr(doc, "title", "")))[:8]
    duplicate_signature = " ".join(sorted(set(duplicate_tokens))) or _safe_text(getattr(doc, "id", ""))
    return DocumentProfile(
        document_id=str(getattr(doc, "id", getattr(doc, "hash", ""))),
        normalized_title=normalized_title,
        normalized_excerpt=normalized_excerpt,
        normalized_text=normalized_text,
        normalized_keywords=normalized_keywords,
        month_bucket=_month_bucket(doc_date),
        source_kind=_document_source_kind(doc),
        source_weight=_source_weight(doc),
        taxonomy_matches=taxonomy_matches,
        primary_taxonomy=str(primary.get("name") or ""),
        primary_taxonomy_score=float(primary.get("score") or 0.0),
        adoption_signal=_term_signal(normalized_text, _adoption_terms()),
        exploration_signal=_term_signal(normalized_text, _exploration_terms()),
        materiality_signal=_materiality_signal(doc, normalized_text, report_type),
        recency_signal=round(recency_signal, 3),
        relevance_signal=round(float(getattr(doc, "relevance_score", 0) or 0) / 100.0, 3),
        boilerplate_penalty=_boilerplate_penalty(normalized_title, normalized_excerpt),
        duplicate_signature=duplicate_signature,
    )


def _document_category(doc: Any, report_type: str) -> str:
    if report_type == "risk_mapping":
        return _safe_text(getattr(doc, "risk_type", None) or getattr(doc, "category", None) or "Otros riesgos")
    return _safe_text(getattr(doc, "category", None) or getattr(doc, "risk_type", None) or "Otros temas")


def _select_cluster_count(document_count: int) -> int:
    if document_count <= 2:
        return 1
    heuristic = int(round(math.sqrt(document_count))) or 2
    return max(2, min(heuristic, min(12, document_count)))


def _select_hdbscan_params(document_count: int) -> tuple[int, int]:
    min_cluster_size = max(4, min(18, int(round(math.sqrt(document_count))) or 4))
    min_samples = max(2, min(min_cluster_size - 1, int(round(min_cluster_size * 0.6)) or 2))
    return min_cluster_size, min_samples


def _build_lexical_features(documents: list[Any]) -> tuple[list[str], Any, np.ndarray, np.ndarray]:
    corpus = [_document_text(doc) for doc in documents]
    max_df = 0.42 if len(documents) >= 30 else 1.0
    min_df = 2 if len(documents) >= 60 else 1
    vectorizer = TfidfVectorizer(
        max_features=2200,
        ngram_range=(1, 2),
        min_df=min_df,
        max_df=max_df,
        strip_accents="unicode",
        sublinear_tf=True,
        stop_words=sorted(_STOPWORDS),
    )
    try:
        matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        vectorizer = TfidfVectorizer(
            max_features=1200,
            ngram_range=(1, 1),
            min_df=1,
            strip_accents="unicode",
            sublinear_tf=True,
            stop_words=sorted(_STOPWORDS),
        )
        matrix = vectorizer.fit_transform([text or f"documento {index + 1}" for index, text in enumerate(corpus)])
    feature_names = vectorizer.get_feature_names_out()
    reduced = _reduce_matrix(matrix, target_components=40)
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


def _normalize_feature_block(block: np.ndarray, weight: float) -> np.ndarray:
    if block.size == 0:
        return block
    dense = np.asarray(block, dtype=float)
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return (dense / norms) * weight


def _build_auxiliary_features(profiles: list[DocumentProfile], report_type: str) -> tuple[np.ndarray, list[str]]:
    categories = [entry.get("name") for entry in _taxonomy_categories(report_type)]
    categories = [str(item) for item in categories if item]
    numeric_names = [
        "relevance",
        "recency",
        "source_weight",
        "adoption",
        "exploration",
        "materiality",
        "paper_like",
        "patent_like",
        "boilerplate_inverse",
        "taxonomy_strength",
    ]
    rows: list[list[float]] = []
    for profile in profiles:
        row = [
            profile.relevance_signal,
            profile.recency_signal,
            profile.source_weight,
            profile.adoption_signal,
            profile.exploration_signal,
            profile.materiality_signal,
            1.0 if profile.source_kind in {"paper", "pdf", "institutional_report"} else 0.0,
            1.0 if profile.source_kind == "patent" else 0.0,
            1.0 - profile.boilerplate_penalty,
            profile.primary_taxonomy_score,
        ]
        row.extend(1.0 if profile.primary_taxonomy == category else 0.0 for category in categories)
        rows.append(row)
    feature_names = numeric_names + [f"taxonomy::{category}" for category in categories]
    return np.asarray(rows, dtype=float), feature_names


def _combine_feature_spaces(
    lexical_features: np.ndarray,
    auxiliary_features: np.ndarray,
    embedding_features: np.ndarray | None,
) -> tuple[np.ndarray, str]:
    parts: list[np.ndarray] = []
    if embedding_features is not None:
        parts.append(_normalize_feature_block(embedding_features, 0.58))
        parts.append(_normalize_feature_block(lexical_features, 0.27))
        parts.append(_normalize_feature_block(auxiliary_features, 0.15))
        return np.concatenate(parts, axis=1), "hybrid_embeddings_lexical_aux_v2"
    parts.append(_normalize_feature_block(lexical_features, 0.76))
    parts.append(_normalize_feature_block(auxiliary_features, 0.24))
    return np.concatenate(parts, axis=1), "hybrid_lexical_aux_v2"


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
                min_dist=0.12,
                random_state=42,
                metric="cosine",
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
            if non_noise and len(non_noise) <= max(2, rows - 2):
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


def _dominant_category_from_docs(report_type: str, docs: list[Any]) -> str | None:
    explicit = Counter(
        value
        for value in (_document_category(doc, report_type) for doc in docs)
        if value and value not in {"Otros temas", "Otros riesgos", "Innovacion general"}
    )
    if not explicit:
        return None
    return explicit.most_common(1)[0][0]


def _cluster_taxonomy_matches(report_type: str, docs: list[Any], profiles: list[DocumentProfile]) -> list[dict[str, Any]]:
    counter: dict[str, dict[str, Any]] = {}
    for doc, profile in zip(docs, profiles, strict=False):
        explicit = _document_category(doc, report_type)
        if explicit and explicit not in {"Otros temas", "Otros riesgos"}:
            entry = counter.setdefault(explicit, {"name": explicit, "score": 0.0, "matched_terms": set(), "sector_tags": set(), "capability_tags": set()})
            entry["score"] += 0.6
        for match in profile.taxonomy_matches:
            name = str(match.get("name") or "").strip()
            if not name:
                continue
            entry = counter.setdefault(name, {"name": name, "score": 0.0, "matched_terms": set(), "sector_tags": set(), "capability_tags": set()})
            entry["score"] += float(match.get("score") or 0.0)
            entry["matched_terms"].update(match.get("matched_terms") or [])
            entry["sector_tags"].update(match.get("sector_tags") or [])
            entry["capability_tags"].update(match.get("capability_tags") or [])

    matches: list[dict[str, Any]] = []
    for entry in counter.values():
        matches.append(
            {
                "name": entry["name"],
                "score": round(min(1.0, entry["score"] / max(len(docs), 1)), 3),
                "matched_terms": sorted(entry["matched_terms"])[:6],
                "sector_tags": sorted(entry["sector_tags"])[:6],
                "capability_tags": sorted(entry["capability_tags"])[:6],
            }
        )
    matches.sort(key=lambda item: (item["score"], len(item["matched_terms"])), reverse=True)
    if matches:
        return matches[:3]
    fallback = _dominant_category_from_docs(report_type, docs)
    if fallback:
        return [{"name": fallback, "score": 0.45, "matched_terms": []}]
    return [{"name": "Otros riesgos" if report_type == "risk_mapping" else "Innovacion general", "score": 0.35, "matched_terms": []}]


def _candidate_title_phrases(docs: list[Any], limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for doc in docs:
        weight = 1.0 + float(getattr(doc, "relevance_score", 0) or 0) / 100.0
        tokens = _tokenize(_safe_text(getattr(doc, "title", "")))
        for size, multiplier in ((3, 2.0), (2, 1.5), (1, 0.8)):
            if len(tokens) < size:
                continue
            for index in range(len(tokens) - size + 1):
                phrase = " ".join(tokens[index:index + size])
                if phrase and phrase not in _configured_generic_terms():
                    counter[phrase] += weight * multiplier
    phrases = [phrase for phrase, _ in counter.most_common(limit * 2)]
    return _meaningful_terms(phrases, limit=limit)


def _cluster_terms(matrix: Any, indices: list[int], feature_names: np.ndarray, docs: list[Any]) -> list[str]:
    if not indices:
        return []
    row = np.asarray(matrix[indices].mean(axis=0)).ravel()
    if row.size == 0:
        return []
    top_indices = row.argsort()[-40:][::-1]
    scores: Counter[str] = Counter()
    for rank, feature_index in enumerate(top_indices):
        if row[feature_index] <= 0:
            continue
        candidate = _clean_term(str(feature_names[feature_index]))
        if candidate:
            scores[candidate] += max(0.4, 3.2 - rank * 0.12)

    for rank, phrase in enumerate(_candidate_title_phrases(docs, limit=12)):
        cleaned = _clean_term(phrase)
        if cleaned:
            scores[cleaned] += max(0.6, 2.8 - rank * 0.14)

    for doc in docs:
        for keyword in getattr(doc, "matched_keywords", []) or []:
            cleaned = _clean_term(_safe_text(keyword))
            if cleaned:
                scores[cleaned] += 2.1

    selected: list[str] = []
    for term, _ in scores.most_common(30):
        tokens = set(term.split())
        if any(tokens <= set(existing.split()) or set(existing.split()) <= tokens for existing in selected):
            continue
        selected.append(term)
        if len(selected) >= 6:
            break

    if len(selected) < 3:
        for term in _fallback_terms_from_docs(docs, limit=6):
            if term not in selected:
                selected.append(term)
            if len(selected) >= 6:
                break
    return selected[:6]


def _heuristic_category(report_type: str, terms: list[str], docs: list[Any], profiles: list[DocumentProfile]) -> str:
    explicit = _dominant_category_from_docs(report_type, docs)
    if explicit:
        return explicit
    matches = _cluster_taxonomy_matches(report_type, docs, profiles)
    if matches:
        return str(matches[0].get("name") or "")
    return "Otros riesgos" if report_type == "risk_mapping" else "Innovacion general"


def _cluster_label(docs: list[Any], report_type: str, terms: list[str], category: str) -> str:
    phrases = _candidate_title_phrases(docs, limit=6)
    if phrases:
        phrase = _display_term(phrases[0])
        if phrase.lower() != _normalize_text(category):
            return phrase[:72]
    if terms:
        return " / ".join(_display_term(term) for term in terms[:2])[:72]
    if category not in {"Innovacion general", "Otros temas", "Otros riesgos"}:
        return category
    title = _safe_text(getattr(docs[0], "title", "")).strip()
    return title[:80] if title else "Cluster sin etiqueta"


def _top_documents(docs: list[Any], profiles: list[DocumentProfile], limit: int = 4) -> list[Any]:
    profile_by_id = {profile.document_id: profile for profile in profiles}

    def _rank(doc: Any) -> float:
        profile = profile_by_id.get(str(getattr(doc, "id", getattr(doc, "hash", ""))))
        if profile is None:
            return float(getattr(doc, "relevance_score", 0) or 0)
        return (
            profile.relevance_signal * 45
            + profile.recency_signal * 18
            + profile.source_weight * 18
            + profile.primary_taxonomy_score * 12
            + (1.0 - profile.boilerplate_penalty) * 7
        )

    return sorted(docs, key=_rank, reverse=True)[:limit]


def _month_series(window_months: int, now: datetime) -> list[str]:
    months: list[str] = []
    year = now.year
    month = now.month
    for offset in range(max(window_months, 1) - 1, -1, -1):
        shifted_month = month - offset
        shifted_year = year
        while shifted_month <= 0:
            shifted_month += 12
            shifted_year -= 1
        months.append(f"{shifted_year:04d}-{shifted_month:02d}")
    return months


def _temporal_metrics(docs: list[Any], profiles: list[DocumentProfile], window_months: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    ordered_months = _month_series(window_months, now)
    month_counter = Counter(profile.month_bucket for profile in profiles if profile.month_bucket != "unknown")
    counts = [month_counter.get(bucket, 0) for bucket in ordered_months]
    active_months = sum(1 for count in counts if count > 0)
    recurrence = active_months / max(len(ordered_months), 1)
    recent_cutoff = max(1, math.ceil(len(ordered_months) / 3))
    recent = counts[-recent_cutoff:]
    earlier = counts[:-recent_cutoff] or counts[:1]
    recent_avg = float(np.mean(recent)) if recent else 0.0
    earlier_avg = float(np.mean(earlier)) if earlier else 0.0
    base = max(earlier_avg, 1.0)
    growth_ratio = round((recent_avg - earlier_avg) / base, 3)
    prior_recent = counts[-recent_cutoff - 1:-1] or earlier or [0]
    acceleration_ratio = round((counts[-1] - float(np.mean(prior_recent))) / max(float(np.mean(prior_recent)), 1.0), 3)
    direction = "up" if growth_ratio > 0.22 else "down" if growth_ratio < -0.18 else "stable"
    recent_share = float(sum(profile.recency_signal for profile in profiles)) / max(len(profiles), 1)
    novelty = min(1.0, 0.45 * recent_share + 0.35 * (1.0 - recurrence) + 0.20 * float(np.mean([profile.exploration_signal for profile in profiles]) if profiles else 0.0))
    return {
        "month_counter": month_counter,
        "ordered_months": ordered_months,
        "active_months": active_months,
        "recurrence": round(recurrence, 3),
        "growth_ratio": growth_ratio,
        "acceleration_ratio": acceleration_ratio,
        "direction": direction,
        "recent_share": round(recent_share, 3),
        "novelty": round(novelty, 3),
        "counts": counts,
    }


def _growth_direction(month_counter: Counter[str]) -> tuple[str, float]:
    ordered = [count for _, count in sorted(month_counter.items())]
    if len(ordered) <= 1:
        return "stable", 0.0
    delta = ordered[-1] - ordered[0]
    base = max(ordered[0], 1)
    ratio = delta / base
    if ratio > 0.22:
        return "up", round(ratio, 2)
    if ratio < -0.18:
        return "down", round(ratio, 2)
    return "stable", round(ratio, 2)


def _maturity_stage(item_count: int, novelty: float, growth: float) -> str:
    if item_count <= 3 and novelty >= 0.65:
        return "innovation_trigger"
    if growth >= 0.55:
        return "peak_of_inflated_expectations"
    if growth < -0.15 and item_count <= 5:
        return "trough_of_disillusionment"
    if item_count >= 8 and novelty <= 0.45:
        return "plateau_of_productivity"
    return "slope_of_enlightenment"


def _direction_label(direction: str) -> str:
    return {
        "up": "creciente",
        "down": "decreciente",
        "stable": "estable",
    }.get(direction, direction)


def _cluster_signal_state(item_count: int, novelty: float, growth: float) -> str:
    if item_count <= 3 and novelty >= 0.6:
        return "senal debil"
    if growth >= 0.3 and novelty >= 0.45:
        return "tema emergente"
    if item_count >= 6 and growth >= 0:
        return "tema en consolidacion"
    if growth <= -0.18:
        return "tema en correccion"
    return "tema en observacion"


def _coherence_score(features: np.ndarray, indices: list[int]) -> float:
    if len(indices) <= 1:
        return 0.65
    vectors = np.asarray(features[indices], dtype=float)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    normalized = vectors / norms
    centroid = normalized.mean(axis=0, keepdims=True)
    centroid_norm = np.linalg.norm(centroid)
    if centroid_norm == 0.0:
        return 0.0
    centroid /= centroid_norm
    similarities = cosine_similarity(normalized, centroid).ravel()
    return round(float(np.clip(np.mean(similarities), 0.0, 1.0)), 3)


def _centroid(features: np.ndarray, indices: list[int]) -> np.ndarray:
    if not indices:
        return np.zeros((features.shape[1],), dtype=float)
    return np.asarray(features[indices], dtype=float).mean(axis=0)


def _separation_scores(grouped_indices: dict[int, list[int]], features: np.ndarray) -> dict[int, float]:
    centroids = {label: _centroid(features, indices) for label, indices in grouped_indices.items()}
    if len(centroids) <= 1:
        return {label: 0.7 for label in grouped_indices}
    normalized = {}
    for label, centroid in centroids.items():
        norm = np.linalg.norm(centroid)
        normalized[label] = centroid / norm if norm else centroid
    result: dict[int, float] = {}
    for label, centroid in normalized.items():
        nearest = max(
            float(np.dot(centroid, other))
            for other_label, other in normalized.items()
            if other_label != label
        )
        result[label] = round(float(np.clip(1.0 - max(nearest, 0.0), 0.0, 1.0)), 3)
    return result


def _build_breakdown(formula: str, weights: dict[str, float], components: dict[str, float]) -> dict[str, Any]:
    detail = []
    score = 0.0
    for key, weight in weights.items():
        value = round(float(components.get(key, 0.0)) * 100, 1)
        contribution = round(value * weight, 1)
        score += contribution
        detail.append({"name": key, "weight": round(weight, 2), "value": value, "contribution": contribution})
    return {"score": round(score, 1), "formula": formula, "components": detail}


def _cluster_hull(points: list[tuple[float, float]]) -> list[list[float]]:
    if len(points) == 0:
        return []
    if len(points) == 1:
        x_value, y_value = points[0]
        delta = 0.18
        return [
            [round(x_value - delta, 3), round(y_value, 3)],
            [round(x_value, 3), round(y_value - delta, 3)],
            [round(x_value + delta, 3), round(y_value, 3)],
            [round(x_value, 3), round(y_value + delta, 3)],
        ]
    if len(points) == 2:
        (x1, y1), (x2, y2) = points
        delta = 0.15
        return [
            [round(x1 - delta, 3), round(y1 - delta, 3)],
            [round(x2 + delta, 3), round(y1 - delta, 3)],
            [round(x2 + delta, 3), round(y2 + delta, 3)],
            [round(x1 - delta, 3), round(y2 + delta, 3)],
        ]
    pts = np.asarray(points, dtype=float)
    try:
        hull = ConvexHull(pts)
        return [[round(float(pts[index, 0]), 3), round(float(pts[index, 1]), 3)] for index in hull.vertices]
    except Exception:
        return [[round(float(x_value), 3), round(float(y_value), 3)] for x_value, y_value in points]


def _maturity_from_score(score: float) -> str:
    if score < 22:
        return "innovation_trigger"
    if score < 42:
        return "peak_of_inflated_expectations"
    if score < 60:
        return "trough_of_disillusionment"
    if score < 78:
        return "slope_of_enlightenment"
    return "plateau_of_productivity"


def _hype_stage(
    report_type: str,
    *,
    impact_score: float,
    maturity_score: float,
    momentum_score: float,
    novelty_score: float,
    uncertainty_score: float,
    weak_signal_flag: bool,
) -> str:
    if weak_signal_flag:
        return "weak_signal"
    if maturity_score >= 78 and impact_score >= 70:
        return "productive_adoption"
    if maturity_score >= 62 and momentum_score >= 40:
        return "consolidation"
    if impact_score >= 72 and momentum_score >= 62 and maturity_score < 62:
        return "peak_visibility"
    if momentum_score >= 68 and novelty_score >= 50:
        return "rising_attention"
    if novelty_score >= 66 and maturity_score < 40:
        return "innovation_trigger"
    if uncertainty_score >= 58 or momentum_score < 36:
        return "correction"
    return "consolidation" if report_type == "risk_mapping" else "rising_attention"


def _cluster_summary(
    label: str,
    report_type: str,
    docs: list[Any],
    category: str,
    direction: str,
    taxonomy_matches: list[dict[str, Any]],
    impact_score: float,
    maturity_score: float,
    momentum_score: float,
    keywords: list[str],
) -> str:
    evidence = ", ".join(keywords[:3]) if keywords else "senales dispersas"
    taxonomy = taxonomy_matches[0]["name"] if taxonomy_matches else category
    if report_type == "risk_mapping":
        return (
            f"{label} consolida {len(docs)} evidencias en {taxonomy}. "
            f"Combina severidad/impacto {round(impact_score)} y persistencia {round(maturity_score)} "
            f"con una trayectoria {_direction_label(direction)} apoyada por {evidence}."
        )
    return (
        f"{label} articula {len(docs)} documentos alrededor de {taxonomy}. "
        f"El cluster muestra impacto {round(impact_score)}, madurez {round(maturity_score)} y momentum "
        f"{round(momentum_score)} con evidencia concentrada en {evidence}."
    )


def _cluster_takeaway(
    label: str,
    report_type: str,
    category: str,
    weak_signal_flag: bool,
    hype_stage: str,
    impact_score: float,
    maturity_score: float,
    momentum_score: float,
) -> str:
    if report_type == "risk_mapping":
        if weak_signal_flag:
            return f"{label} todavia es una senal debil, pero ya merece seguimiento por su aceleracion y posible materialidad."
        if impact_score >= 75:
            return f"{label} ya opera como riesgo prioritario: combina materialidad alta con persistencia suficiente para afectar decisiones de continuidad y control."
        return f"{label} exige vigilancia activa: su severidad es relevante y su trayectoria {hype_stage.replace('_', ' ')} puede escalar rapido."
    if weak_signal_flag:
        return f"{label} aparece como weak signal util para exploracion temprana antes de que gane visibilidad masiva."
    if maturity_score >= 75:
        return f"{label} ya se mueve hacia adopcion productiva; la prioridad deja de ser exploratoria y pasa a captura disciplinada de valor."
    return f"{label} importa por su combinacion de impacto {round(impact_score)} y momentum {round(momentum_score)}; conviene traducirlo a decisiones de portafolio y capacidades."


def _top_level_insight(cluster: dict[str, Any], report_type: str) -> str:
    label = cluster["label"]
    impact = round(cluster["impact_score"])
    momentum = round(cluster["momentum_score"])
    maturity = round(cluster["maturity_score"])
    if report_type == "risk_mapping":
        severity = round(cluster["risk_severity"])
        return f"{label} domina el snapshot por combinar severidad {severity}, materialidad {impact} y persistencia {maturity}, con momentum {momentum}."
    return f"{label} destaca por impacto {impact}, madurez {maturity} y momentum {momentum}, lo que lo vuelve una tendencia explicable y accionable."


def _representative_reason(profile: DocumentProfile, category: str) -> str:
    reasons: list[str] = []
    if profile.relevance_signal >= 0.8:
        reasons.append("alta relevancia")
    if profile.recency_signal >= 0.65:
        reasons.append("senal reciente")
    if profile.source_weight >= 0.75:
        reasons.append("fuente fuerte")
    if profile.primary_taxonomy and profile.primary_taxonomy == category:
        reasons.append("encaje taxonomico")
    if not reasons:
        reasons.append("pieza representativa")
    return " + ".join(reasons[:3])


def _base_document_payload(
    doc: Any,
    profile: DocumentProfile,
    cluster_id: str | None = None,
    x: float | None = None,
    y: float | None = None,
) -> dict[str, Any]:
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
        "taxonomy_matches": profile.taxonomy_matches,
        "source_weight": round(profile.source_weight * 100, 1),
        "duplicate_signature": profile.duplicate_signature,
        "duplicate_flag": False,
        "recency_score": round(profile.recency_signal * 100, 1),
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
    methodology_version = "analytics_methodology_v3"

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
            "methodology_version": methodology_version,
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
                "methodology_version": methodology_version,
            },
            "documents": [],
            "clusters": [],
            "super_clusters": [],
            "timeline": [],
            "monthly_volume": [],
            "source_mix": [],
            "top_documents": [],
            "cluster_cards": [],
            "trend_cards": [],
            "taxonomy_breakdown": [],
            "weak_signals": [],
            "quality_checks": {
                "methodology_version": methodology_version,
                "cluster_coherence_avg": 0.0,
                "unclustered_ratio": 0.0,
                "taxonomy_coverage": 0.0,
                "keyword_usefulness_ratio": 0.0,
            },
            "filters_metadata": {
                "categories": [],
                "source_types": [],
                "sources": [],
                "maturity_stages": list(_GARTNER_STAGES),
                "hype_stages": list(_HYPE_STAGE_ORDER),
                "recommended_sort_orders": ["impact", "momentum", "novelty", "size", "quality"],
            },
            "insights": ["No hay documentos persistidos para la ventana solicitada."],
            "executive_summary": "No hay evidencia suficiente para construir un mapa analitico.",
            "recommendations": ["Ejecutar una nueva corrida de ingesta antes de recalcular el reporte."],
            "risk_signals": [],
            "parameters": {
                "window_months": window_months,
                "cluster_method": "none",
                "vectorizer": "tfidf_ngram_v1",
                "projection_method": "none",
                "feature_space": "none",
                "representation_mode": "none",
                "methodology_version": methodology_version,
            },
        }

    profiles = [_document_profile(doc, report_type, window_months) for doc in documents]
    duplicate_counts = Counter(profile.duplicate_signature for profile in profiles)
    profile_by_id = {profile.document_id: profile for profile in profiles}

    _, matrix, feature_names, lexical_features = _build_lexical_features(documents)
    auxiliary_features, auxiliary_feature_names = _build_auxiliary_features(profiles, report_type)
    embedding_features, embedding_meta = _build_embedding_features(documents)
    clustering_features, representation_mode = _combine_feature_spaces(
        lexical_features,
        auxiliary_features,
        embedding_features,
    )
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

    separation_scores = _separation_scores(grouped_indices, clustering_features)
    clusters: list[dict[str, Any]] = []
    document_points: list[dict[str, Any]] = []
    super_cluster_index: dict[str, list[str]] = defaultdict(list)
    timeline: list[dict[str, Any]] = []
    source_mix = Counter(_safe_text(getattr(doc, "source_id", "")) for doc in documents)
    monthly_volume = Counter(_month_bucket(_document_date(doc)) for doc in documents)
    quality_scores: list[float] = []
    aggregated_taxonomy = Counter()
    keyword_pool: Counter[str] = Counter()

    for label_index in unique_labels:
        indices = grouped_indices[label_index]
        docs = [documents[index] for index in indices]
        local_profiles = [profiles[index] for index in indices]
        terms = _cluster_terms(matrix, indices, feature_names, docs)
        taxonomy_matches = _cluster_taxonomy_matches(report_type, docs, local_profiles)
        category = _heuristic_category(report_type, terms, docs, local_profiles)
        label = _cluster_label(docs, report_type, terms, category)
        avg_score = round(mean((getattr(doc, "relevance_score", 0) or 0) for doc in docs), 1)
        temporal = _temporal_metrics(docs, local_profiles, window_months)
        direction = temporal["direction"]
        growth_ratio = temporal["growth_ratio"]
        acceleration_ratio = temporal["acceleration_ratio"]
        novelty = temporal["novelty"]
        recurrence = temporal["recurrence"]
        source_kind_diversity = len({profile.source_kind for profile in local_profiles}) / 4.0
        source_diversity = min(1.0, len({_safe_text(getattr(doc, "source_id", "")) for doc in docs}) / max(min(len(docs), 8), 1))
        authority = float(np.mean([profile.source_weight for profile in local_profiles])) if local_profiles else 0.5
        adoption = float(np.mean([profile.adoption_signal for profile in local_profiles])) if local_profiles else 0.0
        exploration = float(np.mean([profile.exploration_signal for profile in local_profiles])) if local_profiles else 0.0
        materiality = float(np.mean([profile.materiality_signal for profile in local_profiles])) if local_profiles else 0.0
        relevance = float(np.mean([profile.relevance_signal for profile in local_profiles])) if local_profiles else 0.0
        taxonomy_focus = float(np.mean([profile.primary_taxonomy_score for profile in local_profiles])) if local_profiles else 0.0
        size_signal = min(1.0, math.log1p(len(docs)) / math.log1p(max(len(documents), 2)))
        coherence = _coherence_score(clustering_features, indices)
        separation = separation_scores.get(label_index, 0.7)
        duplicate_ratio = round(
            max(0.0, 1.0 - len({profile.duplicate_signature for profile in local_profiles}) / max(len(local_profiles), 1)),
            3,
        )
        transversality = round(min(1.0, 0.55 * source_kind_diversity + 0.45 * min(len(taxonomy_matches) / 3.0, 1.0)), 3)

        momentum_components = {
            "growth": min(1.0, max(0.0, (growth_ratio + 1.0) / 2.0)),
            "acceleration": min(1.0, max(0.0, (acceleration_ratio + 1.0) / 2.0)),
            "recent_share": temporal["recent_share"],
            "visibility": min(1.0, 0.55 * size_signal + 0.45 * relevance),
        }
        momentum_breakdown = _build_breakdown(
            "0.40 crecimiento + 0.25 aceleracion + 0.20 recencia + 0.15 visibilidad",
            {"growth": 0.40, "acceleration": 0.25, "recent_share": 0.20, "visibility": 0.15},
            momentum_components,
        )
        momentum_score = momentum_breakdown["score"]

        novelty_components = {
            "recent_share": temporal["recent_share"],
            "low_recurrence": 1.0 - recurrence,
            "exploration": exploration,
            "small_scale": 1.0 - size_signal,
        }
        novelty_breakdown = _build_breakdown(
            "0.45 recencia + 0.30 baja recurrencia + 0.15 exploracion + 0.10 escala pequena",
            {"recent_share": 0.45, "low_recurrence": 0.30, "exploration": 0.15, "small_scale": 0.10},
            novelty_components,
        )
        novelty_score = novelty_breakdown["score"]
        weak_signal_flag = len(docs) <= 3 and novelty_score >= 60 and (momentum_score >= 45 or avg_score >= 70)

        if report_type == "risk_mapping":
            severity_breakdown = _build_breakdown(
                "0.26 relevancia + 0.24 materialidad + 0.18 autoridad + 0.16 diversidad + 0.16 foco taxonomico",
                {"relevance": 0.26, "materiality": 0.24, "authority": 0.18, "source_diversity": 0.16, "taxonomy_focus": 0.16},
                {
                    "relevance": relevance,
                    "materiality": materiality,
                    "authority": authority,
                    "source_diversity": source_diversity,
                    "taxonomy_focus": taxonomy_focus,
                },
            )
            risk_severity = severity_breakdown["score"]
            persistence_breakdown = _build_breakdown(
                "0.40 recurrencia + 0.20 escala + 0.15 autoridad + 0.15 coherencia + 0.10 diversidad",
                {"recurrence": 0.40, "size": 0.20, "authority": 0.15, "coherence": 0.15, "source_diversity": 0.10},
                {
                    "recurrence": recurrence,
                    "size": size_signal,
                    "authority": authority,
                    "coherence": coherence,
                    "source_diversity": source_diversity,
                },
            )
            persistence_score = persistence_breakdown["score"]
            impact_breakdown = _build_breakdown(
                "0.50 severidad + 0.20 persistencia + 0.15 diversidad + 0.15 foco taxonomico",
                {"severity": 0.50, "persistence": 0.20, "source_diversity": 0.15, "taxonomy_focus": 0.15},
                {
                    "severity": risk_severity / 100.0,
                    "persistence": persistence_score / 100.0,
                    "source_diversity": source_diversity,
                    "taxonomy_focus": taxonomy_focus,
                },
            )
            impact_score = impact_breakdown["score"]
            maturity_breakdown = _build_breakdown(
                "0.45 persistencia + 0.20 autoridad + 0.20 foco taxonomico + 0.15 coherencia",
                {"persistence": 0.45, "authority": 0.20, "taxonomy_focus": 0.20, "coherence": 0.15},
                {
                    "persistence": persistence_score / 100.0,
                    "authority": authority,
                    "taxonomy_focus": taxonomy_focus,
                    "coherence": coherence,
                },
            )
            maturity_score = maturity_breakdown["score"]
        else:
            risk_severity = 0.0
            persistence_score = round((0.55 * recurrence + 0.25 * size_signal + 0.20 * coherence) * 100, 1)
            impact_breakdown = _build_breakdown(
                "0.28 relevancia + 0.16 autoridad + 0.14 diversidad + 0.14 escala + 0.14 foco taxonomico + 0.14 transversalidad",
                {"relevance": 0.28, "authority": 0.16, "source_diversity": 0.14, "size": 0.14, "taxonomy_focus": 0.14, "transversality": 0.14},
                {
                    "relevance": relevance,
                    "authority": authority,
                    "source_diversity": source_diversity,
                    "size": size_signal,
                    "taxonomy_focus": taxonomy_focus,
                    "transversality": transversality,
                },
            )
            impact_score = impact_breakdown["score"]
            maturity_breakdown = _build_breakdown(
                "0.28 recurrencia + 0.20 adopcion + 0.16 escala + 0.14 coherencia + 0.12 autoridad + 0.10 baja novedad",
                {"recurrence": 0.28, "adoption": 0.20, "size": 0.16, "coherence": 0.14, "authority": 0.12, "low_novelty": 0.10},
                {
                    "recurrence": recurrence,
                    "adoption": adoption,
                    "size": size_signal,
                    "coherence": coherence,
                    "authority": authority,
                    "low_novelty": 1.0 - min(1.0, novelty_score / 100.0),
                },
            )
            maturity_score = maturity_breakdown["score"]

        uncertainty_breakdown = _build_breakdown(
            "0.30 exploracion + 0.25 baja coherencia + 0.20 baja autoridad + 0.15 duplicidad + 0.10 bajo foco taxonomico",
            {"exploration": 0.30, "low_coherence": 0.25, "low_authority": 0.20, "duplicate_pressure": 0.15, "low_taxonomy_focus": 0.10},
            {
                "exploration": exploration,
                "low_coherence": 1.0 - coherence,
                "low_authority": 1.0 - authority,
                "duplicate_pressure": duplicate_ratio,
                "low_taxonomy_focus": 1.0 - taxonomy_focus,
            },
        )
        uncertainty_score = uncertainty_breakdown["score"]
        quality_score = round((0.38 * coherence + 0.22 * separation + 0.20 * taxonomy_focus + 0.10 * source_diversity + 0.10 * (1.0 - duplicate_ratio)) * 100, 1)
        quality_scores.append(quality_score)

        maturity_stage = _maturity_from_score(maturity_score)
        hype_stage = _hype_stage(
            report_type,
            impact_score=impact_score,
            maturity_score=maturity_score,
            momentum_score=momentum_score,
            novelty_score=novelty_score,
            uncertainty_score=uncertainty_score,
            weak_signal_flag=weak_signal_flag,
        )
        cluster_id = f"{report_type}_cluster_{label_index + 1}"
        cluster_x = round(float(np.mean([coordinates[index][0] for index in indices])), 3)
        cluster_y = round(float(np.mean([coordinates[index][1] for index in indices])), 3)
        top_docs = _top_documents(docs, local_profiles)
        source_counts = Counter(_safe_text(getattr(doc, "source_id", "")) for doc in docs)
        representative_documents = []
        for doc in top_docs:
            profile = profile_by_id[str(getattr(doc, "id", getattr(doc, "hash", "")))]
            payload = _base_document_payload(doc, profile)
            payload["representative_reason"] = _representative_reason(profile, taxonomy_matches[0]["name"] if taxonomy_matches else category)
            representative_documents.append(payload)

        for match in taxonomy_matches:
            aggregated_taxonomy[match["name"]] += match["score"]
        for term in terms:
            keyword_pool[term] += 1

        for index, doc in zip(indices, docs, strict=False):
            profile = profiles[index]
            x_value = round(float(coordinates[index][0]), 3)
            y_value = round(float(coordinates[index][1]), 3)
            payload = _base_document_payload(doc, profile, cluster_id=cluster_id, x=x_value, y=y_value)
            payload.update(
                {
                    "cluster_label": label,
                    "keywords": list(getattr(doc, "matched_keywords", []) or [])[:5],
                    "unclustered": False,
                    "duplicate_flag": duplicate_counts[profile.duplicate_signature] > 1,
                    "cluster_quality_score": quality_score,
                    "hype_stage": hype_stage,
                }
            )
            if report_type == "risk_mapping":
                payload["dominant_risk"] = category
            document_points.append(payload)

        for bucket, count in zip(temporal["ordered_months"], temporal["counts"], strict=False):
            timeline.append(
                {
                    "date": bucket,
                    "bucket": bucket,
                    "topic": label,
                    "risk": label,
                    "cluster_id": cluster_id,
                    "count": count,
                    "avg_score": avg_score,
                    "momentum_score": momentum_score,
                }
            )

        summary = _cluster_summary(
            label,
            report_type,
            docs,
            category,
            direction,
            taxonomy_matches,
            impact_score,
            maturity_score,
            momentum_score,
            [_display_term(term) for term in terms],
        )
        cluster_payload = {
            "cluster_id": cluster_id,
            "label": label,
            "subtitle": f"{taxonomy_matches[0]['name'] if taxonomy_matches else category} · {_cluster_signal_state(len(docs), novelty, growth_ratio)}",
            "category": category,
            "summary": summary,
            "rationale": (
                f"Etiqueta construida con taxonomia dominante {taxonomy_matches[0]['name'] if taxonomy_matches else category}, "
                f"keywords {', '.join(_display_term(term) for term in terms[:3]) or 'N/D'} y documentos representativos de mayor score."
            ),
            "keywords": [_display_term(term) for term in terms] or [label],
            "top_keywords": [_display_term(term) for term in terms] or [label],
            "relevance": "alta" if avg_score >= 75 else "media" if avg_score >= 50 else "baja",
            "item_count": len(docs),
            "documents": len(docs),
            "effective_documents": max(1, len({profile.duplicate_signature for profile in local_profiles})),
            "impact_score": impact_score,
            "avg_score": avg_score,
            "maturity_score": maturity_score,
            "horizon_score": round(maturity_score / 100.0, 3),
            "momentum_score": momentum_score,
            "novelty_score": novelty_score,
            "uncertainty_score": uncertainty_score,
            "persistence_score": persistence_score,
            "risk_severity": risk_severity if report_type == "risk_mapping" else None,
            "maturity_stage": maturity_stage,
            "hype_stage": hype_stage,
            "direction": direction,
            "growth_ratio": round(growth_ratio, 2),
            "acceleration_ratio": round(acceleration_ratio, 2),
            "weak_signal_flag": weak_signal_flag,
            "signal_state": _cluster_signal_state(len(docs), novelty, growth_ratio),
            "taxonomy_matches": taxonomy_matches,
            "cluster_quality": {
                "score": quality_score,
                "coherence": round(coherence * 100, 1),
                "separation": round(separation * 100, 1),
                "taxonomy_focus": round(taxonomy_focus * 100, 1),
                "duplicate_pressure": round(duplicate_ratio * 100, 1),
            },
            "maturity_score_breakdown": maturity_breakdown,
            "impact_score_breakdown": impact_breakdown,
            "momentum_score_breakdown": momentum_breakdown,
            "novelty_score_breakdown": novelty_breakdown,
            "uncertainty_score_breakdown": uncertainty_breakdown,
            "risk_severity_breakdown": severity_breakdown if report_type == "risk_mapping" else None,
            "hull_polygon": _cluster_hull([(float(coordinates[index][0]), float(coordinates[index][1])) for index in indices]),
            "coords": {"x": cluster_x, "y": cluster_y},
            "articles": [str(getattr(doc, "id", getattr(doc, "hash", ""))) for doc in docs],
            "top_documents": representative_documents[:3],
            "representative_documents": representative_documents,
            "source_mix": [{"source": source, "count": count} for source, count in source_counts.most_common()],
            "insight_evidence": [
                {"type": "coverage", "detail": f"{len(docs)} documentos, {len(source_counts)} fuentes, {temporal['active_months']} meses activos"},
                {"type": "tempo", "detail": f"direccion {_direction_label(direction)}, crecimiento {round(growth_ratio * 100)}%, aceleracion {round(acceleration_ratio * 100)}%"},
                {"type": "taxonomy", "detail": f"dominante {taxonomy_matches[0]['name'] if taxonomy_matches else category}"},
                {"type": "quality", "detail": f"coherencia {round(coherence * 100)} / calidad {round(quality_score)}"},
            ],
            "executive_takeaway": _cluster_takeaway(label, report_type, category, weak_signal_flag, hype_stage, impact_score, maturity_score, momentum_score),
            "what_is_happening": summary,
            "why_it_matters": (
                f"Impacta {', '.join((taxonomy_matches[0].get('sector_tags') or taxonomy_matches[0].get('capability_tags') or ['capacidades transversales'])[:3])}"
                if taxonomy_matches
                else "impacta capacidades transversales"
            ),
            "decision_prompt": (
                "Escalar monitoreo y traducirlo a casos de uso, inversiones y dependencias."
                if report_type == "trend_mapping"
                else "Validar controles, escenarios y dependencias operativas asociadas."
            ),
            "dominant_risk": category if report_type == "risk_mapping" else None,
        }
        clusters.append(cluster_payload)
        super_cluster_index[category].append(cluster_id)

    for index in unclustered_indices:
        doc = documents[index]
        profile = profiles[index]
        x_value = round(float(coordinates[index][0]), 3)
        y_value = round(float(coordinates[index][1]), 3)
        payload = _base_document_payload(doc, profile, cluster_id="sin_cluster", x=x_value, y=y_value)
        payload.update(
            {
                "cluster_label": "Sin cluster",
                "keywords": list(getattr(doc, "matched_keywords", []) or [])[:5],
                "unclustered": True,
                "duplicate_flag": duplicate_counts[profile.duplicate_signature] > 1,
            }
        )
        document_points.append(payload)

    clusters.sort(key=lambda item: (item["impact_score"], item["momentum_score"], item["item_count"]), reverse=True)
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
                "avg_momentum": round(mean(cluster["momentum_score"] for cluster in related), 1),
            }
        )

    total_articles = sum(1 for doc in documents if _document_source_kind(doc) in {"news", "rss"})
    total_papers = sum(1 for doc in documents if _document_source_kind(doc) in {"paper", "pdf", "institutional_report", "patent"})
    top_documents = []
    for doc in _top_documents(documents, profiles, limit=10):
        profile = profile_by_id[str(getattr(doc, "id", getattr(doc, "hash", "")))]
        payload = _base_document_payload(doc, profile)
        payload["representative_reason"] = _representative_reason(profile, profile.primary_taxonomy)
        top_documents.append(payload)

    dominant_labels = [cluster["label"] for cluster in clusters[:5]]
    unclustered_count = len(unclustered_indices)
    clustered_count = len(documents) - unclustered_count
    unclustered_share = round((unclustered_count / max(len(documents), 1)) * 100, 1)
    taxonomy_coverage = round(sum(profile.primary_taxonomy_score for profile in profiles) / max(len(profiles), 1), 3)
    keyword_usefulness_ratio = round(min(1.0, len({term for term in keyword_pool if term not in _configured_generic_terms()}) / max(sum(keyword_pool.values()), 1)), 3)
    weak_signal_clusters = [cluster for cluster in clusters if cluster["weak_signal_flag"]][:4]
    quality_avg = round(float(np.mean(quality_scores)) if quality_scores else 0.0, 1)

    insights = [_top_level_insight(cluster, report_type) for cluster in clusters[:4]]
    if weak_signal_clusters:
        insights.append("Weak signals priorizados: " + ", ".join(cluster["label"] for cluster in weak_signal_clusters) + ".")
    if unclustered_share >= 25:
        insights.append(f"El {unclustered_share}% del corpus quedo sin cluster util; conviene revisar ruido editorial, dispersion de temas o sobrecarga de noticias tacticas.")

    executive_summary = (
        f"Se analizaron {len(documents)} documentos en {window_months} meses bajo {methodology_version}. "
        f"El snapshot concentra {len(clusters)} clusters utiles, {clustered_count} documentos agrupados y {unclustered_count} sin cluster. "
        f"Los temas/riesgos mas relevantes son {', '.join(dominant_labels[:3]) or 'dispersos'}, con calidad media {quality_avg}/100, "
        f"cobertura taxonomica {round(taxonomy_coverage * 100)}% y silhouette {silhouette}."
    )

    recommendations = []
    for cluster in clusters[:3]:
        if report_type == "risk_mapping":
            recommendations.append(f"Elevar seguimiento sobre {cluster['label']} y conectar su severidad con escenarios, terceros y planes de respuesta.")
        else:
            recommendations.append(f"Traducir {cluster['label']} a decisiones de capacidad, pilotos o apuestas de portafolio segun su momento {cluster['hype_stage']}.")
    if weak_signal_clusters:
        recommendations.append("Separar weak signals de clusters maduros para evitar que la novedad pierda visibilidad frente al volumen.")
    if unclustered_share >= 25:
        recommendations.append("Revisar documentos sin cluster para refinar filtros, taxonomia y deteccion de near-duplicates.")

    risk_signals = [
        {
            "type": cluster["label"],
            "description": cluster["executive_takeaway"],
            "severity": (
                "H"
                if (cluster.get("risk_severity") or cluster["impact_score"]) >= 75
                else "M"
                if (cluster.get("risk_severity") or cluster["impact_score"]) >= 55
                else "L"
            ),
            "related_clusters": [cluster["cluster_id"]],
        }
        for cluster in clusters[:6]
    ]

    summary = {
        "total_documents": len(documents),
        "total_clusters": len(clusters),
        "clustered_documents": clustered_count,
        "unclustered_documents": unclustered_count,
        "dominant_topics": dominant_labels if report_type == "trend_mapping" else [],
        "dominant_risks": dominant_labels if report_type == "risk_mapping" else [],
        "emerging_topics": [cluster["label"] for cluster in clusters if cluster["hype_stage"] in {"weak_signal", "innovation_trigger", "rising_attention"}][:4],
        "consolidating_topics": [cluster["label"] for cluster in clusters if cluster["hype_stage"] in {"consolidation", "productive_adoption"}][:4],
        "weak_signal_topics": [cluster["label"] for cluster in weak_signal_clusters],
        "source_diversity": len(source_mix),
        "avg_relevance": round(mean((getattr(doc, "relevance_score", 0) or 0) for doc in documents), 1),
        "silhouette_score": silhouette,
        "cluster_quality_avg": quality_avg,
        "taxonomy_coverage": round(taxonomy_coverage * 100, 1),
        "methodology_version": methodology_version,
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
        "methodology_version": methodology_version,
    }

    cluster_cards = [
        {
            "cluster_id": cluster["cluster_id"],
            "label": cluster["label"],
            "subtitle": cluster["subtitle"],
            "category": cluster["category"],
            "summary": cluster["summary"],
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
        for cluster in clusters
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
        for cluster in clusters[:8]
    ]

    taxonomy_breakdown = [{"name": name, "score": round(score, 3)} for name, score in aggregated_taxonomy.most_common(12)]
    quality_checks = {
        "methodology_version": methodology_version,
        "cluster_coherence_avg": round(float(np.mean([cluster["cluster_quality"]["coherence"] for cluster in clusters])) if clusters else 0.0, 1),
        "cluster_quality_avg": quality_avg,
        "unclustered_ratio": unclustered_share,
        "taxonomy_coverage": round(taxonomy_coverage * 100, 1),
        "keyword_usefulness_ratio": round(keyword_usefulness_ratio * 100, 1),
        "weak_signal_clusters": len(weak_signal_clusters),
        "low_quality_clusters": len([cluster for cluster in clusters if cluster["cluster_quality"]["score"] < 55]),
    }

    filters_metadata = {
        "categories": sorted({cluster["category"] for cluster in clusters}),
        "source_types": sorted({_document_source_kind(doc) for doc in documents}),
        "sources": [source for source, _ in source_mix.most_common(20)],
        "maturity_stages": list(_GARTNER_STAGES),
        "hype_stages": list(_HYPE_STAGE_ORDER),
        "recommended_sort_orders": ["impact", "momentum", "novelty", "size", "quality"],
        "date_range": {
            "start": min((_document_date(doc) for doc in documents if _document_date(doc) is not None), default=None),
            "end": max((_document_date(doc) for doc in documents if _document_date(doc) is not None), default=None),
        },
    }
    for key in ("start", "end"):
        value = filters_metadata["date_range"][key]
        filters_metadata["date_range"][key] = value.isoformat() if isinstance(value, datetime) else None

    return {
        "generated_at": generated_at,
        "summary": summary,
        "meta": meta,
        "documents": document_points,
        "clusters": clusters,
        "super_clusters": super_clusters,
        "timeline": timeline,
        "monthly_volume": [{"bucket": bucket, "count": count} for bucket, count in sorted(monthly_volume.items())],
        "source_mix": [{"source": source, "count": count} for source, count in source_mix.most_common()],
        "top_documents": top_documents,
        "cluster_cards": cluster_cards,
        "trend_cards": trend_cards,
        "taxonomy_breakdown": taxonomy_breakdown,
        "weak_signals": [card for card in cluster_cards if card["weak_signal_flag"]][:6],
        "quality_checks": quality_checks,
        "filters_metadata": filters_metadata,
        "insights": insights,
        "executive_summary": executive_summary,
        "recommendations": recommendations,
        "risk_signals": risk_signals,
        "methodology": {
            "methodology_version": methodology_version,
            "representation": {
                "document_text": "titulo + excerpt + texto normalizado + keywords + categoria/risk_type + metadata de fuente",
                "feature_space": representation_mode,
                "embedding_usage": embedding_meta["feature_space"],
                "auxiliary_features": auxiliary_feature_names,
            },
            "clustering": {"cluster_method": cluster_method, "projection_method": projection_method, "noise_label": "sin_cluster"},
            "scoring": {
                "impact": "heuristica interpretable multi-factor",
                "maturity": "recurrencia + adopcion/persistencia + coherencia + autoridad",
                "momentum": "crecimiento + aceleracion + recencia + visibilidad",
                "novelty": "recencia + baja recurrencia + exploracion",
                "uncertainty": "exploracion + baja coherencia + baja autoridad + duplicidad",
            },
        },
        "parameters": {
            "window_months": window_months,
            "cluster_method": cluster_method,
            "vectorizer": "tfidf_ngram_v1",
            "projection_method": projection_method,
            "feature_space": embedding_meta["feature_space"],
            "representation_mode": representation_mode,
            "embedding_provider": embedding_meta["embedding_provider"],
            "embedding_model_id": embedding_meta["embedding_model_id"],
            "embedding_attempted": embedding_meta["embedding_attempted"],
            "embedding_error": embedding_meta["embedding_error"],
            "noise_label": "sin_cluster",
            "clustered_documents": clustered_count,
            "unclustered_documents": unclustered_count,
            "cluster_input_dim": int(clustering_features.shape[1]) if clustering_features.ndim == 2 else 0,
            "auxiliary_feature_count": len(auxiliary_feature_names),
            "taxonomy_version": _taxonomy_config().get("version"),
            "methodology_version": methodology_version,
            **(
                {
                    "hdbscan_min_cluster_size": _select_hdbscan_params(len(documents))[0],
                    "hdbscan_min_samples": _select_hdbscan_params(len(documents))[1],
                }
                if cluster_method == "hdbscan"
                else {}
            ),
            **({"embedding_vector_dim": embedding_meta["embedding_vector_dim"]} if embedding_meta.get("embedding_vector_dim") else {}),
        },
    }
