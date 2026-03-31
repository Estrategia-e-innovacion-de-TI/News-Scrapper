"""Preset loader for risk terms (Riesgos Emergentes).

Loads predefined term lists from ``risk_presets.yaml`` and supports merging
with explicit terms provided via CLI or API.
Ported from news_radar_mvp/extractor/adhoc/presets.py
Validates: Requirements 21.1-21.3
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger("newsradar.presets")

_DEFAULT_PRESETS_PATH = (
    Path(__file__).resolve().parents[4] / "config" / "risk_presets.yaml"
)


def load_presets(path: Path | str | None = None) -> dict[str, list[str]]:
    """Load risk presets from YAML (Req 21.1).

    Parameters
    ----------
    path:
        Path to the YAML file. Defaults to ``config/risk_presets.yaml``
        relative to the backend root.

    Returns
    -------
    dict mapping preset name → list of terms.
    """
    p = Path(path) if path else _DEFAULT_PRESETS_PATH
    with open(p, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {p}, got {type(data).__name__}")
    return {k: list(v) for k, v in data.items()}


def resolve_preset(
    name: str,
    presets: dict[str, list[str]] | None = None,
) -> list[str]:
    """Return the term list for *name* (Req 21.2).

    If *name* is ``"all"``, returns the union of every preset (order
    preserved, duplicates removed case-insensitively).

    Raises
    ------
    KeyError
        If the preset does not exist, with a descriptive message listing
        available presets (Req 21.3).
    """
    if presets is None:
        presets = load_presets()

    if name == "all":
        return _dedup_terms([t for terms in presets.values() for t in terms])

    if name not in presets:
        raise KeyError(
            f"Preset '{name}' no encontrado. Disponibles: {sorted(presets)}"
        )

    return list(presets[name])


def merge_terms(
    explicit: list[str] | None,
    preset: list[str] | None,
) -> list[str]:
    """Merge explicit terms with preset terms, deduplicating case-insensitively.

    Preserves the first occurrence of each term (by lowercase key).
    """
    combined: list[str] = []
    if explicit:
        combined.extend(explicit)
    if preset:
        combined.extend(preset)
    return _dedup_terms(combined)


def _dedup_terms(terms: list[str]) -> list[str]:
    """Remove duplicates case-insensitively, preserving first occurrence."""
    seen: set[str] = set()
    result: list[str] = []
    for t in terms:
        key = t.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(t.strip())
    return result
