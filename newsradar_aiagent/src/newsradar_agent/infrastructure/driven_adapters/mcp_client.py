"""MCP client adapter — consumes newsradar_smcp MCP tools.

Connects to the newsradar_smcp MCP server and invokes tools
(aras_adhoc, riesgos_adhoc, etc.) on behalf of the agent.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Mapping of logical tool names to the MCP server HTTP endpoints.
# In a production MCP setup this would use the MCP SDK's ClientSession;
# for now we use a lightweight HTTP adapter that POSTs to the smcp server.
_TOOL_ENDPOINT_MAP: dict[str, str] = {
    "aras_adhoc": "/tools/aras_search",
    "riesgos_adhoc": "/tools/riesgos_search",
    "vigilancia_weekly": "/tools/vigilancia_weekly",
    "vigilancia_historical": "/tools/vigilancia_historical",
    "extract_news": "/tools/extract_news",
}


class MCPClient:
    """Client adapter for the newsradar_smcp MCP server.

    Uses HTTP POST to invoke MCP tools exposed by the smcp server.
    In production this should be replaced with a proper MCP SDK
    ``ClientSession`` for full protocol support (streaming, etc.).

    Parameters
    ----------
    server_url : str
        Base URL of the newsradar_smcp MCP server.
    timeout : float
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        timeout: float = 120.0,
    ) -> None:
        self._server_url = server_url.rstrip("/")
        self._timeout = timeout

    # -- public API --------------------------------------------------------

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Invoke an MCP tool on the newsradar_smcp server.

        Parameters
        ----------
        tool_name : str
            Logical tool name (e.g. ``"aras_adhoc"``, ``"riesgos_adhoc"``).
        arguments : dict | None
            Tool arguments forwarded as JSON body.

        Returns
        -------
        Any
            Parsed JSON response from the MCP server.

        Raises
        ------
        MCPToolError
            When the server returns a non-2xx status or the response
            cannot be parsed.
        """
        endpoint = _TOOL_ENDPOINT_MAP.get(tool_name, f"/tools/{tool_name}")
        url = f"{self._server_url}{endpoint}"
        payload = arguments or {}

        logger.info("MCP call_tool: %s → %s  payload=%s", tool_name, url, payload)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "MCP tool %s returned HTTP %s: %s",
                tool_name, exc.response.status_code, exc.response.text[:500],
            )
            raise MCPToolError(
                f"MCP tool '{tool_name}' failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("MCP tool %s request error: %s", tool_name, exc)
            raise MCPToolError(
                f"MCP tool '{tool_name}' unreachable: {exc}"
            ) from exc
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("MCP tool %s response parse error: %s", tool_name, exc)
            raise MCPToolError(
                f"MCP tool '{tool_name}' returned invalid JSON"
            ) from exc

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools on the MCP server.

        Returns
        -------
        list[dict]
            Tool definitions from the server.
        """
        url = f"{self._server_url}/tools"
        logger.info("MCP list_tools → %s", url)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]
        except Exception:
            logger.warning("Could not list MCP tools — server may be offline")
            return []


class MCPToolError(Exception):
    """Raised when an MCP tool invocation fails."""
