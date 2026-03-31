"""HTTP client adapter for the local newsradar_smcp service."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MCPClientAdapter:
    """Thin HTTP client for SMCP tool endpoints."""

    def __init__(self, server_url: str = "http://localhost:8080") -> None:
        self._server_url = server_url.rstrip("/")

    async def invoke_tool(self, tool_name: str, params: dict) -> dict[str, Any]:
        endpoint = tool_name if tool_name.startswith("/tools/") else f"/tools/{tool_name}"
        url = f"{self._server_url}{endpoint}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
            return response.json()
