"""Use case: Riesgos Emergentes ad-hoc search.

Orchestrates a Riesgos news search by invoking the MCP server pipeline
and returning classified, scored results.
"""
from __future__ import annotations

from newsradar_api.domain.model.dtos import RiesgosSearchRequest, RiesgosSearchResponse


class SearchRiesgosUseCase:
    """Execute a Riesgos Emergentes ad-hoc search via the MCP server.

    Parameters
    ----------
    mcp_client : object
        MCP client adapter to invoke newsradar_smcp tools.
    """

    def __init__(self, mcp_client: object) -> None:
        self._mcp = mcp_client

    async def execute(self, request: RiesgosSearchRequest) -> RiesgosSearchResponse:
        """Run the Riesgos search pipeline.

        Parameters
        ----------
        request : RiesgosSearchRequest
            Search parameters (terms/preset, dates, classifier).

        Returns
        -------
        RiesgosSearchResponse
            Classified results with optional Excel download URL.
        """
        result = await self._mcp.invoke_tool(
            "riesgos_search",
            request.model_dump(mode="json"),
        )
        return RiesgosSearchResponse(**result)
