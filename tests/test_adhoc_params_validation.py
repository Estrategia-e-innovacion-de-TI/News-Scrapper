"""Tests for CLI argument validation in adhoc mode."""
import pytest
from argparse import Namespace

from extractor.main import validate_args


def _ns(**kwargs) -> Namespace:
    """Build a Namespace with sensible defaults, overridden by kwargs."""
    defaults = dict(
        focus=None, adhoc=False, company=None, nit=None, terms=None,
        date_from=None, date_to=None, candidates=None,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


class TestAdhocValidation:
    def test_adhoc_without_focus_errors(self):
        err = validate_args(_ns(adhoc=True))
        assert err is not None
        assert "aras_news" in err

    def test_adhoc_with_riesgos_allowed(self):
        """riesgos_news is now supported for --adhoc."""
        err = validate_args(_ns(adhoc=True, focus="riesgos_news", terms="fraude",
                                date_from="2026-01-01", date_to="2026-03-01"))
        assert err is None

    def test_aras_missing_company(self):
        err = validate_args(_ns(focus="aras_news", adhoc=True,
                                date_from="2026-01-01", date_to="2026-03-01"))
        assert err is not None
        assert "company" in err.lower() or "nit" in err.lower()

    def test_aras_missing_date_from(self):
        err = validate_args(_ns(focus="aras_news", adhoc=True, company="X",
                                date_to="2026-03-01"))
        assert err is not None
        assert "date" in err.lower()

    def test_aras_missing_date_to(self):
        err = validate_args(_ns(focus="aras_news", adhoc=True, company="X",
                                date_from="2026-01-01"))
        assert err is not None
        assert "date" in err.lower()

    def test_aras_date_from_after_date_to(self):
        err = validate_args(_ns(focus="aras_news", adhoc=True, company="X",
                                date_from="2026-06-01", date_to="2026-01-01"))
        assert err is not None
        assert "date-from" in err.lower() or "<=" in err

    def test_aras_valid(self):
        err = validate_args(_ns(focus="aras_news", adhoc=True, company="Bancolombia",
                                date_from="2026-01-01", date_to="2026-03-01"))
        assert err is None

    def test_aras_without_adhoc_flag(self):
        err = validate_args(_ns(focus="aras_news", company="X",
                                date_from="2026-01-01", date_to="2026-03-01"))
        assert err is not None
        assert "adhoc" in err.lower()

    def test_vigilancia_with_adhoc_errors(self):
        err = validate_args(_ns(focus="vigilancia_news", adhoc=True))
        assert err is not None
        assert "vigilancia" in err.lower() or "adhoc" in err.lower()

    def test_no_focus_no_adhoc_ok(self):
        err = validate_args(_ns())
        assert err is None
