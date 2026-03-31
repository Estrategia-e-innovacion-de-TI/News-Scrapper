"""Use case: ARAS ad-hoc search.

Orchestrates an ARAS news search by invoking the MCP server pipeline
and returning classified, scored results.
"""
from __future__ import annotations

from newsradar_api.domain.model.dtos import ArasSearchRequest, ArasSearchResponse


class SearchArasUseCase:
    """Execute an ARAS ad-hoc search via the MCP server.

    Parameters
    ----------
    mcp_client : object
        MCP client adapter to invoke newsradar_smcp tools.
    """

    def __init__(self, mcp_client: object) -> None:
        self._mcp = mcp_client

    async def execute(self, request: ArasSearchRequest) -> ArasSearchResponse:
        """Run the ARAS search pipeline.

        Parameters
        ----------
        request : ArasSearchRequest
            Search parameters (company/NIT, category, dates, classifier).

        Returns
        -------
        ArasSearchResponse
            Classified results with optional Excel download URL.
        """
        result = await self._mcp.invoke_tool(
            "aras_search",
            request.model_dump(mode="json"),
        )
        return ArasSearchResponse(**result)
