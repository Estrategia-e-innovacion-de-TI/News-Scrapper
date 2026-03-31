"""WebSocket chat endpoint — proxy to newsradar_aiagent.

WS /api/chat — Bidirectional chat proxy that forwards user messages
to the AI agent's ``handle_message`` function and relays responses
back to the frontend as JSON.

Message protocol (frontend ↔ backend):
  → Client sends: plain text string (the user message)
  ← Server sends: JSON ``{"message": "...", "conversation_id": "..."}``
  ← On error:     JSON ``{"error": "..."}``
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# Agent server URL — configurable via env var, defaults to localhost.
_AGENT_URL: str = os.getenv("AIAGENT_URL", "http://localhost:8090")
_MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", os.getenv("NEWSRADAR_SMCP_URL", "http://localhost:8080"))
_BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")


@router.websocket("/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint that proxies chat to the AI agent.

    For each incoming text frame the endpoint:
    1. Forwards the user message to the aiagent via HTTP POST
       (or direct function call when running in-process).
    2. Relays the agent's JSON response back to the client.

    Parameters
    ----------
    websocket : WebSocket
        Incoming WebSocket connection from the frontend ChatWidget.
    """
    await websocket.accept()
    conversation_id: str | None = None

    try:
        while True:
            user_message = await websocket.receive_text()
            if not user_message.strip():
                continue

            logger.info("Chat WS received: %s", user_message[:120])

            try:
                result = await _forward_to_agent(
                    user_message, conversation_id
                )
                conversation_id = result.get("conversation_id", conversation_id)
                await websocket.send_text(json.dumps(result, ensure_ascii=False))
            except Exception:  # noqa: BLE001
                logger.exception("Error forwarding message to agent")
                await websocket.send_text(
                    json.dumps({"error": "Error interno al procesar el mensaje."})
                )
    except WebSocketDisconnect:
        logger.info("Chat WebSocket client disconnected")


async def _forward_to_agent(
    user_message: str,
    conversation_id: str | None,
) -> dict[str, Any]:
    """Forward a user message to the AI agent and return its response.

    Strategy (in order of preference):
    1. Direct in-process call to ``handle_message`` — fastest, no network.
       Used when the aiagent package is importable (monorepo / same process).
    2. HTTP POST to the aiagent service — used in production when the
       agent runs as a separate ECS task.

    Returns
    -------
    dict
        Agent response with keys ``message`` and ``conversation_id``.
    """
    # --- Strategy 1: direct in-process call ---
    try:
        from newsradar_agent.infrastructure.entry_points.standalone import (
            handle_message,
        )

        return handle_message(
            user_message,
            conversation_id=conversation_id,
            mcp_server_url=_MCP_SERVER_URL,
            backend_url=_BACKEND_URL,
        )
    except ImportError:
        logger.debug("aiagent not importable — falling back to HTTP proxy")

    # --- Strategy 2: HTTP POST to aiagent service ---
    # TODO: Replace with proper async HTTP client in production
    import httpx

    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "message": user_message,
            "conversation_id": conversation_id,
        }
        response = await client.post(f"{_AGENT_URL}/chat", json=payload)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
