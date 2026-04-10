"""Request and response DTOs for the News Radar API.

All models use Pydantic BaseModel for automatic validation.

Validates: Requirements 1.2, 2.3, 12.2-12.3, 19.2, 22.1-22.4
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────

class DocumentResult(BaseModel):
    """Single document in search results.

    Validates: Requirements 1.2, 2.3
    """

    title: str = ""
    source: str = ""
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    summary: str = ""
    category: Optional[str] = None
    severity: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)
    # Classification enrichment (Req 1.2)
    classifier_mode: Optional[str] = Field(
        None, description="Classifier used: rules | llm"
    )
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Classification confidence 0.0-1.0"
    )
    matched_keywords: list[str] = Field(
        default_factory=list, description="Keywords that matched during classification"
    )
    events: list[str] = Field(
        default_factory=list, description="Materialized events detected (riesgos)"
    )
    # Relevance (Req 2.3)
    relevance_score: Optional[int] = Field(
        None, ge=0, le=100, description="Relevance score 0-100"
    )


# ── ARAS ──────────────────────────────────────────────────────────────

class ArasSearchRequest(BaseModel):
    """Request body for POST /api/aras/search."""

    company: Optional[str] = Field(None, description="Company name to search")
    issuer: Optional[str] = Field(None, description="Issuer name to search")
    nit: Optional[str] = Field(None, description="Colombian NIT (alternative to company)")
    term: Optional[str] = Field(None, description="General risk term to search")
    terms: list[str] = Field(default_factory=list, description="Additional ad-hoc terms")
    risk_category: Optional[str] = Field(None, description="ARAS risk category filter")
    date_from: Optional[date] = Field(None, description="Start date range")
    date_to: Optional[date] = Field(None, description="End date range")
    classifier: str = Field("rules", description="Classifier mode: rules | llm")


class ArasSearchResponse(BaseModel):
    """Response body for POST /api/aras/search."""

    run_id: str
    search_id: Optional[str] = None
    audit_id: Optional[str] = None
    export_id: Optional[str] = None
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
    search_id: Optional[str] = None
    audit_id: Optional[str] = None
    export_id: Optional[str] = None
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
    terms: list[str] = Field(default_factory=list)


class TopicsResponse(BaseModel):
    """Response body for GET /api/vigilancia/topics."""

    topics: list[TopicItem] = Field(default_factory=list)


# ── Trendmap Snapshot ─────────────────────────────────────────────────

class TrendmapSnapshotResponse(BaseModel):
    """Response for a trendmap snapshot query.

    Wraps the snapshot ID and generation timestamp alongside the full
    trendmap data payload (delegated to ``TrendmapResponse`` in
    ``trendmap_models.py``).

    Validates: Requirements 14.8
    """

    snapshot_id: str
    generated_at: Optional[datetime] = None
    data: dict = Field(
        default_factory=dict,
        description="Full trendmap.json payload (meta, clusters, articles, …)",
    )


# ── Pipeline Run ──────────────────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    """Request body for POST /api/pipeline/run.

    Validates: Requirements 19.2
    """

    catalog_path: str = Field("catalog.yaml", description="Path to catalog YAML")
    days: int = Field(7, description="Look-back window in days")
    max_items_per_source: int = Field(20, description="Max items per source")
    focus: Optional[str] = Field(None, description="Focus filter: aras_latam | riesgos_latam | vigilancia_global")
    adhoc: bool = Field(False, description="Ad-hoc mode flag")
    company: Optional[str] = Field(None, description="Company name (ARAS)")
    terms: Optional[str] = Field(None, description="Comma-separated risk terms")
    date_from: Optional[date] = Field(None, description="Start date range")
    date_to: Optional[date] = Field(None, description="End date range")
    classifier_mode: Literal["rules", "llm"] = Field("rules", description="Classifier mode")
    dry_run: bool = Field(False, description="Dry-run: discover only, no fetch")
    nit: Optional[str] = Field(None, description="Colombian NIT for ARAS")
    terms_preset: Optional[str] = Field(None, description="Risk terms preset name")


class PipelineRunResponse(BaseModel):
    """Response body for POST /api/pipeline/run.

    Validates: Requirements 19.2
    """

    run_id: str
    status: str = Field("started", description="Pipeline status: started | running | completed | failed")


# ── Excel Export ──────────────────────────────────────────────────────

class ExcelExportResponse(BaseModel):
    """Response body for POST /api/export/excel.

    Validates: Requirements 12.2-12.3
    """

    file_url: str = Field(..., description="URL to download the generated .xlsx file")
    file_name: str = Field("", description="Generated file name")
    total_rows: int = Field(0, description="Number of data rows in the Resultados sheet")


# ── Subscriptions ─────────────────────────────────────────────────────

class SubscriptionDTO(BaseModel):
    """Subscription data transfer object for vigilancia subscriptions.

    Validates: Requirements 22.1-22.4
    """

    id: str = Field(..., description="Subscription UUID")
    email: str = Field(..., description="Subscriber email address")
    query_groups: list[str] = Field(
        default_factory=list,
        description="Subscribed topic groups (validated against terms_vigilancia.yaml)",
    )
    active: bool = Field(True, description="Whether the subscription is active")
