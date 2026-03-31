"""HTTP server entry point for the NewsRadar AI agent."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel

from newsradar_agent.application.config import AgentConfig
from newsradar_agent.infrastructure.entry_points.standalone import handle_message

logger = logging.getLogger(__name__)

_CONFIG = AgentConfig.load()


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="NewsRadar AI Agent", version="0.2.0")

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "smcp_url": _CONFIG.mcp_server_url,
            "backend_url": _CONFIG.backend_url,
        }

    @app.post("/chat")
    async def chat(request: ChatRequest) -> dict:
        return handle_message(
            request.message,
            conversation_id=request.conversation_id,
            mcp_server_url=_CONFIG.mcp_server_url,
            backend_url=_CONFIG.backend_url,
        )

    return app


app = create_app()


def main() -> None:
    logger.info("newsradar_aiagent server starting")
    import uvicorn

    uvicorn.run("newsradar_agent.server:app", host="0.0.0.0", port=8090)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
