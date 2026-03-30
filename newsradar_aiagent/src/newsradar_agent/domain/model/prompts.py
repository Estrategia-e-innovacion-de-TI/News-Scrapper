"""Prompt templates for the AI Agent.

Templates used to construct LLM prompts for intent detection,
parameter extraction, and response generation.
"""
from __future__ import annotations

from pydantic import BaseModel


class PromptTemplate(BaseModel):
    """A prompt template with placeholder substitution.

    Attributes
    ----------
    name : str
        Template identifier.
    system_prompt : str
        System-level instructions for the LLM.
    user_template : str
        User message template with {placeholders}.
    """

    name: str
    system_prompt: str = ""
    user_template: str = ""

    def render(self, **kwargs: str) -> str:
        """Render the user template with the given parameters.

        Parameters
        ----------
        **kwargs : str
            Values to substitute into {placeholders}.

        Returns
        -------
        str
            Rendered prompt string.
        """
        # TODO: Implement template rendering with validation
        return self.user_template.format(**kwargs)


# -- Default prompt templates ------------------------------------------------

INTENT_DETECTION_PROMPT = PromptTemplate(
    name="intent_detection",
    system_prompt=(
        "You are an intent classifier for a news risk analysis system. "
        "Classify the user message into one of: aras_search, riesgos_search, "
        "clarification, greeting, unknown. Extract relevant parameters."
    ),
    user_template=(
        "Classify the following user message and extract parameters:\n\n"
        "Message: {user_message}\n\n"
        "Respond in JSON: {{\"intent\": \"...\", \"confidence\": 0.0, "
        "\"parameters\": {{...}}}}"
    ),
)

ARAS_RESPONSE_PROMPT = PromptTemplate(
    name="aras_response",
    system_prompt=(
        "You are a risk analyst assistant. Summarize ARAS search results "
        "for the user in a clear, concise manner. Highlight key findings, "
        "severity levels, and evidence."
    ),
    user_template=(
        "The user asked about: {query}\n\n"
        "Search results:\n{results}\n\n"
        "Provide a concise summary of the findings."
    ),
)

RIESGOS_RESPONSE_PROMPT = PromptTemplate(
    name="riesgos_response",
    system_prompt=(
        "You are an emerging risks analyst assistant. Summarize Riesgos "
        "Emergentes search results for the user. Highlight risk types, "
        "materialized events, and severity."
    ),
    user_template=(
        "The user searched for emerging risks with terms: {terms}\n\n"
        "Search results:\n{results}\n\n"
        "Provide a concise summary of the findings."
    ),
)
