"""Unit tests for RulesClassifier in extractor/capabilities/classify.py."""
import pytest

from extractor.capabilities.classify import (
    ClassifyResult,
    RulesClassifier,
    classify_document,
)
from extractor.capabilities.registry import get_capability
from extractor.enums import get_valid_categories


@pytest.fixture
def classifier():
    return RulesClassifier()


# ---------------------------------------------------------------------------
# ARAS classification
# ---------------------------------------------------------------------------

class TestARASClassification:
    def test_lavado_activos(self, classifier):
        result = classifier.classify(
            text="Investigación por lavado de activos en entidad financiera",
            title="Caso de lavado de dinero",
            query_type="aras",
        )
        assert result.label == "lavado_activos"
        assert result.confidence > 0.0
        assert "reason" in result.metadata
        assert "matched_keywords" in result.metadata
        assert len(result.metadata["matched_keywords"]) > 0

    def test_fraude(self, classifier):
        result = classifier.classify(
            text="Se detectó un esquema de fraude financiero y estafa",
            title="Fraude bancario",
            query_type="aras",
        )
        assert result.label == "fraude"
        assert result.confidence > 0.0

    def test_corrupcion(self, classifier):
        result = classifier.classify(
            text="Caso de soborno y cohecho en contrato público",
            title="Corrupción en licitación",
            query_type="aras",
        )
        assert result.label == "corrupcion"
        assert result.confidence > 0.0

    def test_no_match_returns_otro(self, classifier):
        result = classifier.classify(
            text="The weather is nice today in Bogota",
            title="Weather report",
            query_type="aras",
        )
        assert result.label == "otro"
        assert result.confidence == 0.0
        assert result.metadata["matched_keywords"] == []

    def test_label_in_valid_categories(self, classifier):
        valid = get_valid_categories("aras")
        result = classifier.classify(
            text="Derrame de petróleo en zona protegida",
            title="Derrame",
            query_type="aras",
        )
        assert result.label in valid

    def test_accent_insensitive(self, classifier):
        result = classifier.classify(
            text="Contaminación del río por vertido sin permiso",
            title="Contaminación",
            query_type="aras",
        )
        assert result.label == "contaminacion"
        assert result.confidence > 0.0

    def test_case_insensitive(self, classifier):
        result = classifier.classify(
            text="FRAUDE FINANCIERO detectado",
            title="FRAUDE",
            query_type="aras",
        )
        assert result.label == "fraude"

    def test_empty_text_returns_otro(self, classifier):
        result = classifier.classify(text="", title="", query_type="aras")
        assert result.label == "otro"
        assert result.confidence == 0.0

    def test_categories_filter(self, classifier):
        result = classifier.classify(
            text="Fraude y lavado de activos detectados",
            title="",
            query_type="aras",
            categories=["lavado_activos"],
        )
        assert result.label == "lavado_activos"


# ---------------------------------------------------------------------------
# Riesgos classification
# ---------------------------------------------------------------------------

class TestRiesgosClassification:
    def test_cibernetico(self, classifier):
        result = classifier.classify(
            text="Ataque de ransomware y phishing a empresa",
            title="Ciberataque",
            query_type="riesgos",
        )
        assert result.label == "cibernetico"
        assert result.confidence > 0.0
        assert "events" in result.metadata

    def test_operacional(self, classifier):
        result = classifier.classify(
            text="Falla sistémica causó interrupción del servicio",
            title="Outage",
            query_type="riesgos",
        )
        assert result.label == "operacional"
        assert result.confidence > 0.0

    def test_no_match_returns_otro(self, classifier):
        result = classifier.classify(
            text="Beautiful sunset over the mountains",
            title="Nature",
            query_type="riesgos",
        )
        assert result.label == "otro"
        assert result.confidence == 0.0
        assert result.metadata["events"] == []

    def test_label_in_valid_categories(self, classifier):
        valid = get_valid_categories("riesgos")
        result = classifier.classify(
            text="Conflicto laboral en planta industrial",
            title="Huelga",
            query_type="riesgos",
        )
        assert result.label in valid


# ---------------------------------------------------------------------------
# Materialized events detection
# ---------------------------------------------------------------------------

class TestMaterializedEvents:
    def test_detects_multa(self, classifier):
        result = classifier.classify(
            text="La empresa recibió una multa por incumplimiento",
            title="Sanción",
            query_type="riesgos",
        )
        assert "multa" in result.metadata["events"]

    def test_detects_multiple_events(self, classifier):
        result = classifier.classify(
            text="Derrame de petróleo causó incendio y multa millonaria",
            title="Desastre ambiental",
            query_type="riesgos",
        )
        events = result.metadata["events"]
        assert "derrame" in events
        assert "incendio" in events
        assert "multa" in events

    def test_no_events_when_none_present(self, classifier):
        result = classifier.classify(
            text="Inteligencia artificial avanza rápidamente",
            title="IA",
            query_type="riesgos",
        )
        assert result.metadata["events"] == []

    def test_events_only_for_riesgos(self, classifier):
        result = classifier.classify(
            text="Multa por derrame de petróleo",
            title="Sanción",
            query_type="aras",
        )
        assert "events" not in result.metadata


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidence:
    def test_more_matches_higher_confidence(self, classifier):
        r1 = classifier.classify(
            text="fraude",
            title="",
            query_type="aras",
        )
        r2 = classifier.classify(
            text="fraude estafa timo defraudacion falsificacion",
            title="Fraude financiero",
            query_type="aras",
        )
        assert r2.confidence > r1.confidence

    def test_confidence_between_0_and_1(self, classifier):
        result = classifier.classify(
            text="fraude estafa timo ponzi esquema piramidal falsificacion suplantacion defraudacion",
            title="Mega fraude",
            query_type="aras",
        )
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Module-level function & registry
# ---------------------------------------------------------------------------

class TestModuleFunction:
    def test_classify_document_function(self):
        result = classify_document(
            text="Lavado de activos detectado",
            title="LAFT",
            query_type="aras",
        )
        assert isinstance(result, ClassifyResult)
        assert result.label == "lavado_activos"

    def test_classify_document_riesgos(self):
        result = classify_document(
            text="Ransomware attack on bank",
            title="Cyber",
            query_type="riesgos",
        )
        assert isinstance(result, ClassifyResult)
        assert "events" in result.metadata


class TestRegistration:
    def test_capability_registered(self):
        cap = get_capability("classify_document")
        assert cap is not None
        assert cap.name == "classify_document"
        assert callable(cap.callable)

    def test_capability_callable(self):
        cap = get_capability("classify_document")
        result = cap.callable("fraude detectado", "Fraude", "aras")
        assert result.label == "fraude"
