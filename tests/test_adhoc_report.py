"""Tests for adhoc_summary in run_report."""
import pytest

from extractor.report import generate_report
from extractor.state import GraphState


class TestAdhocReport:
    def test_adhoc_summary_present(self):
        state = GraphState(
            adhoc=True,
            focus="aras_news",
            company="Bancolombia",
            date_from="2026-01-01",
            date_to="2026-03-01",
            topk_per_source=5,
            max_candidates_total=50,
        )
        report = generate_report(state)
        assert "adhoc_summary" in report
        summary = report["adhoc_summary"]
        assert summary["query_type"] == "aras"
        assert summary["company"] == "Bancolombia"
        assert summary["date_from"] == "2026-01-01"
        assert summary["date_to"] == "2026-03-01"
        assert summary["topk_per_source"] == 5
        assert summary["max_candidates_total"] == 50

    def test_no_adhoc_summary_in_normal_mode(self):
        state = GraphState()
        report = generate_report(state)
        assert "adhoc_summary" not in report

    def test_params_include_adhoc_fields(self):
        state = GraphState(
            adhoc=True,
            focus="aras_news",
            company="X",
            date_from="2026-01-01",
            date_to="2026-03-01",
        )
        report = generate_report(state)
        assert report["params"]["adhoc"] is True
        assert report["params"]["focus"] == "aras_news"
