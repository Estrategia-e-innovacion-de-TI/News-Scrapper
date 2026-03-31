"""SQLAlchemy ORM models for News Radar.

The schema keeps legacy tables used by the current scaffold while adding the
canonical entities required for execution history, auditability, snapshots,
subscriptions, and worker orchestration.
"""
from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# Legacy compatibility tables -------------------------------------------------


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String(50), unique=True, nullable=False)
    label = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    summary = Column(Text, nullable=False, default="")
    keywords = Column(JSONB, default=list)
    item_count = Column(Integer, default=0)
    impact_score = Column(Float, default=0.0)
    horizon_score = Column(Float, default=0.0)
    hull_polygon = Column(JSONB, default=list)
    avg_score = Column(Float, default=0.0)
    x_embed = Column(Float, default=0.0)
    y_embed = Column(Float, default=0.0)
    relevance = Column(String(10), default="media")
    cluster_kind = Column(String(50), nullable=True)
    business_flow = Column(String(50), nullable=True)
    snapshot_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trend = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    direction = Column(String(20), nullable=False)
    momentum = Column(Float, default=0.0)
    maturity_stage = Column(String(50), nullable=False)
    description = Column(Text, nullable=False, default="")
    impact_on_finance = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    term_count = Column(Integer, default=0)


# Canonical execution and document tables ------------------------------------


class Execution(Base):
    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_key = Column(String(32), unique=True, nullable=False)
    business_flow = Column(String(50), nullable=False)
    trigger_type = Column(String(30), nullable=False, default="manual")
    source_scope = Column(String(30), nullable=True)
    status = Column(String(20), nullable=False, default="started")
    window_months = Column(Integer, nullable=True)
    config_hash = Column(String(64), nullable=True)
    config_json = Column(JSONB, nullable=True)
    metrics_json = Column(JSONB, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sources = relationship("ExecutionSource", back_populates="execution")
    documents = relationship("Document", back_populates="execution")

    __table_args__ = (
        Index("idx_executions_flow_status", "business_flow", "status"),
    )


class ExecutionSource(Base):
    __tablename__ = "execution_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id = Column(String(100), nullable=False)
    source_type = Column(String(40), nullable=True)
    status = Column(String(20), nullable=False, default="completed")
    discovered = Column(Integer, default=0)
    fetched_ok = Column(Integer, default=0)
    text_ok = Column(Integer, default=0)
    dupes = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    classified_ok = Column(Integer, default=0)
    classified_error = Column(Integer, default=0)
    severity_h = Column(Integer, default=0)
    severity_m = Column(Integer, default=0)
    severity_l = Column(Integer, default=0)
    matched_candidates = Column(Integer, default=0)
    selected_candidates = Column(Integer, default=0)
    avg_text_len = Column(Float, default=0.0)
    errors_by_type = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    execution = relationship("Execution", back_populates="sources")

    __table_args__ = (
        UniqueConstraint("execution_id", "source_id", name="uq_execution_source"),
        Index("idx_execution_sources_source", "source_id"),
    )


class Document(Base):
    """Documents extracted, enriched, and/or retrieved via ad-hoc search."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_id = Column(String(16), nullable=False)
    business_flow = Column(String(50), nullable=True)
    source_id = Column(String(100), nullable=False)
    source_type = Column(String(40), nullable=True)
    pipeline_class = Column(String(50), default="news")
    focus = Column(ARRAY(Text), default=list)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    language = Column(String(10), default="unknown")
    text = Column(Text, nullable=False)
    excerpt = Column(String(500), nullable=True)
    raw_len = Column(Integer, nullable=True)
    text_len = Column(Integer, nullable=True)
    text_capped = Column(Boolean, default=False)
    hash = Column(String(64), unique=True, nullable=False)
    fetch_method = Column(String(20), nullable=True)
    status = Column(String(20), default="ok")
    origin = Column(String(30), default="catalog")
    query_type = Column(String(20), nullable=True)
    query_terms = Column(JSONB, nullable=True)
    query_range = Column(JSONB, nullable=True)
    category = Column(String(60), nullable=True)
    risk_type = Column(String(60), nullable=True)
    classifier_mode = Column(String(20), nullable=True)
    confidence = Column(Float, nullable=True)
    matched_keywords = Column(JSONB, nullable=True)
    materialized_events = Column(JSONB, nullable=True)
    severity = Column(String(1), nullable=True)
    severity_confidence = Column(Float, nullable=True)
    relevance_score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    execution = relationship("Execution", back_populates="documents")
    evidence_spans = relationship(
        "EvidenceSpan", back_populates="document", cascade="all, delete-orphan"
    )
    scores = relationship(
        "DocumentScore", back_populates="document", cascade="all, delete-orphan"
    )
    topics = relationship(
        "DocumentTopic", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_documents_run", "run_id"),
        Index("idx_documents_source", "source_id"),
        Index("idx_documents_hash", "hash"),
        Index("idx_documents_flow_published", "business_flow", "published_at"),
        Index("idx_documents_query_type", "query_type"),
    )


class EvidenceSpan(Base):
    __tablename__ = "evidence_spans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    text = Column(Text, nullable=False)
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    matched_term = Column(String(200), nullable=False)

    document = relationship("Document", back_populates="evidence_spans")


class DocumentScore(Base):
    __tablename__ = "document_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    score_type = Column(String(40), nullable=False)
    score = Column(Float, nullable=False)
    model_id = Column(String(150), nullable=True)
    prompt_version = Column(String(60), nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="scores")

    __table_args__ = (
        Index("idx_document_scores_type", "score_type"),
    )


class DocumentTopic(Base):
    __tablename__ = "document_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_type = Column(String(40), nullable=False)
    value = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=True)
    source_method = Column(String(40), nullable=True)
    cluster_ref = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="topics")

    __table_args__ = (
        Index("idx_document_topics_type_value", "topic_type", "value"),
    )


# Legacy pipeline tables kept during migration --------------------------------


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    run_id = Column(String(16), primary_key=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    total_sources = Column(Integer, default=0)
    total_discovered = Column(Integer, default=0)
    total_fetched = Column(Integer, default=0)
    total_ok = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)
    total_dupes = Column(Integer, default=0)
    params_json = Column(JSONB, nullable=True)


class TrendmapSnapshot(Base):
    __tablename__ = "trendmap_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    data_json = Column(JSONB, nullable=False)
    meta_json = Column(JSONB, nullable=True)


# Canonical report/snapshot/audit tables --------------------------------------


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_key = Column(String(80), unique=True, nullable=False)
    report_type = Column(String(50), nullable=False)
    business_flow = Column(String(50), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="completed")
    generated_at = Column(DateTime(timezone=True), nullable=False)
    window_months = Column(Integer, nullable=True)
    source_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    config_hash = Column(String(64), nullable=True)
    summary_json = Column(JSONB, nullable=True)
    parameters_json = Column(JSONB, nullable=True)
    data_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_report_snapshots_type_generated", "report_type", "generated_at"),
    )


class TrendReport(Base):
    __tablename__ = "trend_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("report_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(255), nullable=False)
    summary_text = Column(Text, nullable=True)
    top_topics_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskReport(Base):
    __tablename__ = "risk_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("report_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(255), nullable=False)
    summary_text = Column(Text, nullable=True)
    dominant_risks_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscriber_email = Column(String(200), nullable=False)
    subscriber_name = Column(String(200), nullable=True)
    query_groups = Column(ARRAY(Text), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    topics = relationship(
        "SubscriptionTopic", back_populates="subscription", cascade="all, delete-orphan"
    )
    deliveries = relationship(
        "SubscriptionDelivery",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )


class SubscriptionTopic(Base):
    __tablename__ = "subscription_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_key = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscription = relationship("Subscription", back_populates="topics")

    __table_args__ = (
        UniqueConstraint("subscription_id", "topic_key", name="uq_subscription_topic"),
    )


class SubscriptionDelivery(Base):
    __tablename__ = "subscription_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(20), nullable=False, default="pending")
    subject = Column(String(255), nullable=True)
    content_json = Column(JSONB, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscription = relationship("Subscription", back_populates="deliveries")


class SearchAudit(Base):
    __tablename__ = "search_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_kind = Column(String(40), nullable=False)
    query_mode = Column(String(40), nullable=False)
    company = Column(String(255), nullable=True)
    issuer = Column(String(255), nullable=True)
    nit = Column(String(80), nullable=True)
    term = Column(String(255), nullable=True)
    terms_json = Column(JSONB, nullable=True)
    date_from = Column(Date, nullable=True)
    date_to = Column(Date, nullable=True)
    parameters_json = Column(JSONB, nullable=True)
    results_json = Column(JSONB, nullable=True)
    results_count = Column(Integer, default=0)
    export_id = Column(UUID(as_uuid=True), nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_search_audit_kind_requested", "search_kind", "requested_at"),
    )


class ExportAudit(Base):
    __tablename__ = "exports_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_kind = Column(String(40), nullable=False)
    search_audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("search_audit.id", ondelete="SET NULL"),
        nullable=True,
    )
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="created")
    row_count = Column(Integer, default=0)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMPrompt(Base):
    __tablename__ = "llm_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_key = Column(String(100), nullable=False)
    version = Column(String(60), nullable=False)
    model_id = Column(String(150), nullable=True)
    prompt_file = Column(String(255), nullable=False)
    prompt_hash = Column(String(64), nullable=True)
    content_json = Column(JSONB, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("prompt_key", "version", name="uq_prompt_version"),
    )


class FlowConfig(Base):
    __tablename__ = "flow_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_name = Column(String(100), nullable=False)
    version = Column(String(60), nullable=False)
    config_path = Column(String(255), nullable=False)
    config_hash = Column(String(64), nullable=True)
    config_json = Column(JSONB, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("flow_name", "version", name="uq_flow_config_version"),
    )


class SourceCatalogEntry(Base):
    __tablename__ = "source_catalog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    business_flow = Column(String(50), nullable=True)
    source_type = Column(String(40), nullable=True)
    enabled = Column(Boolean, default=True)
    config_path = Column(String(255), nullable=True)
    config_json = Column(JSONB, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class JobStatus(Base):
    __tablename__ = "job_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String(100), unique=True, nullable=False)
    job_group = Column(String(50), nullable=False)
    schedule = Column(String(100), nullable=True)
    last_status = Column(String(20), nullable=False, default="idle")
    last_started_at = Column(DateTime(timezone=True), nullable=True)
    last_finished_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    last_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

