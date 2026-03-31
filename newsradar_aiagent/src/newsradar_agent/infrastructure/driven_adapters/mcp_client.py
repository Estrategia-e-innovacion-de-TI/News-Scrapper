"""MCP client adapter for NewsRadar SMCP tools."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TOOL_ENDPOINT_MAP: dict[str, str] = {
    "aras_search": "/tools/aras_search",
    "aras_adhoc": "/tools/aras_search",
    "risk_search": "/tools/riesgos_search",
    "riesgos_search": "/tools/riesgos_search",
    "riesgos_adhoc": "/tools/riesgos_search",
    "tech_watch_run": "/tools/vigilancia_weekly",
    "vigilancia_weekly": "/tools/vigilancia_weekly",
    "trendmap_generate": "/tools/vigilancia_historical",
    "vigilancia_historical": "/tools/vigilancia_historical",
    "extract_news": "/tools/extract_news",
}


class MCPClient:
    """Client adapter for the SMCP HTTP tool service."""

    def __init__(self, server_url: str = "http://localhost:8080", timeout: float = 120.0) -> None:
        self._server_url = server_url.rstrip("/")
        self._timeout = timeout

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        endpoint = _TOOL_ENDPOINT_MAP.get(tool_name, f"/tools/{tool_name}")
        url = f"{self._server_url}{endpoint}"
        payload = arguments or {}

        logger.info("MCP call_tool %s -> %s payload=%s", tool_name, url, payload)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "MCP tool %s returned HTTP %s: %s",
                tool_name,
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise MCPToolError(
                f"MCP tool '{tool_name}' failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("MCP tool %s request error: %s", tool_name, exc)
            raise MCPToolError(f"MCP tool '{tool_name}' unreachable: {exc}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("MCP tool %s response parse error: %s", tool_name, exc)
            raise MCPToolError(f"MCP tool '{tool_name}' returned invalid JSON") from exc

    def list_tools(self) -> list[dict[str, Any]]:
        url = f"{self._server_url}/tools"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception:
            logger.warning("Could not list MCP tools; server may be offline")
            return []


class MCPToolError(Exception):
    """Raised when an MCP tool invocation fails."""
