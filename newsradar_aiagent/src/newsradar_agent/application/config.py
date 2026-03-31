"""Agent configuration and lightweight dependency wiring."""
from __future__ import annotations

from dataclasses import dataclass
import os

from newsradar_agent.infrastructure.driven_adapters.backend_client import BackendClient
from newsradar_agent.infrastructure.driven_adapters.mcp_client import MCPClient


@dataclass
class AgentConfig:
    """Runtime configuration for the NewsRadar AI agent."""

    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_region: str = "us-east-1"
    mcp_server_url: str = "http://localhost:8080"
    backend_url: str = "http://localhost:8000"
    max_conversation_turns: int = 20

    @classmethod
    def load(cls) -> "AgentConfig":
        return cls(
            bedrock_model_id=os.getenv(
                "NEWSRADAR_BEDROCK_MODEL_ID",
                "anthropic.claude-3-haiku-20240307-v1:0",
            ),
            bedrock_region=os.getenv("NEWSRADAR_BEDROCK_REGION", "us-east-1"),
            mcp_server_url=os.getenv("NEWSRADAR_SMCP_URL", "http://localhost:8080"),
            backend_url=os.getenv("NEWSRADAR_BACK_URL", "http://localhost:8000"),
            max_conversation_turns=int(os.getenv("NEWSRADAR_MAX_TURNS", "20")),
        )


def create_container(config: AgentConfig | None = None) -> dict[str, object]:
    cfg = config or AgentConfig.load()
    return {
        "config": cfg,
        "mcp_client": MCPClient(server_url=cfg.mcp_server_url),
        "backend_client": BackendClient(base_url=cfg.backend_url),
    }
