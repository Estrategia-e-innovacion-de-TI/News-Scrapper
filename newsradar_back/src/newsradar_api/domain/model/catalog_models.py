"""Catalog and export domain models.

Ports CATALOG_DEFAULTS and export request from
``news_radar_mvp/extractor/catalog.py`` to Pydantic v2.

Validates: Requirements 5.1-5.4, 12.1-12.6
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Re-export SourceConfig so consumers can import from either module.
from newsradar_api.domain.model.pipeline_models import SourceConfig  # noqa: F401

__all__ = [
    "SourceConfig",
    "CatalogDefaults",
    "ExcelExportRequest",
]


# ── Catalog defaults ──────────────────────────────────────────────────


class CatalogDefaults(BaseModel):
    """Default values merged into every source from the catalog YAML.

    Hardcoded defaults match the original MVP ``CATALOG_DEFAULTS`` dict.
    The ``merge()`` class method overlays file-level defaults on top.

    Validates: Requirements 5.1-5.4
    """

    model_config = ConfigDict(frozen=False)

    timeout_seconds: int = 25
    max_retries: int = 2
    retry_backoff_seconds: float = 1.7
    rate_limit_rps: float = 1.0
    max_items_per_source: int = 30
    min_text_chars: int = 800
    allow_languages: list[str] = Field(default_factory=lambda: ["es", "en", "pt"])
    store_raw_html: bool = False
    debug_store_samples_per_source: int = 3

    @classmethod
    def merge(cls, overrides: dict | None = None) -> "CatalogDefaults":
        """Create defaults with optional overrides from catalog YAML."""
        if not overrides:
            return cls()
        return cls(**{k: v for k, v in overrides.items() if k in cls.model_fields})


# ── Excel export ──────────────────────────────────────────────────────


class ExcelExportRequest(BaseModel):
    """Request payload for Excel report generation.

    Validates: Requirements 12.1-12.6
    """

    model_config = ConfigDict(frozen=False)

    run_id: str = ""
    output_path: str = "output/report.xlsx"
    company_or_terms: str = ""
    date_from: str | None = None
    date_to: str | None = None
    total_documents: int = 0
    total_classified: int = 0
