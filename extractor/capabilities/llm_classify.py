"""Capability: LLM-based document classification via Amazon Bedrock.

LLMClassifier sends ``title + text[:3000]`` to Amazon Bedrock (Claude Haiku
by default, configurable model) and parses the structured JSON response.
Falls back to RulesClassifier on any error (timeout, parse error, API error).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from .classify import ClassifyResult, RulesClassifier
from ..enums import get_valid_categories

logger = logging.getLogger(__name__)

# Max characters of document text to send to the LLM
_MAX_TEXT_CHARS = 3000

# Default Bedrock model ID
DEFAULT_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"


def _build_prompt(title: str, text: str, query_type: str, categories: list[str] | None) -> str:
    """Build the classification prompt for the LLM."""
    truncated_text = text[:_MAX_TEXT_CHARS]

    valid_cats = get_valid_categories(query_type)
    if categories:
        valid_cats = valid_cats & set(categories)
    cats_str = ", ".join(sorted(valid_cats))

    if query_type == "riesgos":
        events_instruction = (
            '\n- "events": list of materialized events detected from '
            "{multa, perdida, outage, breach, near_miss, sancion, demanda, "
            "suspension_actividades, suspension_licencia, fatalidad, bloqueo, "
            "derrame, incendio, inundacion, denuncia, conflicto_laboral}. "
            "Empty list if none detected."
        )
    else:
        events_instruction = ""

    prompt = (
        f"Classify the following news article into exactly one category.\n\n"
        f"Valid categories: [{cats_str}]\n\n"
        f"Title: {title}\n"
        f"Text: {truncated_text}\n\n"
        f"Respond ONLY with a JSON object containing:\n"
        f'- "label": exactly one category from the valid list above\n'
        f'- "confidence": float between 0.0 and 1.0\n'
        f'- "reason": brief explanation of why this category was chosen\n'
        f'- "matched_keywords": list of key terms that influenced the classification'
        f"{events_instruction}\n\n"
        f"If no category fits, use \"otro\" with confidence 0.0.\n"
        f"Return ONLY valid JSON, no markdown, no extra text."
    )
    return prompt


class LLMClassifier:
    """LLM-based document classifier using Amazon Bedrock.

    Sends ``title + text[:3000]`` to Bedrock and parses the structured JSON
    response.  Falls back to :class:`RulesClassifier` on any error.

    Parameters
    ----------
    model_id:
        Bedrock model identifier.  Defaults to Claude 3 Haiku.
    region:
        AWS region for the ``bedrock-runtime`` client.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        region: str = "us-east-1",
    ) -> None:
        self.model_id = model_id
        self.region = region
        self._fallback = RulesClassifier()
        self._client: Any = None  # lazy-init boto3 client

    # -- lazy client --------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazily create the ``bedrock-runtime`` boto3 client."""
        if self._client is None:
            try:
                import boto3  # type: ignore[import-untyped]

                self._client = boto3.client(
                    "bedrock-runtime",
                    region_name=self.region,
                    verify=False,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to create bedrock-runtime client: {exc}"
                ) from exc
        return self._client

    # -- public API ---------------------------------------------------------

    def classify(
        self,
        text: str,
        title: str = "",
        query_type: str = "aras",
        categories: list[str] | None = None,
    ) -> ClassifyResult:
        """Classify *text* (+ *title*) using Amazon Bedrock.

        On any error the method falls back to :class:`RulesClassifier` and
        logs a WARNING.
        """
        try:
            return self._classify_via_bedrock(text, title, query_type, categories)
        except Exception as exc:
            logger.warning(
                "LLMClassifier failed, falling back to RulesClassifier: %s",
                exc,
            )
            return self._fallback.classify(text, title, query_type, categories)

    # -- private helpers ----------------------------------------------------

    def _classify_via_bedrock(
        self,
        text: str,
        title: str,
        query_type: str,
        categories: list[str] | None,
    ) -> ClassifyResult:
        """Call Bedrock and parse the response."""
        client = self._get_client()
        prompt = _build_prompt(title, text, query_type, categories)

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
            }
        )

        response = client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        response_body = json.loads(response["body"].read())
        return self._parse_response(response_body, query_type)

    def _parse_response(
        self,
        response_body: dict[str, Any],
        query_type: str,
    ) -> ClassifyResult:
        """Extract classification from the Bedrock response JSON."""
        # Claude returns content as a list of blocks
        content_blocks = response_body.get("content", [])
        if not content_blocks:
            raise ValueError("Empty content in Bedrock response")

        raw_text = content_blocks[0].get("text", "")
        data = json.loads(raw_text)

        label = str(data.get("label", "otro"))
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        # Validate label against valid categories
        valid_cats = get_valid_categories(query_type)
        if label not in valid_cats:
            label = "otro"
            confidence = 0.0

        metadata: dict[str, Any] = {
            "reason": str(data.get("reason", "")),
            "matched_keywords": list(data.get("matched_keywords", [])),
        }

        if query_type == "riesgos":
            metadata["events"] = list(data.get("events", []))

        return ClassifyResult(
            label=label,
            confidence=confidence,
            metadata=metadata,
        )


__all__ = ["LLMClassifier", "DEFAULT_MODEL_ID"]
