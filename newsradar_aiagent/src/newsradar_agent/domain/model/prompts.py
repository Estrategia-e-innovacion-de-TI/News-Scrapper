"""Prompt templates used by the NewsRadar AI agent."""
from __future__ import annotations

import string

from pydantic import BaseModel


class PromptTemplate(BaseModel):
    """Prompt template with safe placeholder validation."""

    name: str
    system_prompt: str = ""
    user_template: str = ""

    def render(self, **kwargs: str) -> str:
        formatter = string.Formatter()
        required = {
            field_name
            for _, field_name, _, _ in formatter.parse(self.user_template)
            if field_name
        }
        missing = sorted(field for field in required if field not in kwargs)
        if missing:
            raise ValueError(f"Missing prompt placeholders for {self.name}: {', '.join(missing)}")
        return self.user_template.format(**kwargs)


INTENT_DETECTION_PROMPT = PromptTemplate(
    name="intent_detection",
    system_prompt=(
        "Classify the user message for the NewsRadar assistant. "
        "Allowed intents: aras_search, risk_search, trendmap_latest, "
        "riskmap_latest, tech_watch_status, help, greeting, clarification, unknown."
    ),
    user_template=(
        "Message: {user_message}\n"
        "Return JSON with keys intent, confidence and parameters."
    ),
)

SEARCH_RESPONSE_PROMPT = PromptTemplate(
    name="search_response",
    system_prompt=(
        "Summarize news search results for an analyst. Highlight the total, the most "
        "relevant documents and any severity or risk labels."
    ),
    user_template=(
        "Query: {query}\n"
        "Results: {results}\n"
        "Provide a concise operational summary."
    ),
)

SNAPSHOT_RESPONSE_PROMPT = PromptTemplate(
    name="snapshot_response",
    system_prompt=(
        "Summarize a persisted analytical snapshot for an executive audience. Focus on "
        "dominant themes, clusters and immediate implications."
    ),
    user_template=(
        "Snapshot type: {snapshot_type}\n"
        "Snapshot data: {snapshot}\n"
        "Provide a concise analytical summary."
    ),
)
