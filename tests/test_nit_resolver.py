"""Tests for NITResolver — NIT format validation, resolution, and CLI integration."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from extractor.capabilities.nit_resolver import (
    NITResolver,
    NITResult,
    _NIT_RE,
)


# ── NIT format validation ──────────────────────────────────────────


class TestNITFormatValidation:
    """Test valid and invalid NIT formats."""

    @pytest.mark.parametrize(
        "nit",
        [
            "900123456",      # 9 digits
            "900123456-7",    # 9 digits + check digit
            "9001234567",     # 10 digits
            "9001234567-8",   # 10 digits + check digit
        ],
    )
    def test_valid_nit_formats(self, nit: str):
        assert NITResolver.validate_nit(nit) is True

    @pytest.mark.parametrize(
        "nit",
        [
            "12345",          # too short
            "abcdefghij",     # letters
            "900123456-78",   # two check digits
            "900123456-",     # trailing hyphen, no digit
            "",               # empty
            "12345678",       # 8 digits (too short)
            "12345678901",    # 11 digits (too long)
        ],
    )
    def test_invalid_nit_formats(self, nit: str):
        assert NITResolver.validate_nit(nit) is False


# ── NIT resolution ─────────────────────────────────────────────────


class TestNITResolution:
    """Test NIT resolution from JSON fallback (Excel mocked/skipped)."""

    def test_resolve_from_json(self, tmp_path: Path):
        """NIT found in nit_table.json returns NITResult with source='json'."""
        json_file = tmp_path / "nit_table.json"
        json_file.write_text(json.dumps({"860002964-4": "Banco de Bogotá"}))

        resolver = NITResolver(
            excel_path=tmp_path / "nonexistent.xlsx",
            json_path=json_file,
        )
        result = resolver.resolve("860002964-4")

        assert result is not None
        assert result.company_name == "Banco de Bogotá"
        assert result.nit == "860002964-4"
        assert result.source == "json"
        assert result.sector is None
        assert result.categoria_riesgo is None
        assert result.pais is None

    def test_resolve_not_found_returns_none(self, tmp_path: Path):
        """NIT not in any source returns None."""
        json_file = tmp_path / "nit_table.json"
        json_file.write_text(json.dumps({"860002964-4": "Banco de Bogotá"}))

        resolver = NITResolver(
            excel_path=tmp_path / "nonexistent.xlsx",
            json_path=json_file,
        )
        result = resolver.resolve("999999999-0")

        assert result is None

    def test_resolve_invalid_format_raises(self, tmp_path: Path):
        """Invalid NIT format raises ValueError with expected message."""
        resolver = NITResolver(
            excel_path=tmp_path / "nonexistent.xlsx",
            json_path=tmp_path / "nit_table.json",
        )
        with pytest.raises(ValueError, match="Formato de NIT inválido"):
            resolver.resolve("abc")

    def test_error_message_content(self, tmp_path: Path):
        """Verify the exact error message for invalid NIT."""
        resolver = NITResolver(
            excel_path=tmp_path / "nonexistent.xlsx",
            json_path=tmp_path / "nit_table.json",
        )
        with pytest.raises(ValueError) as exc_info:
            resolver.resolve("12345")
        assert "9-10 dígitos" in str(exc_info.value)
        assert "-N" in str(exc_info.value)

    def test_excel_priority_over_json(self, tmp_path: Path):
        """When NIT exists in both Excel and JSON, Excel takes priority."""
        json_file = tmp_path / "nit_table.json"
        json_file.write_text(json.dumps({"860002964-4": "JSON Name"}))

        resolver = NITResolver(
            excel_path=tmp_path / "nonexistent.xlsx",
            json_path=json_file,
        )
        # Mock the Excel cache to simulate Excel having the entry
        resolver._excel_cache = {
            "860002964-4": {
                "nombre_cli": "Excel Name",
                "sector": "Financiero",
                "categoria_riesgo": "Alto",
                "pais": "Colombia",
            }
        }
        result = resolver.resolve("860002964-4")

        assert result is not None
        assert result.company_name == "Excel Name"
        assert result.source == "excel"
        assert result.sector == "Financiero"
        assert result.categoria_riesgo == "Alto"
        assert result.pais == "Colombia"

    def test_json_cache_is_reused(self, tmp_path: Path):
        """JSON data is loaded once and cached."""
        json_file = tmp_path / "nit_table.json"
        json_file.write_text(json.dumps({"860002964-4": "Banco de Bogotá"}))

        resolver = NITResolver(
            excel_path=tmp_path / "nonexistent.xlsx",
            json_path=json_file,
        )
        resolver.resolve("860002964-4")
        # Second call should use cache
        resolver.resolve("860002964-4")
        assert resolver._json_cache is not None

    def test_missing_json_file_returns_none(self, tmp_path: Path):
        """When nit_table.json doesn't exist, resolution returns None."""
        resolver = NITResolver(
            excel_path=tmp_path / "nonexistent.xlsx",
            json_path=tmp_path / "nonexistent.json",
        )
        result = resolver.resolve("860002964-4")
        assert result is None


# ── CLI --nit flag ─────────────────────────────────────────────────


class TestCLINitFlag:
    """Test CLI accepts --nit and handles --nit + --company together."""

    def test_nit_flag_is_accepted(self):
        """parse_args accepts --nit without error."""
        from extractor.main import parse_args

        with patch("sys.argv", ["prog", "--nit", "900123456-7", "--focus", "aras_news", "--adhoc", "--date-from", "2025-01-01", "--date-to", "2025-01-31"]):
            args = parse_args()
        assert args.nit == "900123456-7"

    def test_nit_and_company_uses_company(self):
        """When both --nit and --company are provided, validate_args passes and --company is used."""
        from extractor.main import validate_args
        import argparse

        args = argparse.Namespace(
            adhoc=True,
            focus="aras_news",
            company="TestCorp",
            nit="900123456-7",
            terms=None,
            date_from="2025-01-01",
            date_to="2025-01-31",
        )
        error = validate_args(args)
        assert error is None  # no error — --company takes precedence

    def test_nit_alone_passes_validation(self):
        """--nit without --company passes validation for aras_news."""
        from extractor.main import validate_args
        import argparse

        args = argparse.Namespace(
            adhoc=True,
            focus="aras_news",
            company=None,
            nit="900123456-7",
            terms=None,
            date_from="2025-01-01",
            date_to="2025-01-31",
        )
        error = validate_args(args)
        assert error is None

    def test_no_company_no_nit_fails_validation(self):
        """Neither --company nor --nit fails validation for aras_news."""
        from extractor.main import validate_args
        import argparse

        args = argparse.Namespace(
            adhoc=True,
            focus="aras_news",
            company=None,
            nit=None,
            terms=None,
            date_from="2025-01-01",
            date_to="2025-01-31",
        )
        error = validate_args(args)
        assert error is not None
        assert "--company" in error or "--nit" in error


# ── Capability registration ────────────────────────────────────────


class TestCapabilityRegistration:
    """Verify nit_resolver is registered in the CapabilityRegistry."""

    def test_nit_resolver_registered(self):
        from extractor.capabilities.registry import get_capability

        cap = get_capability("nit_resolver")
        assert cap is not None
        assert cap.name == "nit_resolver"
        assert callable(cap.callable)
