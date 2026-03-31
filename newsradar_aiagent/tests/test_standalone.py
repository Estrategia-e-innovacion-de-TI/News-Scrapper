from __future__ import annotations

from newsradar_agent.infrastructure.driven_adapters.backend_client import BackendClient
from newsradar_agent.infrastructure.driven_adapters.mcp_client import MCPClient
from newsradar_agent.infrastructure.entry_points import standalone


class FakeMCPClient(MCPClient):
    def __init__(self) -> None:
        super().__init__("http://fake-smcp")
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, tool_name: str, arguments: dict | None = None):
        payload = arguments or {}
        self.calls.append((tool_name, payload))
        return {
            "total_documents": 2,
            "results": [
                {
                    "title": "Bancolombia bajo investigacion",
                    "category": "Fraude",
                    "severity": "H",
                    "relevance_score": 90,
                }
            ],
            "excel_url": "/api/export/download/demo.xlsx",
        }


class FakeBackendClient(BackendClient):
    def __init__(self) -> None:
        super().__init__("http://fake-backend")

    def trendmap_latest(self) -> dict:
        return {
            "generated_at": "2026-03-31T00:00:00+00:00",
            "summary": {
                "total_documents": 12,
                "total_clusters": 3,
                "dominant_topics": ["IA", "Blockchain"],
                "executive_summary": "IA y blockchain concentran la mayor actividad.",
            },
            "clusters": [],
        }

    def riskmap_latest(self) -> dict:
        return {
            "generated_at": "2026-03-31T00:00:00+00:00",
            "summary": {
                "total_documents": 18,
                "total_clusters": 4,
                "dominant_risks": ["ciberseguridad", "clima y naturaleza"],
                "executive_summary": "Ciberseguridad domina el mapa de riesgos.",
            },
            "clusters": [],
        }

    def jobs_status(self) -> list[dict]:
        return [{"job_group": "tech_watch", "job_name": "tech_watch_ingest", "last_status": "completed", "last_finished_at": "2026-03-31T01:00:00+00:00"}]

    def tech_watch_executions(self) -> list[dict]:
        return [{"run_key": "run-123", "status": "completed"}]


def _fake_container():
    return {
        "mcp_client": FakeMCPClient(),
        "backend_client": FakeBackendClient(),
        "config": object(),
    }


def test_handle_message_routes_aras_query(monkeypatch) -> None:
    standalone._conversations.clear()
    monkeypatch.setattr(standalone, "create_container", lambda config: _fake_container())

    result = standalone.handle_message("Busca noticias asociadas a Bancolombia en el ultimo mes")

    assert result["intent"] == "aras_search"
    assert "ARAS: encontre 2 documento(s)." in result["message"]
    assert "Bancolombia bajo investigacion" in result["message"]


def test_handle_message_reads_latest_trendmap(monkeypatch) -> None:
    standalone._conversations.clear()
    monkeypatch.setattr(standalone, "create_container", lambda config: _fake_container())

    result = standalone.handle_message("muestrame el trendmap actual")

    assert result["intent"] == "trendmap_latest"
    assert "Trend Mapping" in result["message"]
    assert "IA, Blockchain" in result["message"]


def test_handle_message_reads_tech_watch_status(monkeypatch) -> None:
    standalone._conversations.clear()
    monkeypatch.setattr(standalone, "create_container", lambda config: _fake_container())

    result = standalone.handle_message("estado de vigilancia tecnologica")

    assert result["intent"] == "tech_watch_status"
    assert "run-123" in result["message"]
    assert "tech_watch_ingest" in result["message"]
