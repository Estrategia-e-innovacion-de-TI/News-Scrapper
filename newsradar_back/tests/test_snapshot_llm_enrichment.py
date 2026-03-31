from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from newsradar_api.shared_kernel.bedrock.snapshot_enricher import SnapshotLLMEnricher
from newsradar_api.shared_kernel.snapshots.report_builder import build_trendmap_payload


def _doc(identifier: str, title: str, category: str, score: int = 80):
    now = datetime(2026, 3, 31, tzinfo=timezone.utc)
    return SimpleNamespace(
        id=identifier,
        title=title,
        source_id="demo",
        source_type="rss",
        category=category,
        risk_type=None,
        relevance_score=score,
        published_at=now,
        fetched_at=now,
        url=f"https://example.com/{identifier}",
        excerpt=f"Resumen {title}",
        matched_keywords=["ia", "modelo"],
        materialized_events=[],
        text=f"{title} {category} modelo agente bancario",
    )


def test_snapshot_payload_defaults_to_non_llm_when_no_runtime_hints(monkeypatch) -> None:
    monkeypatch.setenv("NEWSRADAR_SNAPSHOT_LLM_MODE", "auto")
    for key in [
        "AWS_ACCESS_KEY_ID",
        "AWS_PROFILE",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        "AWS_SESSION_TOKEN",
    ]:
        monkeypatch.delenv(key, raising=False)

    payload = build_trendmap_payload(
        [
            _doc("1", "IA generativa para banca", "IA", 90),
            _doc("2", "Automatizacion de scoring", "IA", 78),
        ],
        window_months=6,
    )

    assert payload["parameters"]["llm_enrichment"]["used"] is False
    assert "reason" in payload["parameters"]["llm_enrichment"]


def test_snapshot_llm_enricher_overrides_cluster_and_summary(monkeypatch) -> None:
    monkeypatch.setenv("NEWSRADAR_SNAPSHOT_LLM_MODE", "enabled")

    class FakeBedrockAdapter:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def invoke_claude(self, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
            if "Cluster data:" in prompt:
                return (
                    '{"label":"IA aplicada a banca","summary":"Cluster de automatizacion bancaria.",'
                    '"category":"Fintech / Banca Digital","keywords":["ia","banca","automatizacion"],"relevance":"alta",'
                    '"executive_takeaway":"La IA aplicada a banca gana traccion."}'
                )
            return (
                '{"executive_summary":"La IA domina el snapshot.","insights":["IA crece"],'
                '"recommendations":["Acelerar monitoreo"],'
                '"risk_signals":[{"type":"ia","description":"Aumento de actividad","severity":"M",'
                '"related_clusters":["trend_mapping_cluster_1"]}]}'
            )

    monkeypatch.setattr(
        "newsradar_api.shared_kernel.bedrock.snapshot_enricher.BedrockAdapter",
        FakeBedrockAdapter,
    )

    payload = {
        "report_type": "trend_mapping",
        "generated_at": "2026-03-31T00:00:00+00:00",
        "summary": {"total_documents": 4, "total_clusters": 1},
        "clusters": [
            {
                "cluster_id": "trend_mapping_cluster_1",
                "label": "IA",
                "category": "Otros temas",
                "summary": "old",
                "keywords": ["old"],
                "top_keywords": ["old"],
                "relevance": "media",
                "item_count": 4,
                "impact_score": 72,
                "horizon_score": 0.51,
                "maturity_stage": "trigger",
                "coords": {"x": 0.1, "y": 0.2},
                "top_documents": [{"title": "Doc 1"}],
            }
        ],
        "super_clusters": [{"category": "Otros temas", "clusters": ["trend_mapping_cluster_1"], "hull_polygon": [], "total_items": 4, "avg_impact": 72}],
        "top_documents": [{"title": "Doc 1"}],
        "sources_used": ["demo"],
        "parameters": {},
        "articles": [{"cluster_id": "trend_mapping_cluster_1", "title": "Doc 1", "category": "Otros temas"}],
        "trends": [{"cluster_id": "trend_mapping_cluster_1", "topic": "IA", "count": 4, "avg_score": 72}],
        "charts": {
            "cluster_sizes": [{"label": "IA", "count": 4}],
            "hype_cycle": [{"label": "IA", "x": 51.0, "y": 72}],
        },
    }

    enriched = SnapshotLLMEnricher("trend_mapping").enrich_payload(payload)

    assert enriched["clusters"][0]["label"] == "IA aplicada a banca"
    assert enriched["clusters"][0]["category"] == "Fintech / Banca Digital"
    assert enriched["super_clusters"][0]["category"] == "Fintech / Banca Digital"
    assert enriched["summary"]["dominant_topics"] == ["IA aplicada a banca"]
    assert enriched["articles"][0]["category"] == "Fintech / Banca Digital"
    assert enriched["trends"][0]["topic"] == "IA aplicada a banca"
    assert enriched["charts"]["cluster_sizes"][0]["label"] == "IA aplicada a banca"
    assert enriched["parameters"]["cluster_semantics_source"] == "llm"
    assert enriched["summary"]["executive_summary"] == "La IA domina el snapshot."
    assert enriched["insights"] == ["IA crece"]
    assert enriched["parameters"]["llm_enrichment"]["used"] is True


def test_snapshot_llm_enricher_accepts_markdown_wrapped_json(monkeypatch) -> None:
    monkeypatch.setenv("NEWSRADAR_SNAPSHOT_LLM_MODE", "enabled")

    class FakeBedrockAdapter:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def invoke_claude(self, prompt: str, system: str = "", max_tokens: int = 1024) -> str:
            if "Cluster data:" in prompt:
                return """Aqui tienes el JSON:
```json
{
  "label": "IA aplicada a banca",
  "category": "Fintech / Banca Digital",
  "summary": "Cluster de automatizacion bancaria.",
  "keywords": ["ia", "banca", "automatizacion",],
  "relevance": "alta",
  "executive_takeaway": "La IA aplicada a banca gana traccion.",
}
```"""
            return """```json
{
  "executive_summary": "La IA domina el snapshot.",
  "insights": ["IA crece",],
  "recommendations": ["Acelerar monitoreo",],
  "risk_signals": [
    {
      "type": "ia",
      "description": "Aumento de actividad",
      "severity": "M",
      "related_clusters": ["trend_mapping_cluster_1",]
    }
  ]
}
```"""

    monkeypatch.setattr(
        "newsradar_api.shared_kernel.bedrock.snapshot_enricher.BedrockAdapter",
        FakeBedrockAdapter,
    )

    payload = {
        "report_type": "trend_mapping",
        "generated_at": "2026-03-31T00:00:00+00:00",
        "summary": {"total_documents": 4, "total_clusters": 1},
        "clusters": [
            {
                "cluster_id": "trend_mapping_cluster_1",
                "label": "IA",
                "category": "Otros temas",
                "summary": "old",
                "keywords": ["old"],
                "top_keywords": ["old"],
                "relevance": "media",
                "top_documents": [{"title": "Doc 1"}],
            }
        ],
        "top_documents": [{"title": "Doc 1"}],
        "sources_used": ["demo"],
        "parameters": {},
        "documents": [{"cluster_id": "trend_mapping_cluster_1", "title": "Doc 1"}],
    }

    enriched = SnapshotLLMEnricher("trend_mapping").enrich_payload(payload)

    assert enriched["clusters"][0]["label"] == "IA aplicada a banca"
    assert enriched["clusters"][0]["category"] == "Fintech / Banca Digital"
    assert enriched["clusters"][0]["keywords"] == ["ia", "banca", "automatizacion"]
    assert enriched["summary"]["executive_summary"] == "La IA domina el snapshot."
    assert enriched["recommendations"] == ["Acelerar monitoreo"]
    assert enriched["parameters"]["llm_enrichment"]["used"] is True
