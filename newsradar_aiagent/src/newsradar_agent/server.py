"""Main server entry point for the News Radar AI Agent.

Bootstraps the agent, wires dependencies, and starts the server
in either standalone or A2A mode.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the AI Agent server.

    1. Load configuration
    2. Initialize DI container (MCP client, Bedrock LLM)
    3. Select entry point mode (standalone or A2A)
    4. Start serving
    """
    # TODO: Implement server bootstrap
    # from newsradar_agent.application.config import AgentConfig
    # config = AgentConfig.load()
    # ...
    logger.info("newsradar_aiagent server starting...")
    raise NotImplementedError("TODO: implement AI agent server bootstrap")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
