"""Application bootstrap — entry point for the MCP server.

Initializes the DI container, wires ports to infrastructure adapters,
and starts the MCP server.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def create_app() -> None:
    """Bootstrap the MCP server application.

    1. Load configuration
    2. Initialize DI container
    3. Register MCP tools
    4. Start server
    """
    # TODO: Implement application bootstrap
    # from newsradar_server.application.config.container import Container
    # container = Container()
    # container.wire()
    logger.info("newsradar_smcp server starting...")
    raise NotImplementedError("TODO: implement MCP server bootstrap")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app()
