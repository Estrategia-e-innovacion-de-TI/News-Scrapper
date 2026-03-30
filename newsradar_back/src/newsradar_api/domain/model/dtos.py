"""Request and response DTOs for the News Radar API.

All models use Pydantic BaseModel for automatic validation.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────

class DocumentResult(BaseModel):
    """Single document in search results."""

    title: str = ""
    source: str = ""
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    summary: str = ""
    category: Optional[str] = None
    severity: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)


# ── ARAS ──────────────────────────────────────────────────────────────

class ArasSearchRequest(BaseModel):
    """Request body for POST /api/aras/search."""

    company: Optional[str] = Field(None, description="Company name to search")
    nit: Optional[str] = Field(None, description="Colombian NIT (alternative to company)")
    risk_category: Optional[str] = Field(None, description="ARAS risk category filter")
    date_from: Optional[date] = Field(None, description="Start date range")
    date_to: Optional[date] = Field(None, description="End date range")
    classifier: str = Field("rules", description="Classifier mode: rules | llm")


class ArasSearchResponse(BaseModel):
    """Response body for POST /api/aras/search."""

    run_id: str
    total_documents: int = 0
    total_classified: int = 0
    results: list[DocumentResult] = Field(default_factory=list)
    excel_url: Optional[str] = None


# ── Riesgos ───────────────────────────────────────────────────────────

class RiesgosSearchRequest(BaseModel):
    """Request body for POST /api/riesgos/search."""

    terms: list[str] = Field(default_factory=list, description="Custom search terms")
    terms_preset: Optional[str] = Field(
        None, description="Preset: ciber | fraude | operacional | ambiental_social | all"
    )
    date_from: Optional[date] = Field(None, description="Start date range")
    date_to: Optional[date] = Field(None, description="End date range")
    classifier: str = Field("rules", description="Classifier mode: rules | llm")


class RiesgosSearchResponse(BaseModel):
    """Response body for POST /api/riesgos/search."""

    run_id: str
    total_documents: int = 0
    total_classified: int = 0
    results: list[DocumentResult] = Field(default_factory=list)
    excel_url: Optional[str] = None


# ── Vigilancia ────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    """Request body for POST /api/vigilancia/subscribe."""

    email: str = Field(..., description="Subscriber email address")
    name: str = Field(..., description="Subscriber display name")
    query_groups: list[str] = Field(..., description="List of topic groups to subscribe to")


class SubscribeResponse(BaseModel):
    """Response body for POST /api/vigilancia/subscribe."""

    status: str = "ok"
    email: str = ""
    subscribed_groups: list[str] = Field(default_factory=list)


class TopicItem(BaseModel):
    """Single topic/query group available for subscription."""

    group_id: str
    display_name: str
    term_count: int = 0


class TopicsResponse(BaseModel):
    """Response body for GET /api/vigilancia/topics."""

    topics: list[TopicItem] = Field(default_factory=list)
