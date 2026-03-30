"""Preset loader for risk terms (Riesgos Emergentes).

Loads predefined term lists from ``risk_presets.yaml`` and supports merging
with explicit ``--terms`` provided via CLI.
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_PRESETS_PATH = Path(__file__).resolve().parents[2] / "risk_presets.yaml"


def load_presets(path: Path | None = None) -> dict[str, list[str]]:
    """Load risk presets from YAML.

    Parameters
    ----------
    path:
        Path to the YAML file.  Defaults to ``risk_presets.yaml`` in the
        ``news_radar_mvp/`` package root.

    Returns
    -------
    dict mapping preset name → list of terms.
    """
    p = path or _DEFAULT_PRESETS_PATH
    with open(p, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {p}, got {type(data).__name__}")
    return {k: list(v) for k, v in data.items()}


def resolve_preset(
    preset_name: str,
    presets: dict[str, list[str]] | None = None,
) -> list[str]:
    """Return the term list for *preset_name*.

    If *preset_name* is ``"all"``, returns the union of every preset (order
    preserved, duplicates removed case-insensitively).
    """
    if presets is None:
        presets = load_presets()

    if preset_name == "all":
        return _dedup_terms([t for terms in presets.values() for t in terms])

    if preset_name not in presets:
        raise KeyError(f"Unknown preset '{preset_name}'. Available: {sorted(presets)}")

    return list(presets[preset_name])


def merge_terms(
    explicit_terms: list[str] | None,
    preset_terms: list[str] | None,
) -> list[str]:
    """Merge explicit CLI terms with preset terms, deduplicating case-insensitively.

    Preserves the first occurrence of each term (by lowercase key).
    """
    combined: list[str] = []
    if explicit_terms:
        combined.extend(explicit_terms)
    if preset_terms:
        combined.extend(preset_terms)
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
