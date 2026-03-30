"""Standalone entry point — direct user-to-agent interaction.

Provides both a CLI REPL and an ``async handle_message`` function
that the backend WebSocket proxy can call to process a single
user message and get an agent response.
"""
from __future__ import annotations

import logging
from uuid import uuid4

from newsradar_agent.domain.model.conversation import (
    ConversationState,
    Message,
    Role,
)
from newsradar_agent.infrastructure.driven_adapters.mcp_client import (
    MCPClient,
    MCPToolError,
)

logger = logging.getLogger(__name__)

# ── In-memory conversation store (keyed by conversation_id) ──────────
_conversations: dict[str, ConversationState] = {}


def _get_or_create_conversation(conversation_id: str | None = None) -> ConversationState:
    """Return an existing conversation or create a new one."""
    if conversation_id and conversation_id in _conversations:
        return _conversations[conversation_id]
    cid = conversation_id or str(uuid4())
    state = ConversationState(conversation_id=cid)
    _conversations[cid] = state
    return state


def handle_message(
    user_message: str,
    conversation_id: str | None = None,
    *,
    mcp_server_url: str = "http://localhost:8080",
) -> dict:
    """Process a single user message and return the agent response.

    This is the main entry point used by the backend WebSocket proxy.
    It keeps conversation state in-memory and routes to the appropriate
    MCP tool based on simple keyword-based intent detection.

    Parameters
    ----------
    user_message : str
        The user's chat message.
    conversation_id : str | None
        Optional conversation ID for multi-turn context.
    mcp_server_url : str
        URL of the newsradar_smcp MCP server.

    Returns
    -------
    dict
        ``{"message": str, "conversation_id": str}`` with the agent reply.
    """
    state = _get_or_create_conversation(conversation_id)
    state.messages.append(Message(role=Role.USER, content=user_message))
    state.turn_count += 1

    # --- Simple keyword-based intent detection ---
    lower = user_message.lower()
    intent = _detect_intent(lower)

    try:
        reply = _dispatch(intent, lower, mcp_server_url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent error processing message")
        reply = f"Lo siento, ocurrió un error al procesar tu solicitud: {exc}"

    state.messages.append(Message(role=Role.AGENT, content=reply))
    return {"message": reply, "conversation_id": state.conversation_id}


# ── Intent detection (lightweight, no LLM) ───────────────────────────

_ARAS_KEYWORDS = {"aras", "empresa", "nit", "lavado", "corrupcion", "sanciones", "pep"}
_RIESGOS_KEYWORDS = {"riesgo", "ciber", "fraude", "operacional", "ambiental", "ransomware", "phishing"}
_GREETING_KEYWORDS = {"hola", "hello", "hi", "buenos", "buenas"}


def _detect_intent(text: str) -> str:
    """Return one of: 'aras', 'riesgos', 'greeting', 'unknown'."""
    if any(kw in text for kw in _GREETING_KEYWORDS):
        return "greeting"
    if any(kw in text for kw in _ARAS_KEYWORDS):
        return "aras"
    if any(kw in text for kw in _RIESGOS_KEYWORDS):
        return "riesgos"
    return "unknown"


# ── Dispatch to MCP tools ────────────────────────────────────────────

def _dispatch(intent: str, text: str, mcp_server_url: str) -> str:
    """Route the detected intent to the appropriate MCP tool."""
    if intent == "greeting":
        return (
            "¡Hola! Soy el asistente de News Radar. Puedo ayudarte con "
            "búsquedas ARAS (empresa/NIT) o Riesgos Emergentes (términos/preset). "
            "¿Qué necesitas?"
        )

    if intent == "aras":
        return _handle_aras(text, mcp_server_url)

    if intent == "riesgos":
        return _handle_riesgos(text, mcp_server_url)

    return (
        "No estoy seguro de cómo ayudarte con eso. Puedo buscar noticias "
        "ARAS por empresa/NIT o Riesgos Emergentes por términos. "
        "¿Podrías reformular tu pregunta?"
    )


def _handle_aras(text: str, mcp_server_url: str) -> str:
    """Invoke the aras_adhoc MCP tool and summarise the result."""
    # TODO: Extract company/NIT from text using LLM in production
    # For now, use the raw text as the company query
    mcp = MCPClient(server_url=mcp_server_url)
    try:
        result = mcp.call_tool("aras_adhoc", {"company": text})
        total = result.get("total_documents", 0)
        return (
            f"Encontré {total} documento(s) en la búsqueda ARAS. "
            f"Resumen: {result.get('summary', 'Sin resumen disponible.')}"
        )
    except MCPToolError as exc:
        logger.warning("ARAS MCP tool failed: %s", exc)
        return (
            "No pude completar la búsqueda ARAS en este momento. "
            "El servicio de pipeline podría no estar disponible. "
            "Intenta de nuevo más tarde."
        )


def _handle_riesgos(text: str, mcp_server_url: str) -> str:
    """Invoke the riesgos_adhoc MCP tool and summarise the result."""
    # TODO: Extract terms/preset from text using LLM in production
    terms = [w.strip() for w in text.split() if len(w.strip()) > 3][:5]
    mcp = MCPClient(server_url=mcp_server_url)
    try:
        result = mcp.call_tool("riesgos_adhoc", {"terms": terms})
        total = result.get("total_documents", 0)
        return (
            f"Encontré {total} documento(s) en la búsqueda de Riesgos. "
            f"Resumen: {result.get('summary', 'Sin resumen disponible.')}"
        )
    except MCPToolError as exc:
        logger.warning("Riesgos MCP tool failed: %s", exc)
        return (
            "No pude completar la búsqueda de Riesgos en este momento. "
            "El servicio de pipeline podría no estar disponible. "
            "Intenta de nuevo más tarde."
        )


# ── CLI REPL ─────────────────────────────────────────────────────────

def run_standalone() -> None:
    """Run the agent in standalone interactive CLI mode."""
    print("News Radar AI Agent — escribe 'exit' para salir")
    cid = str(uuid4())
    while True:
        try:
            user_input = input("Tú: ")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() in ("exit", "quit", "salir"):
            break
        result = handle_message(user_input, conversation_id=cid)
        print(f"Agente: {result['message']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_standalone()
