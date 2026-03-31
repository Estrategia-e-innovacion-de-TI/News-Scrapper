"""Helpers to resolve shared declarative configuration files."""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_ROOT = REPO_ROOT / "newsradar_back"
BACKEND_CONFIG_ROOT = BACKEND_ROOT / "config"
SHARED_ROOT = REPO_ROOT / "shared"


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def shared_path(*parts: str) -> Path:
    return SHARED_ROOT.joinpath(*parts)


def backend_config_path(*parts: str) -> Path:
    return BACKEND_CONFIG_ROOT.joinpath(*parts)


def resolve_catalog_path(path: str | Path | None = None) -> Path:
    """Return the best available catalog path.

    Priority:
    1. Explicit path
    2. ``shared/catalog.yaml``
    3. ``newsradar_back/config/catalog.yaml``
    4. ``catalog.yaml`` at repo root
    """
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    candidates.extend(
        [
            shared_path("catalog.yaml"),
            backend_config_path("catalog.yaml"),
            repo_path("catalog.yaml"),
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def resolve_terms_path(path: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    candidates.extend(
        [
            shared_path("topics", "tech_watch.yaml"),
            shared_path("terms_vigilancia.yaml"),
            backend_config_path("terms_vigilancia.yaml"),
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def resolve_prompt_path(filename: str) -> Path:
    shared_candidate = shared_path("prompts", filename)
    if shared_candidate.exists():
        return shared_candidate
    return backend_config_path("prompts", filename)


def resolve_flow_path(filename: str) -> Path:
    shared_candidate = shared_path("flows", filename)
    if shared_candidate.exists():
        return shared_candidate
    return backend_config_path(filename)


def load_yaml_file(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        return {}
    return data
