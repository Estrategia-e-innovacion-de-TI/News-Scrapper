"""Domain models for the News Radar pipeline.

Ported from news_radar_mvp/extractor/state.py and adapted to Pydantic v2
with model_config. These models define the core domain types used across
the pipeline: enums, DTOs for classification/scoring, source configuration,
queue items, documents, metrics, and the LangGraph state.

Validates: Requirements 1.1-1.5, 2.1-2.5, 5.1-5.4, 9.1-9.5, 10.1-10.5, 19.1-19.6
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ─────────────────────────────────────────────────────────────


class FetchMethod(str, Enum):
    """How a queue item should be fetched."""

    RSS = "rss"
    HTTP = "http"
    PLAYWRIGHT = "playwright"
    PDF = "pdf"


class ItemStatus(str, Enum):
    """Processing status of a queue item."""

    PENDING = "pending"
    OK = "ok"
    SKIPPED = "skipped"
    ERROR = "error"


class ErrorType(str, Enum):
    """Categorised error types for fetch/parse failures."""

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
    """Reasons a queue item may be skipped without error."""

    GATED_PAYWALL = "gated_paywall_known"
    CUSTOM_PENDING = "custom_pending"
    PLAYWRIGHT_DISABLED = "requires_playwright_but_disabled"
    NO_MATCHES = "no_matches_adhoc"


# ── Metadata DTOs (Req 4) ────────────────────────────────────────────


class MetadataResult(BaseModel):
    """Result of HTML metadata extraction.

    Validates: Requirements 4.1-4.5
    """

    model_config = ConfigDict(frozen=False)

    canonical_url: str | None = None
    title: str | None = None
    published_at: str | None = None
    author: str | None = None
    jsonld: dict[str, Any] | None = None



# ── Classification DTOs (Req 1) ──────────────────────────────────────


class ClassifyResult(BaseModel):
    """Result of document classification (rules or LLM).

    Validates: Requirements 1.1-1.5
    """

    model_config = ConfigDict(frozen=False)

    label: str
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    reason: str = ""
    matched_keywords: list[str] = Field(default_factory=list)


# ── Severity DTOs (Req 10) ───────────────────────────────────────────


class EvidenceSpanDTO(BaseModel):
    """Text fragment around a matched term with character offsets.

    Validates: Requirements 10.5, 11.1-11.5
    """

    model_config = ConfigDict(frozen=False)

    text: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    matched_term: str


class SeverityResult(BaseModel):
    """Result of severity scoring.

    Validates: Requirements 10.1-10.5
    """

    model_config = ConfigDict(frozen=False)

    severity: Literal["H", "M", "L"]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    evidence_spans: list[EvidenceSpanDTO] = Field(default_factory=list)


# ── Reranking DTOs (Req 2) ───────────────────────────────────────────


class RerankerResult(BaseModel):
    """Result of LLM re-ranking.

    Validates: Requirements 2.1-2.5
    """

    model_config = ConfigDict(frozen=False)

    relevance_score: int = Field(ge=0, le=100, description="Relevance 0-100")
    reasoning: str = ""
    geo_region: str = "Global"


# ── Pipeline Parameters (Req 19) ─────────────────────────────────────


class PipelineParams(BaseModel):
    """Parameters accepted by the pipeline run endpoint.

    Validates: Requirements 19.1-19.6
    """

    model_config = ConfigDict(frozen=False)

    catalog_path: str = "catalog.yaml"
    days: int = 7
    max_items_per_source: int = 20
    out_dir: str = "out"
    debug: bool = False
    dry_run: bool = False
    only_source: str | None = None
    no_playwright: bool = False
    focus: str | None = None
    adhoc: bool = False
    company: str | None = None
    terms: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    topk_per_source: int = 5
    max_candidates_total: int = 50
    candidates_path: str | None = None
    classifier_mode: Literal["rules", "llm"] = "rules"
    nit: str | None = None
    terms_preset: str | None = None


# ── Source Configuration (Req 5) ─────────────────────────────────────


class SourceConfig(BaseModel):
    """Parsed source configuration from the YAML catalog.

    Validates: Requirements 5.1-5.4
    """

    model_config = ConfigDict(frozen=False)

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
    # Merged defaults from catalog
    timeout_seconds: int = 25
    max_retries: int = 2
    rate_limit_rps: float = 1.0
    min_text_chars: int = 800


# ── Queue Item ────────────────────────────────────────────────────────


class QueueItem(BaseModel):
    """Item in the processing queue awaiting fetch/extraction."""

    model_config = ConfigDict(frozen=False)

    source_id: str
    url: str
    source_url: str  # feed / listing / pdf origin
    fetch_method: FetchMethod
    title: str | None = None
    published_at: str | None = None
    snippet: str | None = None
    requires_playwright: bool = False
    status: ItemStatus = ItemStatus.PENDING
    error_type: ErrorType | None = None
    error_msg: str | None = None
    skip_reason: SkipReason | None = None
    # Ad-hoc metadata match score (Req 16, 17)
    metadata_score: float = 0.0


# ── Document ──────────────────────────────────────────────────────────


class Document(BaseModel):
    """Extracted document ready for persistence.

    Validates: Requirements 1.2, 2.3, 9.1-9.5, 10.1-10.5, 19.5-19.6
    """

    model_config = ConfigDict(frozen=False)

    run_id: str
    source_id: str
    pipeline_class: str = "news"
    focus: list[str] = Field(default_factory=list)
    title: str
    url: str
    canonical_url: str | None = None
    published_at: str | None = None
    fetched_at: str
    language: str = "unknown"
    text: str
    excerpt: str = ""
    raw_len: int = 0
    text_len: int = 0
    text_capped: bool = False
    hash: str
    fetch_method: str
    status: str = "ok"
    error_type: str | None = None
    source_url: str = ""

    # Provenance for ad-hoc queries
    origin: str = "catalog"  # catalog | adhoc_query | search_ingest
    query_type: str | None = None  # aras | riesgos
    query_terms: list[str] = Field(default_factory=list)
    query_range: dict[str, str] = Field(default_factory=dict)

    # Classification (Req 1)
    category: str | None = None
    risk_type: str | None = None
    classifier_mode: str | None = None
    confidence: float | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    materialized_events: list[str] = Field(default_factory=list)

    # Severity (Req 10)
    severity: str | None = None
    severity_confidence: float | None = None
    evidence_spans: list[EvidenceSpanDTO] = Field(default_factory=list)

    # Relevance scoring (Req 9)
    relevance_score: int | None = None


# ── Metrics ───────────────────────────────────────────────────────────


class SourceMetrics(BaseModel):
    """Metrics for a single source within a pipeline run."""

    model_config = ConfigDict(frozen=False)

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
    # Ad-hoc specific
    matched_candidates: int = 0
    selected_candidates: int = 0
    # Classification counts
    classified_ok: int = 0
    classified_error: int = 0
    severity_h: int = 0
    severity_m: int = 0
    severity_l: int = 0


class RunMetrics(BaseModel):
    """Global metrics for a pipeline run.

    Validates: Requirements 19.6
    """

    model_config = ConfigDict(frozen=False)

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


# ── LangGraph State (Req 19) ─────────────────────────────────────────


class GraphState(BaseModel):
    """Main state object for the LangGraph pipeline.

    Validates: Requirements 19.1-19.6
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    # CLI / API params
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
    focus: str | None = None  # aras_news | riesgos_news | vigilancia_news
    adhoc: bool = False
    company: str | None = None  # ARAS
    terms: str | None = None  # Riesgos
    date_from: str | None = None
    date_to: str | None = None
    topk_per_source: int = 5
    max_candidates_total: int = 50
    match_mode: str = "metadata_only"

    # Classifier mode (Req 1)
    classifier_mode: str = "rules"  # "rules" | "llm"

    # NIT (Req 20)
    nit: str | None = None

    # Terms preset (Req 21)
    terms_preset: str | None = None

    # Candidates ingestion (from search)
    candidates_path: str | None = None

    # Text cap
    max_text_chars: int = 50_000

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
