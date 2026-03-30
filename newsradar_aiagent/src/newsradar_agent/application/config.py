"""Agent configuration and dependency injection.

Loads settings from environment/YAML and wires domain use cases
to infrastructure adapters (MCP client, Bedrock LLM).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    """Configuration for the AI Agent.

    Attributes
    ----------
    bedrock_model_id : str
        Amazon Bedrock model ID for LLM reasoning.
    bedrock_region : str
        AWS region for Bedrock API calls.
    mcp_server_url : str
        URL of the newsradar_smcp MCP server to consume tools from.
    max_conversation_turns : int
        Maximum turns in a single conversation before reset.
    """

    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_region: str = "us-east-1"
    mcp_server_url: str = "http://localhost:8080"
    max_conversation_turns: int = 20

    @classmethod
    def load(cls) -> AgentConfig:
        """Load configuration from environment variables or YAML.

        Returns
        -------
        AgentConfig
            Populated configuration instance.
        """
        # TODO: Load from env vars / YAML file
        return cls()


def create_container(config: AgentConfig | None = None) -> dict:
    """Create and wire the DI container.

    Parameters
    ----------
    config : AgentConfig | None
        Agent configuration. Uses defaults if None.

    Returns
    -------
    dict
        Container with wired dependencies.
    """
    # TODO: Wire MCP client, Bedrock LLM, and use cases
    # from newsradar_agent.infrastructure.driven_adapters.mcp_client import MCPClient
    # from newsradar_agent.infrastructure.driven_adapters.bedrock_llm import BedrockLLM
    # from newsradar_agent.domain.usecase.aras_chat import ArasChatUseCase
    # from newsradar_agent.domain.usecase.riesgos_chat import RiesgosChatUseCase
    raise NotImplementedError("TODO: implement DI container wiring")
