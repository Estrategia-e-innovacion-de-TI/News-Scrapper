"""Intent definitions for the AI Agent.

Intents represent the user's goal detected from their message.
The agent uses intents to route to the appropriate MCP tool
(ARAS search, Riesgos search, etc.).
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Supported intent types for the conversational agent."""

    ARAS_SEARCH = "aras_search"
    """User wants to search ARAS news for a company/NIT."""

    RIESGOS_SEARCH = "riesgos_search"
    """User wants to search Riesgos Emergentes news by terms/preset."""

    CLARIFICATION = "clarification"
    """Agent needs more information from the user."""

    GREETING = "greeting"
    """User greeting or small talk."""

    UNKNOWN = "unknown"
    """Intent could not be determined."""


class Intent(BaseModel):
    """Detected intent from a user message.

    Attributes
    ----------
    intent_type : IntentType
        The classified intent.
    confidence : float
        Confidence score for the intent detection (0.0–1.0).
    parameters : dict
        Extracted parameters (e.g., company name, NIT, terms, date range).
    """

    intent_type: IntentType = IntentType.UNKNOWN
    confidence: float = 0.0
    parameters: dict = Field(default_factory=dict)
