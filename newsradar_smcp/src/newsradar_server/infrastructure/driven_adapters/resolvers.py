"""NIT resolver adapter.

Resolves Colombian NIT to company name using Base ARAS.xlsx (primary)
and nit_table.json (fallback).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NITResolution:
    """Result of NIT resolution."""
    company_name: str
    nit: str
    sector: str | None = None
    categoria_riesgo: str | None = None
    pais: str | None = None


class NITResolver:
    """Resolves NIT → company name from Base ARAS.xlsx and nit_table.json.

    Validates NIT format: 9-10 digits optionally followed by -N.
    Primary source: Base ARAS.xlsx (columna num_doc).
    Fallback: nit_table.json.

    Implements: nit_resolver capability.
    """

    def __init__(
        self,
        excel_path: str = "Base ARAS.xlsx",
        json_path: str = "nit_table.json",
    ) -> None:
        self._excel_path = excel_path
        self._json_path = json_path

    def resolve(self, nit: str) -> NITResolution | None:
        """Resolve a NIT to company name and enrichment context.

        TODO: Port implementation from extractor/capabilities/nit_resolver.py
        """
        raise NotImplementedError("TODO: port NITResolver from extractor")

    @staticmethod
    def validate_format(nit: str) -> bool:
        """Validate NIT format: 9-10 digits, optionally -N.

        TODO: Port implementation from extractor/capabilities/nit_resolver.py
        """
        raise NotImplementedError("TODO: port NIT validation from extractor")
