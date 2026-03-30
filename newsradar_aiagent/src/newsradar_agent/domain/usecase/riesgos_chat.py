"""Use case: Riesgos Emergentes conversational chat.

Handles multi-turn conversation for Riesgos ad-hoc queries.
Detects intent, extracts parameters (terms, preset, date range),
invokes MCP tools via the driven adapter, and generates responses
using the Bedrock LLM.
"""
from __future__ import annotations

from typing import Any, Protocol

from newsradar_agent.domain.model.conversation import ConversationState, Message, Role


class MCPToolPort(Protocol):
    """Port for invoking MCP tools on newsradar_smcp."""

    def call_tool(self, tool_name: str, arguments: dict) -> Any: ...


class LLMPort(Protocol):
    """Port for LLM reasoning (Bedrock)."""

    def invoke(self, system_prompt: str, messages: list[dict]) -> str: ...


class RiesgosChatUseCase:
    """Orchestrates the Riesgos Emergentes conversational flow.

    Parameters
    ----------
    mcp_client : MCPToolPort
        Adapter to call newsradar_smcp MCP tools.
    llm : LLMPort
        Adapter for Bedrock LLM reasoning.
    """

    def __init__(self, mcp_client: MCPToolPort, llm: LLMPort) -> None:
        self._mcp = mcp_client
        self._llm = llm

    def handle_message(
        self, state: ConversationState, user_message: str
    ) -> ConversationState:
        """Process a user message in the Riesgos chat flow.

        Parameters
        ----------
        state : ConversationState
            Current conversation state.
        user_message : str
            The user's latest message.

        Returns
        -------
        ConversationState
            Updated conversation state with agent response.
        """
        # TODO: Implement Riesgos chat flow:
        # 1. Append user message to state
        # 2. Detect intent via LLM (riesgos_search, clarification, etc.)
        # 3. If riesgos_search: extract terms/preset, date range
        # 4. Call MCP tool (riesgos_adhoc) via mcp_client
        # 5. Generate response summary via LLM
        # 6. Append agent response to state
        state.messages.append(Message(role=Role.USER, content=user_message))
        state.turn_count += 1
        raise NotImplementedError("TODO: implement Riesgos chat flow")
