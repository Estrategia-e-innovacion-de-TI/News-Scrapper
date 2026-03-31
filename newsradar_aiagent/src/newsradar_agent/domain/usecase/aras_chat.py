"""Use case: ARAS conversational chat."""
from __future__ import annotations

import re
from typing import Any, Protocol

from newsradar_agent.domain.model.conversation import ConversationState, Message, Role


class MCPToolPort(Protocol):
    def call_tool(self, tool_name: str, arguments: dict) -> Any: ...


class LLMPort(Protocol):
    def invoke(self, system_prompt: str, messages: list[dict]) -> str: ...


class ArasChatUseCase:
    """Thin wrapper around the ARAS search capability."""

    def __init__(self, mcp_client: MCPToolPort, llm: LLMPort | None = None) -> None:
        self._mcp = mcp_client
        self._llm = llm

    def handle_message(self, state: ConversationState, user_message: str) -> ConversationState:
        state.messages.append(Message(role=Role.USER, content=user_message))
        state.turn_count += 1

        nit_match = re.search(r"\b\d{6,12}(?:-\d)?\b", user_message)
        company = user_message.strip()
        payload = {
            "company": company,
            "nit": nit_match.group(0) if nit_match else None,
            "classifier": "rules",
        }
        result = self._mcp.call_tool("aras_search", payload)
        total = int(result.get("total_documents", 0))
        reply = f"ARAS: encontre {total} documento(s)."
        if result.get("results"):
            top = result["results"][0]
            reply += f" Hallazgo principal: {top.get('title', 'Sin titulo')}."

        state.messages.append(Message(role=Role.AGENT, content=reply, metadata={"tool": "aras_search"}))
        state.context.update({k: v for k, v in payload.items() if v})
        return state
