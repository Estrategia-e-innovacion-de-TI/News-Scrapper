"""NIT → company name resolution.

Resolves Colombian NIT (tax ID) to company name using a JSON lookup table.
Ported from news_radar_mvp/extractor/capabilities/nit_resolver.py
Validates: Requirements 20.1-20.3
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger("newsradar.nit_resolver")

# NIT format: 9-10 digits, optionally followed by -N (single check digit)
_NIT_RE = re.compile(r"^\d{9,10}(-\d)?$")

_DEFAULT_JSON_PATH = Path(__file__).resolve().parents[4] / "config" / "nit_table.json"


class NITResolver:
    """Resolve NIT → company name from JSON table."""

    def __init__(self, json_path: str | Path | None = None) -> None:
        self._json_path = Path(json_path) if json_path else _DEFAULT_JSON_PATH
        self._cache: dict[str, str] | None = None

    @staticmethod
    def validate_nit(nit: str) -> bool:
        """Return True if *nit* matches the expected format (Req 20.1).

        Valid format: 9-10 digits, optionally followed by -N.
        """
        return bool(_NIT_RE.match(nit))

    def resolve(self, nit: str) -> str | None:
        """Resolve a NIT string to a company name (Req 20.1, 20.2).

        Parameters
        ----------
        nit:
            The NIT string to resolve.

        Returns
        -------
        str | None
            Company name or ``None`` when the NIT is not found.

        Raises
        ------
        ValueError
            If the NIT format is invalid.
        """
        if not self.validate_nit(nit):
            raise ValueError(
                "Formato de NIT inválido. Esperado: 9-10 dígitos, "
                "opcionalmente seguido de -N"
            )

        table = self._load_table()
        name = table.get(nit)

        if name is None:
            logger.warning("NIT %s no encontrado en tabla de resolución", nit)
            return None

        return name

    def _load_table(self) -> dict[str, str]:
        """Load and cache the JSON lookup table."""
        if self._cache is not None:
            return self._cache

        if not self._json_path.exists():
            logger.warning(
                "nit_table.json not found at %s — NIT resolution disabled",
                self._json_path,
            )
            self._cache = {}
            return self._cache

        try:
            with open(self._json_path, encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.info("Loaded %d entries from nit_table.json", len(self._cache))
        except Exception:
            logger.exception("Error loading nit_table.json")
            self._cache = {}

        return self._cache
