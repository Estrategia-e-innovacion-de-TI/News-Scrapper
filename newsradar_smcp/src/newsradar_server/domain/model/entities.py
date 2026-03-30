"""Domain entities — Pydantic models for the News Radar pipeline.

Extracted from extractor/state.py to form the core domain model.
These are pure data models with no infrastructure dependencies.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

import uuid
from pydantic import BaseModel, ConfigDict, Field


# ── Value Objects (small, immutable) ─────────────────────────────────


class FetchMethod(str, Enum):
    RSS = "rss"
    HTTP = "http"
    PLAYWRIGHT = "playwright"
    PDF = "pdf"


class ItemStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    SKIPPED = "skipped"
    ERROR = "error"


class ErrorType(str, Enum):
    TIMEOUT = "timeout"
    FORBIDDEN = "http_403"
    HTTP_4XX = "http_4xx"
    HTTP_5XX = "http_5xx"
    PAYWALL = "paywall"
    EMPTY = "empty_or_thin"
    PARSE = "parse_error"
    SELECTOR_NO_MATCH = "selector_no_match"
    PDF_PARSE = "pdf_parse_error"
    REDIRECT = "redirect_error"
    TLS_ERROR = "tls_error"
    CUSTOM_PENDING = "custom_pending"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class SkipReason(str, Enum):
    GATED_PAYWALL = "gated_paywall_known"
    CUSTOM_PENDING = "custom_pending"
    PLAYWRIGHT_DISABLED = "requires_playwright_but_disabled"
    NO_MATCHES = "no_matches_adhoc"


class EvidenceSpan(BaseModel):
    """Value object: text fragment around a matched term with offsets."""
    text: str
    start_offset: int
    end_offset: int
    matched_term: str


# ── Entities ─────────────────────────────────────────────────────────


class SourceConfig(BaseModel):
    """Parsed source configuration from catalog."""
    source_id: str
    name: str
    enabled: bool = True
    availability: str = "unknown"
    focus: list[str] = Field(default_factory=list)
    pipeline_class: str = "news"
    type: Literal["rss", "scrape", "pdf", "query", "custom"]
    base_url: str = ""
    rss_urls: list[str] = Field(default_factory=list)
    listing_urls: list[str] = Field(default_factory=list)
    pdf_urls: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["es", "en"])
    geo: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    requires_playwright: bool = False
    selectors: dict[str, str] = Field(default_factory=dict)
    profile_required: bool = False
    quality_hint: str = "ok"
    notes: str = ""
    timeout_seconds: int = 25
    max_retries: int = 2
    rate_limit_rps: float = 1.0
    min_text_chars: int = 800


class QueueItem(BaseModel):
    """Item in the processing queue."""
    source_id: str
    url: str
    source_url: str
    fetch_method: FetchMethod
    title: str | None = None
    published_at: str | None = None
    requires_playwright: bool = False
    status: ItemStatus = ItemStatus.PENDING
    error_type: ErrorType | None = None
    error_msg: str | None = None
    skip_reason: SkipReason | None = None


class SearchCandidate(BaseModel):
    """Candidate item from search ingestion (ArXiv, GitHub, Patents)."""
    source: str
    title: str
    url: str
    published_at: str | None = None
    excerpt: str = ""
    score: float = 0.0
    mode: str = ""  # papers | repos | patents


class MatchResult(BaseModel):
    """Result of matching a document against query terms."""
    matched: bool
    matched_terms: list[str] = Field(default_factory=list)
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Extracted document ready for persistence."""
    run_id: str
    source_id: str
    pipeline_class: str
    focus: list[str]
    title: str
    url: str
    canonical_url: str | None = None
    published_at: str | None = None
    fetched_at: str
    language: str = "unknown"
    text: str
    excerpt: str
    raw_len: int
    text_len: int
    text_capped: bool = False
    hash: str
    fetch_method: str
    status: str = "ok"
    error_type: str | None = None
    source_url: str
    origin: str = "catalog"
    query_type: str | None = None
    query_terms: list[str] = Field(default_factory=list)
    query_range: dict[str, str] = Field(default_factory=dict)

    # Classification (Req 1)
    category: str | None = None
    risk_type: str | None = None
    materialized_events: list[str] = Field(default_factory=list)

    # Severity (Req 2)
    severity: str | None = None
    severity_confidence: float | None = None
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)

    # Relevance scoring — vigilancia (Req 4)
    relevance_score: int | None = None


class SourceMetrics(BaseModel):
    """Metrics for a single source."""
    source_id: str
    discovered: int = 0
    fetched_ok: int = 0
    text_ok: int = 0
    dupes: int = 0
    skipped: int = 0
    errors: int = 0
    errors_by_type: dict[str, int] = Field(default_factory=dict)
    avg_text_len: float = 0.0
    requires_playwright: bool = False
    matched_candidates: int = 0
    selected_candidates: int = 0

    # Classification counts (Req 11)
    classified_ok: int = 0
    classified_error: int = 0
    severity_h: int = 0
    severity_m: int = 0
    severity_l: int = 0


class RunMetrics(BaseModel):
    """Global run metrics."""
    run_id: str
    started_at: str
    finished_at: str | None = None
    duration_seconds: float = 0.0
    total_sources: int = 0
    total_discovered: int = 0
    total_fetched: int = 0
    total_ok: int = 0
    total_skipped: int = 0
    total_errors: int = 0
    total_dupes: int = 0
    by_source: dict[str, SourceMetrics] = Field(default_factory=dict)


class GraphState(BaseModel):
    """Main state for LangGraph pipeline."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # CLI params
    catalog_path: str = "catalog.yaml"
    days: int = 7
    max_items_per_source: int = 20
    out_dir: str = "out"
    debug: bool = False
    dry_run: bool = False
    only_source: str | None = None
    no_playwright: bool = False
    store_raw_html: bool = False

    # Focus / ad-hoc params
    focus: str | None = None
    adhoc: bool = False
    company: str | None = None
    terms: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    topk_per_source: int = 5
    max_candidates_total: int = 50
    match_mode: str = "metadata_only"

    # Classifier mode (Req 11)
    classifier_mode: str = "rules"

    # NIT (Req 7)
    nit: str | None = None

    # Terms preset (Req 12)
    terms_preset: str | None = None

    # Candidates ingestion
    candidates_path: str | None = None

    # Text cap
    max_text_chars: int = 50000

    # Catalog data
    defaults: dict[str, Any] = Field(default_factory=dict)
    sources: list[SourceConfig] = Field(default_factory=list)
    selected_sources: list[SourceConfig] = Field(default_factory=list)

    # Processing queues
    queue: list[QueueItem] = Field(default_factory=list)
    http_queue: list[QueueItem] = Field(default_factory=list)
    browser_queue: list[QueueItem] = Field(default_factory=list)
    pdf_queue: list[QueueItem] = Field(default_factory=list)
    skipped_queue: list[QueueItem] = Field(default_factory=list)

    # Results
    documents: list[Document] = Field(default_factory=list)
    seen_hashes: set[str] = Field(default_factory=set)

    # Metrics
    metrics: RunMetrics | None = None
    source_metrics: dict[str, SourceMetrics] = Field(default_factory=dict)

    # Errors
    errors: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)
