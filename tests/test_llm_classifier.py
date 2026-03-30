"""Unit tests for LLMClassifier in extractor/capabilities/llm_classify.py.

boto3 is NOT required in the test environment — all Bedrock calls are mocked.
"""
from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from extractor.capabilities.classify import ClassifyResult, RulesClassifier
from extractor.capabilities.llm_classify import (
    DEFAULT_MODEL_ID,
    LLMClassifier,
    _build_prompt,
    _MAX_TEXT_CHARS,
)
from extractor.enums import get_valid_categories


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bedrock_response(data: dict) -> dict:
    """Build a mock Bedrock invoke_model response."""
    body_bytes = json.dumps(
        {"content": [{"text": json.dumps(data)}]}
    ).encode()
    mock_body = MagicMock()
    mock_body.read.return_value = body_bytes
    return {"body": mock_body}


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------

class TestFallbackOnError:
    """LLMClassifier must fall back to RulesClassifier on any Bedrock error."""

    def test_fallback_on_client_creation_error(self):
        """If boto3 import or client creation fails, fallback kicks in."""
        clf = LLMClassifier()
        # Force _get_client to raise
        clf._get_client = MagicMock(side_effect=RuntimeError("no boto3"))

        result = clf.classify(
            text="Investigación por lavado de activos",
            title="Lavado",
            query_type="aras",
        )
        # Should get a valid result from RulesClassifier
        assert isinstance(result, ClassifyResult)
        assert result.label == "lavado_activos"
        assert result.confidence > 0.0

    def test_fallback_on_invoke_model_error(self):
        """If invoke_model raises, fallback kicks in."""
        clf = LLMClassifier()
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = Exception("Bedrock timeout")
        clf._client = mock_client

        result = clf.classify(
            text="Ataque de ransomware a empresa",
            title="Ciberataque",
            query_type="riesgos",
        )
        assert isinstance(result, ClassifyResult)
        assert result.label == "cibernetico"
        assert "events" in result.metadata

    def test_fallback_on_malformed_json_response(self):
        """If Bedrock returns non-JSON, fallback kicks in."""
        clf = LLMClassifier()
        mock_client = MagicMock()
        # Return invalid JSON in the content block
        bad_body = json.dumps(
            {"content": [{"text": "this is not json"}]}
        ).encode()
        mock_resp_body = MagicMock()
        mock_resp_body.read.return_value = bad_body
        mock_client.invoke_model.return_value = {"body": mock_resp_body}
        clf._client = mock_client

        result = clf.classify(
            text="Fraude financiero detectado",
            title="Fraude",
            query_type="aras",
        )
        assert isinstance(result, ClassifyResult)
        assert result.label == "fraude"

    def test_fallback_logs_warning(self, caplog):
        """Fallback event is logged at WARNING level."""
        clf = LLMClassifier()
        clf._get_client = MagicMock(side_effect=RuntimeError("boom"))

        with caplog.at_level(logging.WARNING):
            clf.classify(text="test", title="", query_type="aras")

        assert any(
            "falling back to RulesClassifier" in rec.message
            for rec in caplog.records
        )

    def test_fallback_on_empty_content(self):
        """If Bedrock returns empty content blocks, fallback kicks in."""
        clf = LLMClassifier()
        mock_client = MagicMock()
        empty_body = json.dumps({"content": []}).encode()
        mock_resp_body = MagicMock()
        mock_resp_body.read.return_value = empty_body
        mock_client.invoke_model.return_value = {"body": mock_resp_body}
        clf._client = mock_client

        result = clf.classify(
            text="Derrame de petróleo",
            title="Derrame",
            query_type="aras",
        )
        assert isinstance(result, ClassifyResult)
        # RulesClassifier should handle this
        assert result.label in get_valid_categories("aras")


# ---------------------------------------------------------------------------
# Successful Bedrock response
# ---------------------------------------------------------------------------

class TestSuccessfulClassification:
    """When Bedrock returns a valid response, LLMClassifier parses it."""

    def test_aras_classification(self):
        clf = LLMClassifier()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = _make_bedrock_response(
            {
                "label": "corrupcion",
                "confidence": 0.85,
                "reason": "Article discusses bribery",
                "matched_keywords": ["soborno", "cohecho"],
            }
        )
        clf._client = mock_client

        result = clf.classify(
            text="Caso de soborno y cohecho",
            title="Corrupción",
            query_type="aras",
        )
        assert result.label == "corrupcion"
        assert result.confidence == 0.85
        assert result.metadata["reason"] == "Article discusses bribery"
        assert result.metadata["matched_keywords"] == ["soborno", "cohecho"]

    def test_riesgos_classification_with_events(self):
        clf = LLMClassifier()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = _make_bedrock_response(
            {
                "label": "cibernetico",
                "confidence": 0.9,
                "reason": "Ransomware attack detected",
                "matched_keywords": ["ransomware"],
                "events": ["breach"],
            }
        )
        clf._client = mock_client

        result = clf.classify(
            text="Ransomware breach at company",
            title="Cyber",
            query_type="riesgos",
        )
        assert result.label == "cibernetico"
        assert result.metadata["events"] == ["breach"]

    def test_invalid_label_falls_to_otro(self):
        """If LLM returns a label not in valid categories, use 'otro'."""
        clf = LLMClassifier()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = _make_bedrock_response(
            {
                "label": "nonexistent_category",
                "confidence": 0.7,
                "reason": "test",
                "matched_keywords": [],
            }
        )
        clf._client = mock_client

        result = clf.classify(text="test", title="", query_type="aras")
        assert result.label == "otro"
        assert result.confidence == 0.0

    def test_confidence_clamped(self):
        """Confidence is clamped to [0.0, 1.0]."""
        clf = LLMClassifier()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = _make_bedrock_response(
            {
                "label": "fraude",
                "confidence": 1.5,
                "reason": "test",
                "matched_keywords": [],
            }
        )
        clf._client = mock_client

        result = clf.classify(text="fraude", title="", query_type="aras")
        assert result.confidence == 1.0


# ---------------------------------------------------------------------------
# Text truncation
# ---------------------------------------------------------------------------

class TestTextTruncation:
    """Verify that text sent to Bedrock is truncated to 3000 chars."""

    def test_long_text_truncated_in_prompt(self):
        # Use a unique marker that won't appear in category names
        marker = "ZQZQ"
        long_text = marker * 2000  # 8000 chars
        prompt = _build_prompt("Title", long_text, "aras", None)
        # Only 3000 chars of text are included → 3000/4 = 750 full markers
        assert prompt.count(marker) == _MAX_TEXT_CHARS // len(marker)

    def test_short_text_not_truncated(self):
        short_text = "hello world"
        prompt = _build_prompt("Title", short_text, "aras", None)
        assert "hello world" in prompt

    def test_invoke_sends_truncated_text(self):
        """End-to-end: invoke_model receives truncated text."""
        clf = LLMClassifier()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = _make_bedrock_response(
            {
                "label": "otro",
                "confidence": 0.0,
                "reason": "no match",
                "matched_keywords": [],
            }
        )
        clf._client = mock_client

        marker = "ZQZQ"
        long_text = marker * 2000  # 8000 chars
        clf.classify(text=long_text, title="T", query_type="aras")

        # Check the body sent to invoke_model
        call_kwargs = mock_client.invoke_model.call_args
        sent_body = json.loads(call_kwargs.kwargs.get("body") or call_kwargs[1].get("body"))
        user_msg = sent_body["messages"][0]["content"]
        # Only 3000/4 = 750 full markers should appear in the text portion
        assert user_msg.count(marker) == _MAX_TEXT_CHARS // len(marker)


# ---------------------------------------------------------------------------
# Constructor defaults
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_default_model_id(self):
        clf = LLMClassifier()
        assert clf.model_id == DEFAULT_MODEL_ID

    def test_custom_model_id(self):
        clf = LLMClassifier(model_id="anthropic.claude-3-sonnet-20240229-v1:0")
        assert clf.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"

    def test_default_region(self):
        clf = LLMClassifier()
        assert clf.region == "us-east-1"

    def test_custom_region(self):
        clf = LLMClassifier(region="eu-west-1")
        assert clf.region == "eu-west-1"
