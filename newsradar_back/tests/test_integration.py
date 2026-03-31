from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from newsradar_api.infrastructure.connectors.search_models import SearchCandidate, SearchReport
from newsradar_api.infrastructure.driven_adapters.database import get_session
from newsradar_api.infrastructure.driven_adapters.db_models import (
    Document as DBDocument,
    PipelineRun,
    Subscription,
    TrendmapSnapshot,
)
from newsradar_api.infrastructure.driven_adapters.db_adapter import DBAdapter
from newsradar_api.infrastructure.entry_points import aras_routes, export_routes, trendmap_routes, vigilancia_routes
from newsradar_api.main import app
import newsradar_api.main as main_module


class FakeScalarResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = list(items)

    def all(self) -> list[Any]:
        return list(self._items)


class FakeResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = list(items)

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._items)

    def scalar_one_or_none(self) -> Any:
        return self._items[0] if self._items else None


class FakeSession:
    def __init__(self, entity_map: dict[type[Any], list[Any]] | None = None) -> None:
        self.entity_map = entity_map or {}
        self.added: list[Any] = []

    async def execute(self, statement: Any) -> FakeResult:
        entity = statement.column_descriptions[0].get("entity")
        return FakeResult(self.entity_map.get(entity, []))

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        self.entity_map.setdefault(type(obj), []).append(obj)

    async def commit(self) -> None:
        return None

    async def refresh(self, obj: Any) -> None:
        return None


def build_client(monkeypatch: pytest.MonkeyPatch, session: FakeSession) -> TestClient:
    async def _noop_init_db() -> None:
        return None

    async def _override_get_session():
        yield session

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    app.dependency_overrides[get_session] = _override_get_session
    return TestClient(app)


def test_routers_registered_and_existing_routes_respond(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = SimpleNamespace(
        id="snapshot-1",
        generated_at=datetime(2026, 3, 31, tzinfo=timezone.utc),
    )
    session = FakeSession(
        entity_map={
            Subscription: [],
            TrendmapSnapshot: [snapshot],
        },
    )

    async def _fake_get_clusters(self: DBAdapter) -> list[Any]:
        return []

    async def _fake_get_trends(self: DBAdapter) -> list[Any]:
        return []

    monkeypatch.setattr(DBAdapter, "get_clusters", _fake_get_clusters)
    monkeypatch.setattr(DBAdapter, "get_trends", _fake_get_trends)
    vigilancia_routes._subscription_manager = None
    vigilancia_routes._cluster_engine = None

    with build_client(monkeypatch, session) as client:
        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        paths = openapi.json()["paths"]
        assert "/api/pipeline/run" in paths
        assert "/api/subscriptions/" in paths
        assert "/api/catalog/sources" in paths

        middleware_names = [mw.cls.__name__ for mw in app.user_middleware]
        assert "CORSMiddleware" in middleware_names

        catalog = client.get("/api/catalog/sources")
        assert catalog.status_code == 200
        assert "sources" in catalog.json()

        subscriptions = client.get("/api/subscriptions/")
        assert subscriptions.status_code == 200
        assert subscriptions.json() == []

        vigilancia_topics = client.get("/api/vigilancia/topics")
        assert vigilancia_topics.status_code == 200
        assert any(topic["group_id"] == "ia_ml" for topic in vigilancia_topics.json())

        trendmap_meta = client.get("/api/trendmap/meta")
        assert trendmap_meta.status_code == 200
        assert trendmap_meta.json()["total_clusters"] == 0

    app.dependency_overrides.clear()


def test_aras_search_classification_severity_and_excel_export(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    now = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)
    run_id = "arasrun1"
    session = FakeSession(
        entity_map={
            DBDocument: [
                SimpleNamespace(
                    run_id=run_id,
                    source_id="google_news",
                    title="Investigacion por soborno en Acme",
                    url="https://example.com/aras-1",
                    text="Acme enfrenta una investigacion por soborno y fraude.",
                    excerpt="Acme enfrenta una investigacion por soborno y fraude.",
                    hash="hash-aras-1",
                    fetch_method="http",
                    fetched_at=now,
                    published_at=now,
                    category="Fraude",
                    severity="H",
                    relevance_score=91,
                ),
            ],
            PipelineRun: [
                SimpleNamespace(
                    run_id=run_id,
                    started_at=now,
                    params_json={
                        "company": "Acme",
                        "date_from": "2026-03-01",
                        "date_to": "2026-03-31",
                    },
                ),
            ],
        },
    )

    async def _fake_search_google_news(query: str, max_items: int = 30) -> list[dict[str, Any]]:
        return [
            {
                "title": "Investigacion por soborno en Acme",
                "summary": "Acme enfrenta una investigacion por soborno y fraude.",
                "url": "https://example.com/aras-1",
                "source": "google_news",
                "published_at": now.isoformat(),
            },
        ]

    def _fake_filter_aras_candidates(
        queue_items: list[Any],
        company: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> Any:
        return SimpleNamespace(candidates=[SimpleNamespace(url="https://example.com/aras-1")])

    async def _fake_search_documents(self: DBAdapter, **kwargs: Any) -> list[Any]:
        return []

    class _FakeClassifier:
        def classify(self, text: str, title: str, query_type: str) -> Any:
            return SimpleNamespace(
                label="fraude",
                confidence=0.94,
                matched_keywords=["soborno", "fraude"],
            )

    class _FakeReranker:
        def rerank(self, doc: Any, query_context: str, heuristic_score: int) -> tuple[int, str]:
            return 91, "relevant"

    class _FakeSeverityScorer:
        def score(self, text: str, title: str) -> Any:
            return SimpleNamespace(
                severity="H",
                evidence_spans=[
                    SimpleNamespace(text="soborno"),
                    SimpleNamespace(text="fraude"),
                ],
            )

    class _FakeExporter:
        def export(self, docs: list[Any], output_path: str | Path, metadata: dict[str, Any] | None = None) -> Path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fake-aras-export")
            return path

    monkeypatch.setattr(aras_routes, "search_google_news", _fake_search_google_news)
    monkeypatch.setattr(
        "newsradar_api.domain.usecase.aras_filter.filter_aras_candidates",
        _fake_filter_aras_candidates,
    )
    monkeypatch.setattr(DBAdapter, "search_documents", _fake_search_documents)
    monkeypatch.setattr(aras_routes, "_get_llm_classifier", lambda: _FakeClassifier())
    monkeypatch.setattr(aras_routes, "_get_llm_reranker", lambda flow="aras_news": _FakeReranker())
    monkeypatch.setattr(aras_routes, "_get_excel_exporter", lambda: _FakeExporter())
    monkeypatch.setattr(aras_routes, "SeverityScorer", _FakeSeverityScorer)
    monkeypatch.setattr(export_routes, "EXPORT_DIR", tmp_path)
    vigilancia_routes._subscription_manager = None
    vigilancia_routes._cluster_engine = None

    with build_client(monkeypatch, session) as client:
        search_response = client.post(
            "/api/aras/search",
            json={
                "company": "Acme",
                "classifier": "llm",
                "date_from": "2026-03-01",
                "date_to": "2026-03-31",
            },
        )
        assert search_response.status_code == 200
        payload = search_response.json()
        assert payload["total_documents"] == 1
        assert payload["total_classified"] == 1
        assert payload["excel_url"] == f"/api/export/download/{payload['run_id']}_aras.xlsx"

        result = payload["results"][0]
        assert result["category"] == "Fraude"
        assert result["severity"] == "H"
        assert result["evidence"] == ["soborno", "fraude"]
        assert result["matched_keywords"] == ["soborno", "fraude"]
        assert result["relevance_score"] == 91

        export_response = client.post(
            "/api/export/excel",
            json={"run_id": run_id, "filters": {"category": "Fraude"}},
        )
        assert export_response.status_code == 200
        export_payload = export_response.json()
        assert export_payload["file_name"] == f"{run_id}_export.xlsx"
        assert export_payload["total_rows"] == 1

        download = client.get(export_payload["file_url"])
        assert download.status_code == 200
        assert (
            download.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    app.dependency_overrides.clear()


def test_vigilancia_subscription_validation_and_clustered_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession(entity_map={Subscription: []})

    async def _fake_run_search(
        mode: str,
        out_dir: str | Path,
        terms: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        terms_path: str | Path | None = None,
        since_days: int = 30,
        max_per_term: int = 20,
    ) -> tuple[list[SearchCandidate], SearchReport]:
        candidates = [
            SearchCandidate(
                mode=mode,
                term="inteligencia artificial",
                title="Nuevo paper de IA para banca",
                url="https://example.com/paper-1",
                snippet="Estudio sobre agentes de IA para banca digital.",
                published_at="2026-03-20T00:00:00+00:00",
                source_provider="arxiv",
                score=0.92,
            ),
            SearchCandidate(
                mode=mode,
                term="blockchain",
                title="Tokenizacion bancaria con blockchain",
                url="https://example.com/paper-2",
                snippet="Analisis de tokenizacion y activos digitales.",
                published_at="2026-03-21T00:00:00+00:00",
                source_provider="arxiv",
                score=0.81,
            ),
        ]
        report = SearchReport(
            mode=mode,
            terms_count=len(terms or []),
            total_candidates=len(candidates),
            by_term={candidate.term: 1 for candidate in candidates},
            providers_used=["arxiv"],
            errors=[],
            duration_seconds=0.12,
        )
        return candidates, report

    monkeypatch.setattr(
        "newsradar_api.infrastructure.connectors.search_orchestrator.run_search",
        _fake_run_search,
    )
    vigilancia_routes._subscription_manager = None
    vigilancia_routes._cluster_engine = None

    with build_client(monkeypatch, session) as client:
        subscribe_response = client.post(
            "/api/vigilancia/subscribe",
            json={
                "email": "analista@example.com",
                "name": "Analista",
                "query_groups": ["ia_ml", "blockchain"],
            },
        )
        assert subscribe_response.status_code == 200
        assert subscribe_response.json()["subscribed_groups"] == ["ia_ml", "blockchain"]
        assert len(session.entity_map.get(Subscription, [])) == 1

        search_response = client.post(
            "/api/vigilancia/search",
            json={
                "query_groups": ["ia_ml", "blockchain"],
                "mode": "papers",
                "since_days": 30,
                "max_per_term": 5,
            },
        )
        assert search_response.status_code == 200
        payload = search_response.json()
        assert payload["query_groups"] == ["ia_ml", "blockchain"]
        assert payload["mode"] == "papers"
        assert payload["total_results"] == 2
        assert payload["report"]["providers_used"] == ["arxiv"]
        assert payload["clusters"][0]["cluster_id"] == "all_items"
        assert sorted(payload["results"][0]["matched_groups"]) == ["ia_ml"]
        assert sorted(payload["results"][1]["matched_groups"]) == ["blockchain"]

        invalid_response = client.post(
            "/api/vigilancia/search",
            json={
                "query_groups": ["grupo_inexistente"],
                "mode": "papers",
            },
        )
        assert invalid_response.status_code == 400
        assert "Grupos inexistentes" in invalid_response.json()["detail"]

    app.dependency_overrides.clear()
