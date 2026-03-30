"""API configuration and dependency injection.

Loads settings from environment/YAML and wires domain use cases
to infrastructure adapters (MCP client, SMTP, DB).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiConfig:
    """Configuration for the Backend API.

    Attributes
    ----------
    mcp_server_url : str
        URL of the newsradar_smcp MCP server.
    aiagent_ws_url : str
        WebSocket URL of the newsradar_aiagent for chat proxy.
    smtp_host : str
        SMTP server host for newsletter delivery.
    smtp_port : int
        SMTP server port.
    db_url : str
        Database connection URL for subscriptions persistence.
    """

    mcp_server_url: str = "http://localhost:8080"
    aiagent_ws_url: str = "ws://localhost:8081/chat"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    db_url: str = "sqlite:///subscriptions.db"

    @classmethod
    def load(cls) -> ApiConfig:
        """Load configuration from environment variables or YAML.

        Returns
        -------
        ApiConfig
            Populated configuration instance.
        """
        # TODO: Load from env vars / YAML file
        return cls()


def create_container(config: ApiConfig | None = None) -> dict:
    """Create and wire the DI container.

    Parameters
    ----------
    config : ApiConfig | None
        API configuration. Uses defaults if None.

    Returns
    -------
    dict
        Container with wired dependencies.
    """
    # TODO: Wire MCP client, SMTP adapter, DB adapter, and use cases
    raise NotImplementedError("TODO: implement DI container wiring")
