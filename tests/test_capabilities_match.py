"""Tests for capabilities/match.py and capabilities registry."""
import pytest

from extractor.capabilities.match import match_terms_metadata_only, normalize_text
from extractor.capabilities.registry import CAPABILITY_REGISTRY, get_capability, list_capabilities


class TestMatchTermsMetadataOnly:
    def test_basic_match(self):
        result = match_terms_metadata_only(
            title="Bancolombia reports Q4 earnings",
            snippet="",
            terms=["bancolombia"],
        )
        assert result["score"] > 0
        assert "bancolombia" in result["matched_terms"]

    def test_no_match(self):
        result = match_terms_metadata_only(
            title="Weather forecast",
            snippet="Sunny skies",
            terms=["bancolombia"],
        )
        assert result["score"] == 0.0
        assert result["matched_terms"] == []

    def test_multiple_terms(self):
        result = match_terms_metadata_only(
            title="Fraude detectado en Bancolombia",
            snippet="",
            terms=["fraude", "bancolombia"],
        )
        assert len(result["matched_terms"]) == 2
        assert result["score"] > 0

    def test_accent_insensitive(self):
        result = match_terms_metadata_only(
            title="Investigación de fraude electrónico",
            snippet="",
            terms=["fraude electronico"],
        )
        assert result["score"] > 0

    def test_empty_inputs(self):
        result = match_terms_metadata_only("", "", [])
        assert result["score"] == 0.0
        assert result["matched_terms"] == []


class TestNormalizeText:
    def test_lowercase(self):
        assert "hello" in normalize_text("HELLO")

    def test_accent_removal(self):
        assert "electronico" in normalize_text("electrónico")

    def test_empty(self):
        assert normalize_text("") == ""


class TestCapabilityRegistry:
    def test_match_capability_registered(self):
        cap = get_capability("match_terms")
        assert cap is not None
        assert cap.name == "match_terms"
        assert callable(cap.callable)

    def test_list_capabilities(self):
        caps = list_capabilities()
        names = [c.name for c in caps]
        assert "match_terms" in names
        assert "rank_items" in names
        assert "classify_document" in names

    def test_capability_contract(self):
        cap = get_capability("match_terms")
        assert "title" in cap.inputs_schema
        assert "score" in cap.outputs_schema

    def test_capability_callable(self):
        cap = get_capability("match_terms")
        result = cap.callable("Test fraude", "", ["fraude"])
        assert result["score"] > 0
