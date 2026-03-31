"""SQLAlchemy ORM models for News Radar."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

import uuid


class Base(DeclarativeBase):
    pass


# ── Existing tables (unchanged) ──


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String(50), unique=True, nullable=False)
    label = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    summary = Column(Text, nullable=False, default="")
    keywords = Column(JSON, default=list)
    item_count = Column(Integer, default=0)
    impact_score = Column(Float, default=0.0)
    horizon_score = Column(Float, default=0.0)
    hull_polygon = Column(JSON, default=list)
    avg_score = Column(Float, default=0.0)
    x_embed = Column(Float, default=0.0)
    y_embed = Column(Float, default=0.0)
    relevance = Column(String(10), default="media")
    created_at = Column(DateTime, default=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    term_count = Column(Integer, default=0)


# ── New tables from full-pipeline-port spec ──


class Document(Base):
    """Documentos extraídos y clasificados por el pipeline."""

    __tablename__ = "documents"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id = Column(String(16), nullable=False)
    source_id = Column(String(100), nullable=False)
    pipeline_class = Column(String(50), default="news")
    focus = Column(ARRAY(Text), default=list)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    language = Column(String(10), default="unknown")
    text = Column(Text, nullable=False)
    excerpt = Column(String(500), nullable=True)
    raw_len = Column(Integer, nullable=True)
    text_len = Column(Integer, nullable=True)
    hash = Column(String(64), unique=True, nullable=False)
    fetch_method = Column(String(20), nullable=True)
    status = Column(String(20), default="ok")
    origin = Column(String(30), default="catalog")
    query_type = Column(String(20), nullable=True)
    category = Column(String(60), nullable=True)
    risk_type = Column(String(60), nullable=True)
    severity = Column(String(1), nullable=True)
    severity_confidence = Column(Float, nullable=True)
    relevance_score = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    evidence_spans = relationship(
        "EvidenceSpan", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_documents_run", "run_id"),
        Index("idx_documents_source", "source_id"),
        Index("idx_documents_hash", "hash"),
    )


class EvidenceSpan(Base):
    """Evidence spans asociados a documentos."""

    __tablename__ = "evidence_spans"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
    )
    text = Column(Text, nullable=False)
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    matched_term = Column(String(200), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="evidence_spans")


class PipelineRun(Base):
    """Métricas de ejecución del pipeline."""

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
    """Datos de trendmap generados."""

    __tablename__ = "trendmap_snapshots"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generated_at = Column(DateTime(timezone=True), nullable=False)
    data_json = Column(JSONB, nullable=False)
    meta_json = Column(JSONB, nullable=True)


class Subscription(Base):
    """Suscripciones de vigilancia."""

    __tablename__ = "subscriptions"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subscriber_email = Column(String(200), nullable=False)
    query_groups = Column(ARRAY(Text), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )
