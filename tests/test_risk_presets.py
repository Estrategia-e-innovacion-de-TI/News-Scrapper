"""Tests for risk preset loading, resolution, and CLI integration."""
from __future__ import annotations

import textwrap
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from extractor.adhoc.presets import load_presets, merge_terms, resolve_preset
from extractor.main import validate_args


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ns(**kwargs) -> Namespace:
    """Build a Namespace with sensible defaults, overridden by kwargs."""
    defaults = dict(
        focus=None, adhoc=False, company=None, nit=None, terms=None,
        terms_preset=None, date_from=None, date_to=None, candidates=None,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


# ---------------------------------------------------------------------------
# load_presets
# ---------------------------------------------------------------------------

class TestLoadPresets:
    def test_loads_from_default_path(self):
        presets = load_presets()
        assert isinstance(presets, dict)
        assert "ciber" in presets
        assert "fraude" in presets
        assert "operacional" in presets
        assert "ambiental_social" in presets

    def test_each_preset_is_nonempty_list(self):
        presets = load_presets()
        for name, terms in presets.items():
            assert isinstance(terms, list), f"{name} should be a list"
            assert len(terms) > 0, f"{name} should not be empty"

    def test_loads_from_custom_path(self, tmp_path: Path):
        custom = tmp_path / "custom.yaml"
        custom.write_text(yaml.dump({"test_preset": ["term1", "term2"]}))
        presets = load_presets(custom)
        assert presets == {"test_preset": ["term1", "term2"]}


# ---------------------------------------------------------------------------
# resolve_preset
# ---------------------------------------------------------------------------

class TestResolvePreset:
    def test_resolve_known_preset(self):
        presets = load_presets()
        terms = resolve_preset("ciber", presets)
        assert "ransomware" in terms
        assert "phishing" in terms

    def test_resolve_all_is_union(self):
        presets = load_presets()
        all_terms = resolve_preset("all", presets)
        for name, terms in presets.items():
            for t in terms:
                assert t.strip().lower() in {x.strip().lower() for x in all_terms}, (
                    f"Term '{t}' from preset '{name}' missing in 'all'"
                )

    def test_resolve_all_has_no_duplicates(self):
        presets = load_presets()
        all_terms = resolve_preset("all", presets)
        lowered = [t.lower() for t in all_terms]
        assert len(lowered) == len(set(lowered))

    def test_resolve_unknown_preset_raises(self):
        with pytest.raises(KeyError, match="Unknown preset"):
            resolve_preset("nonexistent", {"ciber": ["x"]})


# ---------------------------------------------------------------------------
# merge_terms
# ---------------------------------------------------------------------------

class TestMergeTerms:
    def test_merge_both_lists(self):
        result = merge_terms(["a", "b"], ["c", "d"])
        assert result == ["a", "b", "c", "d"]

    def test_merge_dedup_case_insensitive(self):
        result = merge_terms(["Phishing", "malware"], ["phishing", "DDoS"])
        lowered = [t.lower() for t in result]
        assert lowered.count("phishing") == 1
        assert "malware" in lowered
        assert "ddos" in lowered

    def test_merge_preserves_first_occurrence(self):
        result = merge_terms(["Phishing"], ["phishing"])
        assert result == ["Phishing"]

    def test_merge_only_explicit(self):
        result = merge_terms(["a", "b"], None)
        assert result == ["a", "b"]

    def test_merge_only_preset(self):
        result = merge_terms(None, ["c", "d"])
        assert result == ["c", "d"]

    def test_merge_both_none(self):
        result = merge_terms(None, None)
        assert result == []


# ---------------------------------------------------------------------------
# CLI validation
# ---------------------------------------------------------------------------

class TestCLIValidation:
    def test_terms_preset_flag_accepted(self):
        """parse_args accepts --terms-preset without error."""
        from extractor.main import parse_args

        with patch(
            "sys.argv",
            [
                "prog",
                "--focus", "riesgos_news",
                "--adhoc",
                "--terms-preset", "ciber",
                "--date-from", "2025-01-01",
                "--date-to", "2025-03-01",
            ],
        ):
            args = parse_args()
            assert args.terms_preset == "ciber"

    def test_neither_terms_nor_preset_fails(self):
        err = validate_args(_ns(
            focus="riesgos_news", adhoc=True,
            date_from="2025-01-01", date_to="2025-03-01",
        ))
        assert err is not None
        assert "terms" in err.lower()

    def test_terms_preset_alone_passes(self):
        err = validate_args(_ns(
            focus="riesgos_news", adhoc=True,
            terms_preset="ciber",
            date_from="2025-01-01", date_to="2025-03-01",
        ))
        assert err is None

    def test_terms_alone_passes(self):
        err = validate_args(_ns(
            focus="riesgos_news", adhoc=True,
            terms="fraude,estafa",
            date_from="2025-01-01", date_to="2025-03-01",
        ))
        assert err is None

    def test_both_terms_and_preset_passes(self):
        err = validate_args(_ns(
            focus="riesgos_news", adhoc=True,
            terms="custom_term",
            terms_preset="ciber",
            date_from="2025-01-01", date_to="2025-03-01",
        ))
        assert err is None
