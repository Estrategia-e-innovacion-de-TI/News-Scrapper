from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import sys
from types import SimpleNamespace
import types

import numpy as np

from newsradar_api.domain.model.pipeline_models import (
    FetchMethod,
    GraphState,
    QueueItem,
    SourceConfig,
    SourceMetrics,
)
from newsradar_api.infrastructure.connectors.search_models import SearchCandidate
from newsradar_api.shared_kernel.analytics import advanced_engine
from newsradar_api.shared_kernel.ingestion import runtime
from newsradar_api.shared_kernel.snapshots.report_builder import (
    _attach_comparative_signals,
    _legacy_cluster_id,
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
    query_terms: list[str] | None = None,
    origin: str | None = None,
    text: str | None = None,
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
        text=text or f"{title} {category or risk_type or ''} {' '.join(keywords or [])}",
        query_terms=query_terms or [],
        origin=origin,
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
    assert trend_payload["parameters"]["analysis_engine"] == "legacy_trend_pipeline_adapter"
    assert trend_payload["parameters"]["vectorizer"] == "legacy_tfidf_fallback_or_bedrock"
    assert trend_payload["charts"]["embedding_scatter"]
    assert trend_payload["clusters"]
    assert "executive_summary" in trend_payload["summary"]
    assert trend_payload["quality_checks"]["methodology_version"] == "legacy_trend_pipeline_adapter_v1"
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


def test_search_seed_terms_do_not_pollute_semantic_representation() -> None:
    search_doc = _doc(
        "tw-search",
        "Bank pilots document automation",
        source_id="arxiv",
        source_type="paper",
        score=78,
        days_ago=4,
        keywords=["machine learning", "document intelligence"],
        query_terms=["machine learning"],
        origin="search_ingest",
        text="Banks are piloting document automation workflows with OCR and policy extraction.",
    )
    regular_doc = _doc(
        "tw-regular",
        "Bank pilots document automation",
        source_id="rss-tech",
        source_type="rss",
        score=78,
        days_ago=4,
        keywords=["machine learning", "document intelligence"],
        text="Banks are piloting document automation workflows with OCR and policy extraction.",
    )

    search_text = advanced_engine._document_text(search_doc, "trend_mapping")
    regular_text = advanced_engine._document_text(regular_doc, "trend_mapping")
    search_profile = advanced_engine._document_profile(search_doc, "trend_mapping", 6)
    regular_profile = advanced_engine._document_profile(regular_doc, "trend_mapping", 6)

    assert "machine learning" not in search_text.lower()
    assert "machine learning" in regular_text.lower()
    assert "machine learning" not in " ".join(search_profile.taxonomy_matches[0].get("matched_terms") or []).lower()
    assert "machine learning" in regular_profile.normalized_keywords


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


def test_legacy_cluster_id_compacts_long_identifiers_stably() -> None:
    original = "trend-inteligencia-artificial-inteligencia-artif-eba66c2c67"

    compact = _legacy_cluster_id(original)

    assert len(compact) <= 50
    assert compact == _legacy_cluster_id(original)
    assert compact != original


def test_batch_discovery_adds_google_news_and_arxiv_for_tech_watch(monkeypatch) -> None:
    fake_langgraph = types.ModuleType("langgraph")
    fake_langgraph_graph = types.ModuleType("langgraph.graph")
    fake_langgraph_graph.END = object()

    class _FakeStateGraph:
        def __init__(self, *args, **kwargs) -> None:
            return None

    fake_langgraph_graph.StateGraph = _FakeStateGraph
    fake_bs4 = types.ModuleType("bs4")

    class _FakeBeautifulSoup:
        def __init__(self, *args, **kwargs) -> None:
            return None

    fake_bs4.BeautifulSoup = _FakeBeautifulSoup
    monkeypatch.setitem(sys.modules, "langgraph", fake_langgraph)
    monkeypatch.setitem(sys.modules, "langgraph.graph", fake_langgraph_graph)
    monkeypatch.setitem(sys.modules, "bs4", fake_bs4)

    nodes = importlib.import_module("newsradar_api.infrastructure.pipeline.nodes")

    async def _fake_google_news_search(company=None, terms=None, date_from=None, date_to=None, max_items=30):
        return [
            QueueItem(
                source_id="google_news",
                url=f"https://example.com/news/{'-'.join(terms or ['none'])}",
                source_url="google_news_rss",
                fetch_method=FetchMethod.HTTP,
                title="Resultado Google News",
            )
        ]

    async def _fake_search_arxiv(term: str, max_results: int = 20, since_days: int = 30, timeout: int = 30):
        return [
            SearchCandidate(
                mode="papers",
                term=term,
                title=f"Paper {term}",
                url=f"https://arxiv.org/abs/{term.replace(' ', '-')}",
                snippet=f"Abstract sobre {term}",
                source_provider="arxiv",
            )
        ]

    monkeypatch.setattr("newsradar_api.infrastructure.connectors.google_news_connector.search", _fake_google_news_search)
    monkeypatch.setattr("newsradar_api.infrastructure.connectors.providers.arxiv_provider.search_arxiv", _fake_search_arxiv)

    state = GraphState(
        focus="vigilancia_news",
        adhoc=False,
        selected_sources=[],
        source_metrics={},
    )

    result = asyncio.run(nodes.discover_items_node(state))

    assert any(item.source_id == "google_news" for item in result["queue"])
    assert any(item.source_id == "arxiv" for item in result["queue"])
    assert any(source.source_id == "google_news" for source in result["selected_sources"])
    assert any(source.source_id == "arxiv" for source in result["selected_sources"])
    assert all(item.query_terms for item in result["queue"] if item.source_id in {"google_news", "arxiv"})


def test_top_documents_reduce_duplicates_and_repeat_sources() -> None:
    docs = [
        _doc("tw-r1", "AI agents for banking", source_id="rss-a", source_type="rss", category="IA", score=94, keywords=["ai", "agents", "banking"]),
        _doc("tw-r2", "AI agents for banking", source_id="rss-a", source_type="rss", category="IA", score=92, keywords=["ai", "agents", "banking"]),
        _doc("tw-r3", "Foundation models for insurance", source_id="rss-b", source_type="rss", category="IA", score=88, keywords=["foundation models", "insurance"]),
        _doc("tw-r4", "Tokenization pilots in banking", source_id="rss-c", source_type="rss", category="Blockchain", score=84, keywords=["tokenization", "banking"]),
    ]

    profiles = [advanced_engine._document_profile(doc, "trend_mapping", 6) for doc in docs]
    selected = advanced_engine._top_documents(docs, profiles, limit=3)
    selected_ids = {doc.id for doc in selected}

    assert len(selected) == 3
    assert len({doc.source_id for doc in selected}) >= 2
    assert not {"tw-r1", "tw-r2"} <= selected_ids
