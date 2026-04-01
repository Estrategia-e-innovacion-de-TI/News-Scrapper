from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np

from newsradar_api.shared_kernel.analytics import advanced_engine
from newsradar_api.shared_kernel.ingestion import runtime
from newsradar_api.shared_kernel.snapshots.report_builder import (
    _attach_comparative_signals,
    build_riskmap_payload,
    build_trendmap_payload,
)


def _doc(
    identifier: str,
    title: str,
    *,
    source_id: str,
    source_type: str,
    category: str | None = None,
    risk_type: str | None = None,
    score: int = 70,
    days_ago: int = 0,
    keywords: list[str] | None = None,
) -> SimpleNamespace:
    published_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return SimpleNamespace(
        id=identifier,
        title=title,
        source_id=source_id,
        source_type=source_type,
        category=category,
        risk_type=risk_type,
        relevance_score=score,
        published_at=published_at,
        fetched_at=published_at,
        url=f"https://example.com/{identifier}",
        excerpt=f"Resumen de {title}",
        matched_keywords=keywords or [],
        materialized_events=[],
        text=f"{title} {category or risk_type or ''} {' '.join(keywords or [])}",
    )


def test_snapshot_builders_emit_advanced_analytics_payloads() -> None:
    tech_docs = [
        _doc("tw-1", "IA generativa para banca", source_id="rss-tech", source_type="rss", category="IA", score=91, days_ago=5, keywords=["ia", "agentes", "banca"]),
        _doc("tw-2", "Modelos fundacionales en seguros", source_id="rss-tech", source_type="rss", category="IA", score=85, days_ago=12, keywords=["modelos", "seguros"]),
        _doc("tw-3", "Tokenizacion de activos bancarios", source_id="paper-tech", source_type="paper", category="Blockchain", score=78, days_ago=20, keywords=["tokenizacion", "activos"]),
        _doc("tw-4", "Patentes de vision computacional", source_id="patent-tech", source_type="patent", category="Vision", score=73, days_ago=28, keywords=["vision", "patentes"]),
    ]
    risk_docs = [
        _doc("rk-1", "Alerta de ransomware en banca", source_id="wef", source_type="pdf", risk_type="ciberseguridad", score=95, days_ago=3, keywords=["ransomware", "ciber"]),
        _doc("rk-2", "Fraude digital y suplantacion", source_id="allianz", source_type="institutional_report", risk_type="desinformacion", score=82, days_ago=15, keywords=["fraude", "suplantacion"]),
        _doc("rk-3", "Riesgo climatico en infraestructura", source_id="world-bank", source_type="pdf", risk_type="clima y naturaleza", score=80, days_ago=25, keywords=["clima", "infraestructura"]),
    ]

    trend_payload = build_trendmap_payload(tech_docs, window_months=6)
    risk_payload = build_riskmap_payload(risk_docs, window_months=6)

    assert trend_payload["version"] == 3
    assert trend_payload["parameters"]["vectorizer"] == "tfidf_ngram_v1"
    assert trend_payload["charts"]["embedding_scatter"]
    assert trend_payload["clusters"]
    assert "executive_summary" in trend_payload["summary"]
    assert trend_payload["quality_checks"]["methodology_version"] == "analytics_methodology_v4"
    assert trend_payload["quality_checks"]["cluster_coverage"] >= 0
    assert "cluster_cards" in trend_payload

    assert risk_payload["version"] == 3
    assert risk_payload["parameters"]["cluster_method"] in {"kmeans", "hdbscan", "single_cluster"}
    assert risk_payload["charts"]["hype_cycle"]
    assert risk_payload["summary"]["dominant_risks"]
    assert "filters_metadata" in risk_payload
    assert "severity_bands" in risk_payload["filters_metadata"]


def test_smcp_ingestion_falls_back_to_local_runtime(monkeypatch) -> None:
    async def _fail_smcp(run_id: str, focus: str, **params):
        raise RuntimeError("smcp offline")

    async def _local(run_id: str, focus: str, **params):
        return {"status": "completed", "run_id": run_id, "execution_id": "exec-local"}

    monkeypatch.setenv("NEWSRADAR_USE_SMCP", "1")
    monkeypatch.setattr(runtime, "run_smcp_ingestion", _fail_smcp)
    monkeypatch.setattr(runtime, "run_local_ingestion", _local)

    result = asyncio.run(runtime.run_ingestion_with_fallback("run-123", "vigilancia_news", days=7))

    assert result["run_id"] == "run-123"
    assert result["execution_id"] == "exec-local"


def test_noise_documents_remain_unclustered(monkeypatch) -> None:
    docs = [
        _doc("tw-a", "IA generativa en banca", source_id="rss-tech", source_type="rss", category="IA", score=91, days_ago=5, keywords=["ia", "banca"]),
        _doc("tw-b", "Modelos agentes en seguros", source_id="rss-tech", source_type="rss", category="IA", score=85, days_ago=7, keywords=["agentes", "seguros"]),
        _doc("tw-c", "Nueva regulación fintech", source_id="rss-reg", source_type="rss", category="Regulacion", score=69, days_ago=3, keywords=["regulacion", "fintech"]),
        _doc("tw-d", "Demanda energética de data centers", source_id="rss-energy", source_type="rss", category="Infraestructura", score=66, days_ago=9, keywords=["energia", "data center"]),
    ]

    monkeypatch.setattr(
        advanced_engine,
        "_cluster_features",
        lambda features: (np.asarray([0, 0, -1, -1], dtype=int), "hdbscan"),
    )
    monkeypatch.setattr(
        advanced_engine,
        "_project_coordinates",
        lambda features: (
            np.asarray(
                [
                    [0.0, 0.0],
                    [0.1, 0.2],
                    [1.0, 1.0],
                    [1.1, 1.2],
                ],
                dtype=float,
            ),
            "mock",
        ),
    )

    analysis = advanced_engine.generate_report_analysis(docs, "trend_mapping", 6)

    assert analysis["summary"]["total_clusters"] == 1
    assert analysis["summary"]["clustered_documents"] == 2
    assert analysis["summary"]["unclustered_documents"] == 2
    assert any(doc["cluster_id"] == "sin_cluster" for doc in analysis["documents"])
    assert analysis["parameters"]["noise_label"] == "sin_cluster"


def test_embeddings_are_preferred_for_clustering(monkeypatch) -> None:
    docs = [
        _doc("tw-1", "IA generativa en banca", source_id="rss-tech", source_type="rss", category="IA", score=91, days_ago=5, keywords=["ia", "banca"]),
        _doc("tw-2", "Modelos agentes en seguros", source_id="rss-tech", source_type="rss", category="IA", score=85, days_ago=7, keywords=["agentes", "seguros"]),
        _doc("tw-3", "Tokenizacion de activos", source_id="rss-fin", source_type="rss", category="Blockchain", score=80, days_ago=6, keywords=["tokenizacion", "activos"]),
        _doc("tw-4", "Infraestructura para modelos", source_id="rss-cloud", source_type="rss", category="Cloud", score=77, days_ago=10, keywords=["infraestructura", "modelo"]),
    ]

    monkeypatch.setenv("NEWSRADAR_ANALYTICS_EMBEDDINGS_MODE", "enabled")

    class FakeBedrockAdapter:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def get_embeddings(self, texts: list[str]) -> list[list[float]]:
            return [
                [1.0, 0.0, 0.1],
                [0.9, 0.1, 0.1],
                [0.0, 1.0, 0.1],
                [0.1, 0.9, 0.0],
            ]

    monkeypatch.setattr(advanced_engine, "BedrockAdapter", FakeBedrockAdapter)
    monkeypatch.setattr(
        advanced_engine,
        "_cluster_features",
        lambda features: (np.asarray([0, 0, 1, -1], dtype=int), "hdbscan"),
    )
    monkeypatch.setattr(
        advanced_engine,
        "_project_coordinates",
        lambda features: (
            np.asarray(
                [
                    [0.0, 0.0],
                    [0.1, 0.2],
                    [1.0, 1.0],
                    [1.2, 1.1],
                ],
                dtype=float,
            ),
            "mock",
        ),
    )

    analysis = advanced_engine.generate_report_analysis(docs, "trend_mapping", 6)

    assert analysis["parameters"]["feature_space"] == "bedrock_embeddings"
    assert analysis["parameters"]["embedding_provider"] == "bedrock"
    assert analysis["parameters"]["embedding_attempted"] is True
    assert analysis["parameters"]["cluster_method"] == "hdbscan"
    assert analysis["summary"]["clustered_documents"] == 2
    assert analysis["summary"]["unclustered_documents"] == 2


def test_cluster_labels_filter_noise_and_infer_category(monkeypatch) -> None:
    docs = [
        _doc("tw-l1", "AI agents transform banking operations", source_id="rss-tech", source_type="rss", score=88, days_ago=4),
        _doc("tw-l2", "Foundation models for banking automation", source_id="rss-tech", source_type="rss", score=84, days_ago=7),
        _doc("tw-l3", "Generative AI copilots for risk teams", source_id="rss-fin", source_type="rss", score=82, days_ago=9),
    ]

    monkeypatch.setattr(
        advanced_engine,
        "_build_embedding_features",
        lambda documents, report_type: (None, {
            "feature_space": "tfidf_lexical",
            "embedding_provider": None,
            "embedding_model_id": None,
            "embedding_attempted": False,
            "embedding_error": None,
        }),
    )
    monkeypatch.setattr(
        advanced_engine,
        "_cluster_features",
        lambda features: (np.asarray([0, 0, 0], dtype=int), "single_cluster"),
    )
    monkeypatch.setattr(
        advanced_engine,
        "_project_coordinates",
        lambda features: (
            np.asarray(
                [
                    [0.0, 0.0],
                    [0.2, 0.1],
                    [0.1, 0.2],
                ],
                dtype=float,
            ),
            "mock",
        ),
    )

    analysis = advanced_engine.generate_report_analysis(docs, "trend_mapping", 6)
    cluster = analysis["clusters"][0]

    assert cluster["category"] == "Inteligencia Artificial"
    assert cluster["label"] != "Mas / And"
    assert cluster["label"] != "Más / And"
    assert "and" not in [keyword.lower() for keyword in cluster["keywords"]]
    assert "mas" not in [keyword.lower() for keyword in cluster["keywords"]]


def test_hdbscan_all_noise_falls_back_to_kmeans(monkeypatch) -> None:
    features = np.asarray(
        [
            [0.0, 0.0],
            [0.1, 0.1],
            [1.0, 1.0],
            [1.1, 1.1],
        ],
        dtype=float,
    )

    class FakeHdbscanModule:
        class HDBSCAN:
            def __init__(self, *args, **kwargs) -> None:
                return None

            def fit_predict(self, values):
                return np.asarray([-1, -1, -1, -1], dtype=int)

    class FakeKMeans:
        def __init__(self, n_clusters: int, random_state: int, n_init: int) -> None:
            return None

        def fit_predict(self, values):
            return np.asarray([0, 0, 1, 1], dtype=int)

    monkeypatch.setattr(advanced_engine, "hdbscan", FakeHdbscanModule)
    monkeypatch.setattr(advanced_engine, "KMeans", FakeKMeans)

    labels, method = advanced_engine._cluster_features(features)

    assert method == "kmeans"
    assert labels.tolist() == [0, 0, 1, 1]


def test_comparative_signals_reuse_lineage_and_update_quality_checks() -> None:
    payload = {
        "report_type": "trend_mapping",
        "clusters": [
            {
                "cluster_id": "trend-ai-new",
                "label": "Agentes de IA para servicio",
                "category": "Inteligencia Artificial",
                "keywords": ["agentes de ia", "copilots", "service automation"],
                "top_keywords": ["agentes de ia", "copilots", "service automation"],
                "taxonomy_matches": [{"name": "Inteligencia Artificial", "score": 0.9}],
                "item_count": 6,
                "impact_score": 78.0,
                "momentum_score": 71.0,
                "lineage_id": "trend-ai-new",
                "history_depth": 1,
            }
        ],
        "documents": [
            {"id": "doc-1", "cluster_id": "trend-ai-new"},
        ],
        "timeline": [
            {"cluster_id": "trend-ai-new", "topic": "Agentes de IA para servicio"},
        ],
        "cluster_cards": [
            {"cluster_id": "trend-ai-new", "label": "Agentes de IA para servicio"},
        ],
        "weak_signals": [],
        "risk_signals": [],
        "quality_checks": {},
        "filters_metadata": {},
    }
    previous = {
        "clusters": [
            {
                "cluster_id": "trend-ai-stable",
                "lineage_id": "trend-ai-stable",
                "history_depth": 3,
                "label": "Agentes de IA para servicio",
                "category": "Inteligencia Artificial",
                "keywords": ["agentes de ia", "copilots", "service automation"],
                "top_keywords": ["agentes de ia", "copilots", "service automation"],
                "taxonomy_matches": [{"name": "Inteligencia Artificial", "score": 0.9}],
                "item_count": 4,
                "impact_score": 72.0,
                "momentum_score": 58.0,
            }
        ]
    }

    _attach_comparative_signals(payload, previous)

    cluster = payload["clusters"][0]
    assert cluster["cluster_id"] == "trend-ai-stable"
    assert cluster["history_depth"] == 4
    assert cluster["comparative_signal"]["status"] == "accelerating"
    assert payload["quality_checks"]["lineage_reused_clusters"] == 1
    assert payload["quality_checks"]["stability_score_avg"] > 0
