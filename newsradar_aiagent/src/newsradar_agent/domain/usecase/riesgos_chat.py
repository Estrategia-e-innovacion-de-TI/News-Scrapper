"""Use case: risk conversational chat."""
from __future__ import annotations

import re
from typing import Any, Protocol

from newsradar_agent.domain.model.conversation import ConversationState, Message, Role


class MCPToolPort(Protocol):
    def call_tool(self, tool_name: str, arguments: dict) -> Any: ...


class LLMPort(Protocol):
    def invoke(self, system_prompt: str, messages: list[dict]) -> str: ...


class RiesgosChatUseCase:
    """Thin wrapper around the risk search capability."""

    def __init__(self, mcp_client: MCPToolPort, llm: LLMPort | None = None) -> None:
        self._mcp = mcp_client
        self._llm = llm

    def handle_message(self, state: ConversationState, user_message: str) -> ConversationState:
        state.messages.append(Message(role=Role.USER, content=user_message))
        state.turn_count += 1

        terms = [term for term in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", user_message.lower())[:6]]
        payload = {"terms": terms, "classifier": "rules"}
        result = self._mcp.call_tool("riesgos_search", payload)
        total = int(result.get("total_documents", 0))
        reply = f"Riesgos: encontre {total} documento(s)."
        if result.get("results"):
            top = result["results"][0]
            reply += f" Hallazgo principal: {top.get('title', 'Sin titulo')}."

        state.messages.append(Message(role=Role.AGENT, content=reply, metadata={"tool": "riesgos_search"}))
        state.context.update({k: v for k, v in payload.items() if v})
        return state
