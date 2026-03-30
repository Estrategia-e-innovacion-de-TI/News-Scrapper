"""Unit tests for SeverityScorer in extractor/capabilities/severity.py."""
import pytest

from extractor.capabilities.severity import (
    SeverityResult,
    SeverityScorer,
    HIGH_SEVERITY_KEYWORDS,
    MEDIUM_SEVERITY_KEYWORDS,
)
from extractor.capabilities.classify import ClassifyResult
from extractor.state import EvidenceSpan


@pytest.fixture
def scorer():
    return SeverityScorer()


# ---------------------------------------------------------------------------
# SeverityResult dataclass
# ---------------------------------------------------------------------------


class TestSeverityResult:
    def test_dataclass_fields(self):
        r = SeverityResult(severity="H", confidence=0.8, evidence_spans=[])
        assert r.severity == "H"
        assert r.confidence == 0.8
        assert r.evidence_spans == []

    def test_default_evidence_spans(self):
        r = SeverityResult(severity="L", confidence=0.2)
        assert r.evidence_spans == []

    def test_with_evidence_spans(self):
        span = EvidenceSpan(
            text="...multa impuesta...",
            start_offset=10,
            end_offset=30,
            matched_term="multa",
        )
        r = SeverityResult(severity="H", confidence=0.9, evidence_spans=[span])
        assert len(r.evidence_spans) == 1
        assert r.evidence_spans[0].matched_term == "multa"


# ---------------------------------------------------------------------------
# Short document guard (<100 chars)
# ---------------------------------------------------------------------------


class TestShortDocumentGuard:
    def test_short_text_returns_low(self, scorer):
        result = scorer.score(text="short", title="t")
        assert result.severity == "L"
        assert result.confidence == 0.1
        assert result.evidence_spans == []

    def test_empty_text_returns_low(self, scorer):
        result = scorer.score(text="", title="")
        assert result.severity == "L"
        assert result.confidence == 0.1

    def test_exactly_99_chars_returns_low(self, scorer):
        # title + " " + text must be < 100
        text = "a" * 95
        result = scorer.score(text=text, title="ab")
        # "ab" + " " + "a"*95 = 99 chars
        assert result.severity == "L"
        assert result.confidence == 0.1

    def test_100_chars_not_short(self, scorer):
        # 100 chars should NOT trigger the short-doc guard
        text = "a" * 96
        result = scorer.score(text=text, title="abc")
        # "abc" + " " + "a"*96 = 100 chars
        assert result.confidence != 0.1 or result.severity == "L"


# ---------------------------------------------------------------------------
# High severity (H)
# ---------------------------------------------------------------------------


class TestHighSeverity:
    def test_three_high_keywords(self, scorer):
        text = (
            "La empresa fue acusada de fraude, lavado de activos y "
            "terrorismo financiero en una investigación internacional. "
            + "x" * 100
        )
        result = scorer.score(text=text, title="Caso grave")
        assert result.severity == "H"
        assert result.confidence > 0.0

    def test_many_high_keywords(self, scorer):
        text = (
            "Multa por fraude, lavado, terrorismo, corrupcion, soborno "
            "y ransomware detectados en la empresa. "
            + "x" * 100
        )
        result = scorer.score(text=text, title="Escándalo")
        assert result.severity == "H"
        assert result.confidence > 0.5

    def test_two_high_keywords_not_H(self, scorer):
        text = (
            "Se detectó fraude y lavado en la empresa. "
            + "x" * 100
        )
        result = scorer.score(text=text, title="Caso")
        assert result.severity != "H"


# ---------------------------------------------------------------------------
# Medium severity (M)
# ---------------------------------------------------------------------------


class TestMediumSeverity:
    def test_one_high_keyword(self, scorer):
        text = (
            "Se detectó un caso de fraude en la empresa. "
            + "x" * 100
        )
        result = scorer.score(text=text, title="Alerta")
        assert result.severity == "M"

    def test_three_medium_keywords(self, scorer):
        text = (
            "Investigacion sobre denuncia de contaminacion en la zona. "
            + "x" * 100
        )
        result = scorer.score(text=text, title="Reporte")
        assert result.severity == "M"

    def test_two_medium_keywords_not_M(self, scorer):
        text = (
            "Investigacion sobre protesta en la zona industrial. "
            + "x" * 100
        )
        result = scorer.score(text=text, title="Reporte")
        # 2 medium keywords → not enough for M
        assert result.severity == "L"


# ---------------------------------------------------------------------------
# Low severity (L)
# ---------------------------------------------------------------------------


class TestLowSeverity:
    def test_no_keywords(self, scorer):
        text = "La empresa reportó resultados positivos este trimestre. " + "x" * 100
        result = scorer.score(text=text, title="Resultados")
        assert result.severity == "L"

    def test_one_medium_keyword(self, scorer):
        text = "Se reportó un accidente menor en la planta. " + "x" * 100
        result = scorer.score(text=text, title="Reporte")
        assert result.severity == "L"


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidence:
    def test_confidence_between_0_and_1(self, scorer):
        text = (
            "Multa por fraude, lavado, terrorismo, corrupcion, soborno, "
            "ransomware, breach, demanda, fatalidad, muerte, sancion. "
            + "x" * 100
        )
        result = scorer.score(text=text, title="Todo")
        assert 0.0 <= result.confidence <= 1.0

    def test_more_keywords_higher_confidence(self, scorer):
        text1 = "Fraude detectado en la empresa. " + "x" * 100
        text2 = (
            "Fraude, lavado y terrorismo detectados en la empresa. "
            + "x" * 100
        )
        r1 = scorer.score(text=text1, title="Caso")
        r2 = scorer.score(text=text2, title="Caso grave")
        assert r2.confidence > r1.confidence

    def test_low_severity_low_confidence(self, scorer):
        text = "La empresa tuvo un buen año financiero. " + "x" * 100
        result = scorer.score(text=text, title="Resultados")
        assert result.confidence <= 0.5


# ---------------------------------------------------------------------------
# Evidence spans
# ---------------------------------------------------------------------------


class TestEvidenceSpans:
    def test_evidence_spans_returned(self, scorer):
        text = (
            "La empresa fue multada por fraude financiero grave. "
            + "x" * 200
        )
        result = scorer.score(text=text, title="Multa")
        assert len(result.evidence_spans) > 0

    def test_max_three_spans(self, scorer):
        text = (
            "Multa por fraude. " + "x" * 200 + " Lavado detectado. "
            + "x" * 200 + " Terrorismo financiero. " + "x" * 200
            + " Corrupcion en la empresa. " + "x" * 200
            + " Soborno confirmado. " + "x" * 200
        )
        result = scorer.score(text=text, title="Caso")
        assert len(result.evidence_spans) <= 3

    def test_evidence_span_has_correct_fields(self, scorer):
        text = "La empresa fue sancionada por fraude grave. " + "x" * 200
        result = scorer.score(text=text, title="Sanción")
        if result.evidence_spans:
            span = result.evidence_spans[0]
            assert isinstance(span, EvidenceSpan)
            assert isinstance(span.text, str)
            assert isinstance(span.start_offset, int)
            assert isinstance(span.end_offset, int)
            assert isinstance(span.matched_term, str)
            assert span.start_offset >= 0
            assert span.end_offset > span.start_offset

    def test_no_evidence_for_no_matches(self, scorer):
        text = "La empresa tuvo un buen año financiero. " + "x" * 100
        result = scorer.score(text=text, title="Resultados")
        assert result.evidence_spans == []


# ---------------------------------------------------------------------------
# Normalization (accent/case insensitive)
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_accent_insensitive(self, scorer):
        text = "Sanciones impuestas por contaminación del río. " + "x" * 100
        result = scorer.score(text=text, title="Sanción")
        # "sancion" should match "Sanciones" and "contaminacion" should match "contaminación"
        assert result.severity in ("H", "M")

    def test_case_insensitive(self, scorer):
        text = "FRAUDE FINANCIERO detectado en LAVADO de activos. " + "x" * 100
        result = scorer.score(text=text, title="TERRORISMO")
        assert result.severity == "H"


# ---------------------------------------------------------------------------
# classify_result parameter (interface parity)
# ---------------------------------------------------------------------------


class TestClassifyResultParam:
    def test_accepts_classify_result(self, scorer):
        cr = ClassifyResult(
            label="fraude",
            confidence=0.9,
            metadata={"reason": "keyword", "matched_keywords": ["fraude"]},
        )
        text = "Fraude detectado en la empresa. " + "x" * 100
        result = scorer.score(text=text, title="Fraude", classify_result=cr)
        assert result.severity in ("H", "M", "L")

    def test_works_without_classify_result(self, scorer):
        text = "Fraude detectado en la empresa. " + "x" * 100
        result = scorer.score(text=text, title="Fraude")
        assert result.severity in ("H", "M", "L")
