"""Standalone entry point for the NewsRadar AI agent."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
import logging
import re
import unicodedata
from uuid import uuid4

from newsradar_agent.application.config import AgentConfig, create_container
from newsradar_agent.domain.model.conversation import ConversationState, Message, Role
from newsradar_agent.domain.model.intents import Intent, IntentType
from newsradar_agent.infrastructure.driven_adapters.backend_client import (
    BackendClient,
    BackendClientError,
)
from newsradar_agent.infrastructure.driven_adapters.mcp_client import MCPClient, MCPToolError

logger = logging.getLogger(__name__)

_conversations: dict[str, ConversationState] = {}

_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_GREETING_KEYWORDS = {"hola", "hello", "hi", "buenos dias", "buenas tardes", "buenas noches"}
_HELP_KEYWORDS = {"ayuda", "help", "que puedes hacer", "capacidades", "opciones"}
_ARAS_HINTS = {"aras", "empresa", "emisor", "nit", "sanciones", "pep", "lavado", "corrupcion"}
_RISK_HINTS = {
    "riesgo", "ciber", "fraude", "clima", "geopolit", "desinformacion",
    "malinformacion", "ia", "contaminacion", "ransomware", "phishing",
}
_STOPWORDS = {
    "aras", "riesgo", "riesgos", "mapa", "mapping", "trend", "trends", "risk", "latest",
    "quiero", "muestrame", "muestreme", "necesito", "busca", "buscar", "noticias", "sobre",
    "para", "del", "de", "la", "el", "los", "las", "en", "con", "por", "favor", "ultimo",
    "ultimos", "ultimo", "actual", "actuales", "informe", "analitico",
}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value.lower()).strip()


def _get_or_create_conversation(conversation_id: str | None = None) -> ConversationState:
    if conversation_id and conversation_id in _conversations:
        return _conversations[conversation_id]
    cid = conversation_id or str(uuid4())
    state = ConversationState(conversation_id=cid)
    _conversations[cid] = state
    return state


def _extract_nit(text: str) -> str | None:
    match = re.search(r"\b\d{6,12}(?:-\d)?\b", text)
    return match.group(0) if match else None


def _extract_company(text: str) -> str | None:
    patterns = [
        r"(?:empresa|emisor|issuer)\s+([A-Z0-9][A-Za-z0-9&().,\- ]{2,80})",
        r"(?:sobre|para|asociad[oa]s?\s+a)\s+([A-Z0-9][A-Za-z0-9&().,\- ]{2,80})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,:;")

    capitalized = re.findall(r"\b([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3})\b", text)
    for candidate in capitalized:
        clean = candidate.strip()
        if clean.lower() not in {"aras", "risk", "trend", "news", "radar"}:
            return clean
    return None


def _extract_date_range(text: str) -> dict[str, str]:
    normalized = _normalize_text(text)
    today = datetime.now(timezone.utc).date()

    explicit = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if len(explicit) >= 2:
        return {"date_from": explicit[0], "date_to": explicit[1]}

    month_match = re.search(
        r"\b(" + "|".join(_MONTHS.keys()) + r")\s+(?:de\s+)?(20\d{2})\b",
        normalized,
    )
    if month_match:
        month = _MONTHS[month_match.group(1)]
        year = int(month_match.group(2))
        last_day = calendar.monthrange(year, month)[1]
        return {
            "date_from": date(year, month, 1).isoformat(),
            "date_to": date(year, month, last_day).isoformat(),
        }

    months_match = re.search(r"\bultim(?:o|os)\s+(\d+)\s+mes", normalized)
    if months_match:
        months = max(1, int(months_match.group(1)))
        return {
            "date_from": (today - timedelta(days=months * 30)).isoformat(),
            "date_to": today.isoformat(),
        }

    if "ultimo mes" in normalized:
        return {
            "date_from": (today - timedelta(days=30)).isoformat(),
            "date_to": today.isoformat(),
        }

    if "ultimo ano" in normalized or "ultimo anio" in normalized:
        return {
            "date_from": (today - timedelta(days=365)).isoformat(),
            "date_to": today.isoformat(),
        }

    return {}


def _extract_terms(text: str) -> list[str]:
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', text)
    quoted_terms = [item.strip() for pair in quoted for item in pair if item.strip()]
    if quoted_terms:
        return quoted_terms[:5]

    normalized = _normalize_text(text)
    if "," in normalized:
        terms = [part.strip() for part in normalized.split(",") if part.strip()]
    else:
        terms = re.findall(r"[a-z][a-z0-9_-]{3,}", normalized)
    clean_terms: list[str] = []
    for term in terms:
        if term in _STOPWORDS or term.isdigit():
            continue
        if term not in clean_terms:
            clean_terms.append(term)
    return clean_terms[:6]


def _detect_intent(text: str, state: ConversationState) -> Intent:
    normalized = _normalize_text(text)
    parameters = {
        **_extract_date_range(text),
    }
    nit = _extract_nit(text) or state.context.get("nit")
    company = _extract_company(text) or state.context.get("company")
    terms = _extract_terms(text) or state.context.get("terms") or []
    if nit:
        parameters["nit"] = nit
    if company:
        parameters["company"] = company
    if terms:
        parameters["terms"] = terms

    if any(keyword in normalized for keyword in _GREETING_KEYWORDS):
        return Intent(intent_type=IntentType.GREETING, confidence=0.98, parameters=parameters)

    if any(keyword in normalized for keyword in _HELP_KEYWORDS):
        return Intent(intent_type=IntentType.HELP, confidence=0.95, parameters=parameters)

    if "trendmap" in normalized or "trend mapping" in normalized or "mapa de tendencias" in normalized:
        return Intent(intent_type=IntentType.TRENDMAP_LATEST, confidence=0.9, parameters=parameters)

    if "riskmap" in normalized or "risk mapping" in normalized or "mapa de riesgos" in normalized:
        return Intent(intent_type=IntentType.RISKMAP_LATEST, confidence=0.9, parameters=parameters)

    if (
        any(keyword in normalized for keyword in {"estado", "ejecucion", "ejecuciones", "topics", "documentos"})
        and any(keyword in normalized for keyword in {"vigilancia", "tech watch", "tech-watch"})
    ):
        return Intent(intent_type=IntentType.TECH_WATCH_STATUS, confidence=0.88, parameters=parameters)

    if any(keyword in normalized for keyword in _ARAS_HINTS) or nit or company:
        return Intent(intent_type=IntentType.ARAS_SEARCH, confidence=0.82, parameters=parameters)

    if any(keyword in normalized for keyword in _RISK_HINTS) or terms:
        return Intent(intent_type=IntentType.RISK_SEARCH, confidence=0.78, parameters=parameters)

    return Intent(intent_type=IntentType.UNKNOWN, confidence=0.25, parameters=parameters)


def _help_message() -> str:
    return (
        "Puedo ayudarte con cuatro capacidades: busquedas ARAS por empresa, emisor o NIT; "
        "busquedas de riesgos por terminos; lectura del ultimo Trend Mapping; lectura del ultimo "
        "Risk Mapping; y estado operativo de vigilancia tecnologica. "
        "Ejemplos: 'Busca Bancolombia en el ultimo mes', 'riesgos de ciberseguridad en junio de 2025', "
        "'muestrame el trendmap actual' o 'estado de tech watch'."
    )


def _format_search_response(label: str, result: dict) -> str:
    total = int(result.get("total_documents", 0))
    if total <= 0:
        return f"{label}: no encontre documentos para los parametros solicitados."

    rows = result.get("results") or []
    highlights: list[str] = []
    for row in rows[:3]:
        title = row.get("title") or "Sin titulo"
        category = row.get("category") or row.get("risk_type") or "sin etiqueta"
        severity = row.get("severity") or "n/a"
        score = row.get("relevance_score")
        suffix = f" [{category}, sev {severity}"
        if score is not None:
            suffix += f", score {score}"
        suffix += "]"
        highlights.append(f"{title}{suffix}")

    parts = [f"{label}: encontre {total} documento(s)."]
    if highlights:
        parts.append("Top hallazgos: " + " | ".join(highlights))
    if result.get("excel_url"):
        parts.append(f"Export disponible en {result['excel_url']}.")
    return " ".join(parts)


def _format_snapshot_response(label: str, payload: dict) -> str:
    summary = payload.get("summary") or {}
    generated_at = payload.get("generated_at") or "sin fecha"
    clusters = payload.get("clusters") or []
    dominant = summary.get("dominant_topics") or summary.get("dominant_risks") or [
        cluster.get("label") for cluster in clusters[:3]
    ]
    dominant = [item for item in dominant if item]
    executive = summary.get("executive_summary") or payload.get("executive_summary")
    message = (
        f"{label}: snapshot generado en {generated_at}. "
        f"Documentos analizados: {summary.get('total_documents', 0)}. "
        f"Clusters: {summary.get('total_clusters', len(clusters))}."
    )
    if dominant:
        message += f" Dominantes: {', '.join(dominant[:3])}."
    if executive:
        message += f" Resumen: {executive}"
    return message


def _format_tech_watch_status(jobs: list[dict], executions: list[dict]) -> str:
    latest_execution = executions[0] if executions else None
    latest_job = next((job for job in jobs if job.get("job_group") == "tech_watch"), None)
    parts = ["Tech Watch:"]
    if latest_execution:
        parts.append(
            f"ultima ejecucion {latest_execution.get('run_key', 'n/a')} con estado "
            f"{latest_execution.get('status', 'unknown')}"
        )
    else:
        parts.append("sin ejecuciones registradas")
    if latest_job:
        parts.append(
            f"job {latest_job.get('job_name')} en estado {latest_job.get('last_status')} "
            f"(fin {latest_job.get('last_finished_at') or 'n/a'})"
        )
    return ". ".join(parts) + "."


def _build_container(mcp_server_url: str | None = None, backend_url: str | None = None) -> dict[str, object]:
    config = AgentConfig.load()
    if mcp_server_url:
        config.mcp_server_url = mcp_server_url
    if backend_url:
        config.backend_url = backend_url
    return create_container(config)


def _dispatch(intent: Intent, state: ConversationState, *, mcp_server_url: str | None, backend_url: str | None) -> str:
    container = _build_container(mcp_server_url=mcp_server_url, backend_url=backend_url)
    mcp = container["mcp_client"]
    backend = container["backend_client"]
    assert isinstance(mcp, MCPClient)
    assert isinstance(backend, BackendClient)

    if intent.intent_type == IntentType.GREETING:
        return "Hola. Soy el asistente de NewsRadar. " + _help_message()
    if intent.intent_type == IntentType.HELP:
        return _help_message()

    if intent.intent_type == IntentType.ARAS_SEARCH:
        if not intent.parameters.get("company") and not intent.parameters.get("nit"):
            return "Necesito al menos una empresa, emisor o NIT para ejecutar la busqueda ARAS."
        payload = {
            "company": intent.parameters.get("company"),
            "issuer": intent.parameters.get("company"),
            "nit": intent.parameters.get("nit"),
            "date_from": intent.parameters.get("date_from"),
            "date_to": intent.parameters.get("date_to"),
            "classifier": "rules",
        }
        try:
            result = mcp.call_tool("aras_search", payload)
            state.context.update({k: v for k, v in payload.items() if v})
            return _format_search_response("ARAS", result)
        except MCPToolError as exc:
            logger.warning("ARAS MCP tool failed: %s", exc)
            return "No pude completar la busqueda ARAS en este momento."

    if intent.intent_type == IntentType.RISK_SEARCH:
        terms = intent.parameters.get("terms") or []
        if not terms:
            return "Necesito al menos un termino de riesgo para ejecutar la busqueda."
        payload = {
            "terms": terms,
            "date_from": intent.parameters.get("date_from"),
            "date_to": intent.parameters.get("date_to"),
            "classifier": "rules",
        }
        try:
            result = mcp.call_tool("riesgos_search", payload)
            state.context.update({k: v for k, v in payload.items() if v})
            return _format_search_response("Riesgos", result)
        except MCPToolError as exc:
            logger.warning("Risk search MCP tool failed: %s", exc)
            return "No pude completar la busqueda de riesgos en este momento."

    if intent.intent_type == IntentType.TRENDMAP_LATEST:
        try:
            return _format_snapshot_response("Trend Mapping", backend.trendmap_latest())
        except BackendClientError as exc:
            logger.warning("Trendmap backend call failed: %s", exc)
            return "No pude leer el ultimo Trend Mapping en este momento."

    if intent.intent_type == IntentType.RISKMAP_LATEST:
        try:
            return _format_snapshot_response("Risk Mapping", backend.riskmap_latest())
        except BackendClientError as exc:
            logger.warning("Riskmap backend call failed: %s", exc)
            return "No pude leer el ultimo Risk Mapping en este momento."

    if intent.intent_type == IntentType.TECH_WATCH_STATUS:
        try:
            return _format_tech_watch_status(backend.jobs_status(), backend.tech_watch_executions())
        except BackendClientError as exc:
            logger.warning("Tech watch backend call failed: %s", exc)
            return "No pude consultar el estado operativo de Tech Watch."

    if intent.intent_type == IntentType.UNKNOWN:
        return _help_message()

    return "Necesito mas contexto para responder esa solicitud."


def handle_message(
    user_message: str,
    conversation_id: str | None = None,
    *,
    mcp_server_url: str | None = None,
    backend_url: str | None = None,
) -> dict:
    state = _get_or_create_conversation(conversation_id)
    state.messages.append(Message(role=Role.USER, content=user_message))
    state.turn_count += 1

    intent = _detect_intent(user_message, state)
    state.current_intent = intent.model_dump(mode="json")

    try:
        reply = _dispatch(intent, state, mcp_server_url=mcp_server_url, backend_url=backend_url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent error processing message")
        reply = f"Ocurrio un error al procesar la solicitud: {exc}"

    state.messages.append(
        Message(
            role=Role.AGENT,
            content=reply,
            metadata={"intent": intent.intent_type.value, "parameters": intent.parameters},
        )
    )
    return {"message": reply, "conversation_id": state.conversation_id, "intent": intent.intent_type.value}


def run_standalone() -> None:
    print("NewsRadar AI Agent - escribe 'exit' para salir")
    cid = str(uuid4())
    while True:
        try:
            user_input = input("Tu: ")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() in {"exit", "quit", "salir"}:
            break
        result = handle_message(user_input, conversation_id=cid)
        print(f"Agente: {result['message']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_standalone()
