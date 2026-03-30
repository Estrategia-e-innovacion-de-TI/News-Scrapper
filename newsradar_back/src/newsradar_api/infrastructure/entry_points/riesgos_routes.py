"""Riesgos Emergentes REST endpoints.

POST /api/riesgos/search — Execute a Riesgos ad-hoc news search.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from newsradar_api.domain.model.dtos import (
    DocumentResult,
    RiesgosSearchRequest,
    RiesgosSearchResponse,
)
from newsradar_api.infrastructure.driven_adapters.mcp_client import MCPClientAdapter

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Dependency injection ──────────────────────────────────────────────

_mcp_client: MCPClientAdapter | None = None


def get_mcp_client() -> MCPClientAdapter:
    """Return the shared MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        # TODO: Load server_url from ApiConfig / environment
        _mcp_client = MCPClientAdapter()
    return _mcp_client


# ── Route ─────────────────────────────────────────────────────────────


@router.post("/search", response_model=RiesgosSearchResponse)
async def search_riesgos(
    request: RiesgosSearchRequest,
    mcp: MCPClientAdapter = Depends(get_mcp_client),
) -> RiesgosSearchResponse:
    """Execute a Riesgos Emergentes ad-hoc search.

    Invokes the MCP server's ``tool_riesgos_search`` tool with the provided
    terms/preset and date range. Returns classified results with an optional
    Excel download URL.
    """
    logger.info(
        "POST /api/riesgos/search — terms=%s, preset=%s, classifier=%s",
        request.terms, request.terms_preset, request.classifier,
    )

    # Build MCP tool parameters from the request DTO
    tool_params: dict = {
        "terms": request.terms if request.terms else None,
        "terms_preset": request.terms_preset,
        "date_from": request.date_from.isoformat() if request.date_from else None,
        "date_to": request.date_to.isoformat() if request.date_to else None,
        "classifier_mode": request.classifier,
    }

    # Invoke the MCP server tool
    result = await mcp.invoke_tool("tool_riesgos_search", tool_params)

    # Map MCP result to response DTO
    documents = [
        DocumentResult(**doc) for doc in result.get("results", [])
    ]

    return RiesgosSearchResponse(
        run_id=result.get("run_id", ""),
        total_documents=result.get("total_documents", 0),
        total_classified=result.get("total_classified", 0),
        results=documents,
        excel_url=result.get("excel_path"),
    )
