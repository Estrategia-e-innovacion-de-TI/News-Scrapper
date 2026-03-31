"""Lightweight A2A compatibility entry point for the NewsRadar agent."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel

from newsradar_agent.application.config import AgentConfig
from newsradar_agent.infrastructure.entry_points.standalone import handle_message

logger = logging.getLogger(__name__)

_CONFIG = AgentConfig.load()


class TaskRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="NewsRadar AI Agent A2A", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "mode": "a2a_compat"}

    @app.get("/agent-card")
    async def agent_card() -> dict:
        return {
            "name": "newsradar-aiagent",
            "description": "Conversational facade over NewsRadar backend and SMCP capabilities.",
            "capabilities": [
                "aras_search",
                "risk_search",
                "trendmap_latest",
                "riskmap_latest",
                "tech_watch_status",
            ],
            "transport": "http-json-compat",
        }

    @app.post("/tasks/send")
    async def send_task(request: TaskRequest) -> dict:
        return handle_message(
            request.message,
            conversation_id=request.conversation_id,
            mcp_server_url=_CONFIG.mcp_server_url,
            backend_url=_CONFIG.backend_url,
        )

    return app


def run_a2a_server(host: str = "0.0.0.0", port: int = 8081) -> None:
    logger.info("Starting NewsRadar A2A compatibility server on %s:%s", host, port)
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)
