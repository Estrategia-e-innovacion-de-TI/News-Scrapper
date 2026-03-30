"""A2A protocol entry point — placeholder for future Agent-to-Agent communication.

This module will implement the A2A (Agent-to-Agent) protocol, allowing
other agents or the backend API to communicate with this agent using
a standardized protocol.

See: https://google.github.io/A2A/
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_a2a_server(host: str = "0.0.0.0", port: int = 8081) -> None:
    """Start the agent in A2A protocol mode.

    Parameters
    ----------
    host : str
        Host to bind the A2A server.
    port : int
        Port to listen on.
    """
    # TODO: Implement A2A protocol server
    # This will expose the agent's capabilities via the A2A protocol,
    # enabling:
    # - Agent card discovery
    # - Task submission and streaming
    # - Multi-turn conversation via A2A messages
    logger.info("A2A server placeholder — not yet implemented")
    raise NotImplementedError("TODO: implement A2A protocol entry point")
