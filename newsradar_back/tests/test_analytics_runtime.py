from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from newsradar_api.shared_kernel.ingestion import runtime
from newsradar_api.shared_kernel.snapshots.report_builder import (
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

    assert trend_payload["version"] == 2
    assert trend_payload["parameters"]["vectorizer"] == "tfidf_ngram_v1"
    assert trend_payload["charts"]["embedding_scatter"]
    assert trend_payload["clusters"]
    assert "executive_summary" in trend_payload["summary"]

    assert risk_payload["version"] == 2
    assert risk_payload["parameters"]["cluster_method"] in {"kmeans", "hdbscan", "single_cluster"}
    assert risk_payload["charts"]["hype_cycle"]
    assert risk_payload["summary"]["dominant_risks"]


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
