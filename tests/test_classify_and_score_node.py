"""Unit tests for the classify_and_score pipeline node."""
from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import patch

from extractor.graph import classify_and_score_node
from extractor.state import Document, GraphState, SourceMetrics


def _make_doc(
    source_id: str = "src1",
    text: str = "Empresa investigada por lavado de activos y fraude financiero con multa millonaria",
    title: str = "Noticia de prueba",
    query_type: str = "aras",
    adhoc: bool = True,
) -> Document:
    return Document(
        run_id="test-run",
        source_id=source_id,
        pipeline_class="news",
        focus=["aras_news"] if query_type == "aras" else ["riesgos_news"],
        title=title,
        url="https://example.com/article",
        fetched_at=datetime.utcnow().isoformat(),
        text=text,
        excerpt=text[:100],
        raw_len=len(text),
        text_len=len(text),
        hash="abc123",
        fetch_method="http",
        source_url="https://example.com",
        origin="adhoc_query" if adhoc else "catalog",
        query_type=query_type,
    )


def _make_state(
    documents: list[Document] | None = None,
    adhoc: bool = True,
    focus: str = "aras_news",
    classifier_mode: str = "rules",
    source_ids: list[str] | None = None,
) -> GraphState:
    if documents is None:
        documents = [_make_doc()]
    sids = source_ids or list({d.source_id for d in documents})
    sm = {sid: SourceMetrics(source_id=sid) for sid in sids}
    return GraphState(
        documents=documents,
        adhoc=adhoc,
        focus=focus,
        classifier_mode=classifier_mode,
        source_metrics=sm,
    )


class TestAdhocClassification:
    """Tests for adhoc mode: classify + severity + evidence."""

    @pytest.mark.asyncio
    async def test_adhoc_sets_category(self):
        state = _make_state()
        result = await classify_and_score_node(state)
        docs = result["documents"]
        assert len(docs) == 1
        assert docs[0].category is not None
        assert docs[0].category != "error"

    @pytest.mark.asyncio
    async def test_adhoc_sets_severity(self):
        state = _make_state()
        result = await classify_and_score_node(state)
        doc = result["documents"][0]
        assert doc.severity in ("H", "M", "L")
        assert doc.severity_confidence is not None
        assert 0.0 <= doc.severity_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_adhoc_riesgos_sets_risk_type(self):
        doc = _make_doc(
            query_type="riesgos",
            text="Ciberataque ransomware afecta sistemas bancarios con breach de datos",
        )
        state = _make_state(documents=[doc], focus="riesgos_news")
        result = await classify_and_score_node(state)
        assert result["documents"][0].risk_type is not None

    @pytest.mark.asyncio
    async def test_adhoc_updates_source_metrics_ok(self):
        state = _make_state()
        result = await classify_and_score_node(state)
        sm = result["source_metrics"]["src1"]
        assert sm.classified_ok == 1
        assert sm.classified_error == 0

    @pytest.mark.asyncio
    async def test_adhoc_severity_metrics(self):
        state = _make_state()
        result = await classify_and_score_node(state)
        sm = result["source_metrics"]["src1"]
        total_sev = sm.severity_h + sm.severity_m + sm.severity_l
        assert total_sev == 1


class TestVigilanciaScoring:
    """Tests for vigilancia mode: relevance score."""

    @pytest.mark.asyncio
    async def test_vigilancia_sets_relevance_score(self):
        doc = _make_doc(adhoc=False, query_type=None)
        doc.query_type = None
        state = _make_state(
            documents=[doc],
            adhoc=False,
            focus="vigilancia_news",
        )
        result = await classify_and_score_node(state)
        assert result["documents"][0].relevance_score is not None
        assert 0 <= result["documents"][0].relevance_score <= 100

    @pytest.mark.asyncio
    async def test_vigilancia_updates_metrics(self):
        doc = _make_doc(adhoc=False)
        state = _make_state(
            documents=[doc],
            adhoc=False,
            focus="vigilancia_news",
        )
        result = await classify_and_score_node(state)
        sm = result["source_metrics"]["src1"]
        assert sm.classified_ok == 1


class TestErrorHandling:
    """Tests for per-document error resilience."""

    @pytest.mark.asyncio
    async def test_error_marks_category_error(self):
        doc = _make_doc()
        state = _make_state(documents=[doc])
        # Patch the classifier to raise an exception
        with patch(
            "extractor.graph.RulesClassifier.classify",
            side_effect=RuntimeError("boom"),
        ):
            result = await classify_and_score_node(state)
        assert result["documents"][0].category == "error"
        assert result["documents"][0].severity is None

    @pytest.mark.asyncio
    async def test_error_increments_classified_error(self):
        doc = _make_doc()
        state = _make_state(documents=[doc])
        with patch(
            "extractor.graph.RulesClassifier.classify",
            side_effect=RuntimeError("boom"),
        ):
            result = await classify_and_score_node(state)
        sm = result["source_metrics"]["src1"]
        assert sm.classified_error == 1
        assert sm.classified_ok == 0

    @pytest.mark.asyncio
    async def test_partial_error_continues_batch(self):
        good_doc = _make_doc(source_id="src1")
        bad_doc = _make_doc(source_id="src2")
        state = _make_state(
            documents=[good_doc, bad_doc],
            source_ids=["src1", "src2"],
        )
        call_count = 0
        original_classify = RulesClassifier.classify

        def flaky_classify(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("second doc fails")
            return original_classify(self, *args, **kwargs)

        with patch(
            "extractor.graph.RulesClassifier.classify",
            flaky_classify,
        ):
            result = await classify_and_score_node(state)

        docs = result["documents"]
        assert docs[0].category != "error"
        assert docs[1].category == "error"
        assert result["source_metrics"]["src1"].classified_ok == 1
        assert result["source_metrics"]["src2"].classified_error == 1


class TestNoOpModes:
    """Tests for modes where classify_and_score does nothing."""

    @pytest.mark.asyncio
    async def test_empty_documents_returns_empty(self):
        state = _make_state(documents=[])
        result = await classify_and_score_node(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_non_adhoc_non_vigilancia_returns_empty(self):
        doc = _make_doc(adhoc=False)
        state = _make_state(
            documents=[doc],
            adhoc=False,
            focus="some_other_focus",
        )
        result = await classify_and_score_node(state)
        assert result == {}


# Need the import for the patch target
from extractor.capabilities.classify import RulesClassifier
