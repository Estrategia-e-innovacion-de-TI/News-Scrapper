"""Load search terms from YAML configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml


def load_terms(path: str | Path) -> dict[str, Any]:
    """
    Load terms YAML file.
    
    Expected format:
    papers:
      terms: ["machine learning", "LLM security"]
      filters:
        require_keywords_any: ["risk", "fraud"]
    repos:
      terms: ["langgraph", "news-extraction"]
      filters:
        min_stars: 50
        updated_within_days: 90
    patents:
      terms: ["fraud detection AI"]
      filters:
        date_window_months: 6
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Terms file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not data:
        raise ValueError("Empty terms file")
    
    return data


def get_terms_for_mode(terms_data: dict[str, Any], mode: str) -> list[str]:
    """Get search terms for a specific mode."""
    section = terms_data.get(mode, {})
    return section.get("terms", [])


def get_filters_for_mode(terms_data: dict[str, Any], mode: str) -> dict[str, Any]:
    """Get filters for a specific mode."""
    section = terms_data.get(mode, {})
    return section.get("filters", {})
