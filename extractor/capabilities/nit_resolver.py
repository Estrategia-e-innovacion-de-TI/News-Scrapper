"""Capability: NIT → company name resolution.

Resolves Colombian NIT (tax ID) to company name using two sources:
1. Base ARAS.xlsx (primary) — also returns sector, categoria_riesgo, pais
2. nit_table.json (fallback) — flat dict NIT→name

Registered as capability ``nit_resolver``.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .registry import CapabilityDef, register_capability

logger = logging.getLogger(__name__)

# NIT format: 9-10 digits, optionally followed by -N (single check digit)
_NIT_RE = re.compile(r"^\d{9,10}(-\d)?$")


@dataclass
class NITResult:
    """Result of a NIT resolution."""

    company_name: str
    nit: str
    sector: str | None = None
    categoria_riesgo: str | None = None
    pais: str | None = None
    source: str = "excel"  # "excel" or "json"


class NITResolver:
    """Resolve NIT → company name from Excel + JSON fallback."""

    def __init__(
        self,
        excel_path: str | Path | None = None,
        json_path: str | Path | None = None,
    ) -> None:
        self._excel_path = Path(excel_path) if excel_path else Path("Base ARAS.xlsx")
        self._json_path = Path(json_path) if json_path else Path("nit_table.json")
        self._excel_cache: dict[str, dict[str, Any]] | None = None
        self._json_cache: dict[str, str] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def validate_nit(nit: str) -> bool:
        """Return True if *nit* matches the expected format."""
        return bool(_NIT_RE.match(nit))

    def resolve(self, nit: str) -> NITResult | None:
        """Resolve a NIT string to a :class:`NITResult`.

        Raises
        ------
        ValueError
            If the NIT format is invalid.

        Returns
        -------
        NITResult | None
            Resolved result or ``None`` when the NIT is not found.
        """
        if not self.validate_nit(nit):
            raise ValueError(
                "Formato de NIT inválido. Esperado: 9-10 dígitos, "
                "opcionalmente seguido de -N"
            )

        # 1. Try Excel (primary)
        result = self._lookup_excel(nit)
        if result is not None:
            return result

        # 2. Fallback to JSON
        return self._lookup_json(nit)

    # ------------------------------------------------------------------
    # Excel lookup
    # ------------------------------------------------------------------

    def _load_excel(self) -> dict[str, dict[str, Any]]:
        """Load and cache the Excel data. Returns dict keyed by num_doc."""
        if self._excel_cache is not None:
            return self._excel_cache

        if not self._excel_path.exists():
            logger.warning("Base ARAS.xlsx not found at %s — skipping Excel lookup", self._excel_path)
            self._excel_cache = {}
            return self._excel_cache

        try:
            import openpyxl

            wb = openpyxl.load_workbook(self._excel_path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()

            if not rows:
                self._excel_cache = {}
                return self._excel_cache

            headers = [str(h).strip().lower() if h else "" for h in rows[0]]
            col_map = {h: i for i, h in enumerate(headers)}

            cache: dict[str, dict[str, Any]] = {}
            for row in rows[1:]:
                num_doc_raw = row[col_map.get("num_doc", -1)] if "num_doc" in col_map else None
                if num_doc_raw is None:
                    continue
                num_doc = str(num_doc_raw).strip()
                if not num_doc:
                    continue
                cache[num_doc] = {
                    "nombre_cli": str(row[col_map["nombre_cli"]]).strip() if "nombre_cli" in col_map and row[col_map["nombre_cli"]] else "",
                    "sector": str(row[col_map["sector"]]).strip() if "sector" in col_map and row[col_map["sector"]] else None,
                    "categoria_riesgo": str(row[col_map["categoria_riesgo"]]).strip() if "categoria_riesgo" in col_map and row[col_map["categoria_riesgo"]] else None,
                    "pais": str(row[col_map["pais"]]).strip() if "pais" in col_map and row[col_map["pais"]] else None,
                }

            self._excel_cache = cache
            logger.info("Loaded %d entries from Base ARAS.xlsx", len(cache))
        except Exception:
            logger.exception("Error loading Base ARAS.xlsx")
            self._excel_cache = {}

        return self._excel_cache

    def _lookup_excel(self, nit: str) -> NITResult | None:
        cache = self._load_excel()
        entry = cache.get(nit)
        if entry is None:
            return None
        return NITResult(
            company_name=entry["nombre_cli"],
            nit=nit,
            sector=entry.get("sector"),
            categoria_riesgo=entry.get("categoria_riesgo"),
            pais=entry.get("pais"),
            source="excel",
        )

    # ------------------------------------------------------------------
    # JSON lookup
    # ------------------------------------------------------------------

    def _load_json(self) -> dict[str, str]:
        """Load and cache the JSON fallback table."""
        if self._json_cache is not None:
            return self._json_cache

        if not self._json_path.exists():
            logger.warning("nit_table.json not found at %s — skipping JSON lookup", self._json_path)
            self._json_cache = {}
            return self._json_cache

        try:
            with open(self._json_path, encoding="utf-8") as f:
                self._json_cache = json.load(f)
            logger.info("Loaded %d entries from nit_table.json", len(self._json_cache))
        except Exception:
            logger.exception("Error loading nit_table.json")
            self._json_cache = {}

        return self._json_cache

    def _lookup_json(self, nit: str) -> NITResult | None:
        cache = self._load_json()
        name = cache.get(nit)
        if name is None:
            return None
        return NITResult(
            company_name=name,
            nit=nit,
            source="json",
        )


# ------------------------------------------------------------------
# Capability registration
# ------------------------------------------------------------------

def resolve_nit(nit: str, excel_path: str | None = None, json_path: str | None = None) -> NITResult | None:
    """Convenience wrapper for capability registry."""
    resolver = NITResolver(excel_path=excel_path, json_path=json_path)
    return resolver.resolve(nit)


_cap = CapabilityDef(
    name="nit_resolver",
    purpose="Resolve Colombian NIT to company name (Excel primary, JSON fallback)",
    inputs_schema={"nit": "str", "excel_path": "str|None", "json_path": "str|None"},
    outputs_schema={"result": "NITResult|None"},
    callable=resolve_nit,
    tags=["nit", "aras", "resolution"],
)
register_capability(_cap)
