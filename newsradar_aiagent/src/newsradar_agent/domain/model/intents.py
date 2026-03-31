"""Intent definitions for the NewsRadar conversational agent."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Supported user intents for the agent layer."""

    ARAS_SEARCH = "aras_search"
    RISK_SEARCH = "risk_search"
    TRENDMAP_LATEST = "trendmap_latest"
    RISKMAP_LATEST = "riskmap_latest"
    TECH_WATCH_STATUS = "tech_watch_status"
    HELP = "help"
    CLARIFICATION = "clarification"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class Intent(BaseModel):
    """Detected intent plus extracted parameters."""

    intent_type: IntentType = IntentType.UNKNOWN
    confidence: float = 0.0
    parameters: dict = Field(default_factory=dict)
