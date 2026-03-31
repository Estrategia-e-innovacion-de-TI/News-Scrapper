"""API configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ApiConfig:
    database_url: str = ""
    aiagent_ws_url: str = "ws://localhost:8081/chat"
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"

    @classmethod
    def load(cls) -> ApiConfig:
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://newsradar:newsradar@localhost:5432/newsradar",
            ),
            aiagent_ws_url=os.getenv("AIAGENT_URL", "ws://localhost:8081/chat"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            bedrock_model_id=os.getenv(
                "BEDROCK_MODEL_ID",
                "anthropic.claude-3-haiku-20240307-v1:0",
            ),
            bedrock_embed_model_id=os.getenv(
                "BEDROCK_EMBED_MODEL_ID",
                "amazon.titan-embed-text-v2:0",
            ),
        )
