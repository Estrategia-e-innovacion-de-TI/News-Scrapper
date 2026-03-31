"""Data models for search results.

Ported from news_radar_mvp/extractor/search/models.py.

Validates: Requirements 18.1-18.5
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SearchCandidate(BaseModel):
    """A candidate found via external search provider."""

    mode: str  # papers | repos | patents
    term: str  # search term that found it
    title: str
    url: str
    snippet: str = ""
    published_at: str | None = None
    fetched_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source_provider: str = ""  # arxiv | github | epo_ops
    score: float = 0.0
    extra: dict = Field(default_factory=dict)


class SearchReport(BaseModel):
    """Report for a search run."""

    mode: str
    terms_count: int
    total_candidates: int
    by_term: dict[str, int] = Field(default_factory=dict)
    providers_used: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    duration_seconds: float = 0.0
