"""Classifier adapters — RulesClassifier and LLMClassifier.

RulesClassifier: keyword-based classification without external API calls.
LLMClassifier: Amazon Bedrock (Claude Haiku) classification with fallback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClassifyResult:
    """Result of document classification."""
    label: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class RulesClassifier:
    """Keyword-based document classifier.

    Classifies documents using keyword matching against predefined
    term dictionaries per category. No external API calls.

    Implements: ClassifierService protocol.
    """

    def classify(
        self,
        text: str,
        title: str,
        query_type: str,
        categories: list[str] | None = None,
    ) -> ClassifyResult:
        """Classify a document by keyword matching.

        TODO: Port implementation from extractor/capabilities/classify.py
        """
        raise NotImplementedError("TODO: port RulesClassifier from extractor")


class LLMClassifier:
    """Amazon Bedrock LLM-based document classifier.

    Sends title + text[:3000] to Bedrock (Claude Haiku by default).
    Falls back to RulesClassifier on error/timeout.

    Implements: ClassifierService protocol.
    """

    def __init__(
        self,
        *,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        fallback: RulesClassifier | None = None,
    ) -> None:
        self._model_id = model_id
        self._fallback = fallback or RulesClassifier()

    def classify(
        self,
        text: str,
        title: str,
        query_type: str,
        categories: list[str] | None = None,
    ) -> ClassifyResult:
        """Classify a document via Amazon Bedrock.

        TODO: Port implementation from extractor/capabilities/classify.py
        """
        raise NotImplementedError("TODO: port LLMClassifier from extractor")
