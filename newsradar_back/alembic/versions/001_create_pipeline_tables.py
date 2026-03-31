"""Create pipeline tables: documents, evidence_spans, pipeline_runs, trendmap_snapshots, subscriptions.

Revision ID: 001
Revises: None
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- documents --
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.String(16), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("pipeline_class", sa.String(50), server_default="news"),
        sa.Column("focus", ARRAY(sa.Text), server_default="{}"),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("canonical_url", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(10), server_default="unknown"),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("excerpt", sa.String(500), nullable=True),
        sa.Column("raw_len", sa.Integer, nullable=True),
        sa.Column("text_len", sa.Integer, nullable=True),
        sa.Column("hash", sa.String(64), unique=True, nullable=False),
        sa.Column("fetch_method", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), server_default="ok"),
        sa.Column("origin", sa.String(30), server_default="catalog"),
        sa.Column("query_type", sa.String(20), nullable=True),
        sa.Column("category", sa.String(60), nullable=True),
        sa.Column("risk_type", sa.String(60), nullable=True),
        sa.Column("severity", sa.String(1), nullable=True),
        sa.Column("severity_confidence", sa.Float, nullable=True),
        sa.Column("relevance_score", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_documents_run", "documents", ["run_id"])
    op.create_index("idx_documents_source", "documents", ["source_id"])
    op.create_index("idx_documents_hash", "documents", ["hash"])

    # -- evidence_spans --
    op.create_table(
        "evidence_spans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("start_offset", sa.Integer, nullable=False),
        sa.Column("end_offset", sa.Integer, nullable=False),
        sa.Column("matched_term", sa.String(200), nullable=False),
    )

    # -- pipeline_runs --
    op.create_table(
        "pipeline_runs",
        sa.Column("run_id", sa.String(16), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("total_sources", sa.Integer, server_default="0"),
        sa.Column("total_discovered", sa.Integer, server_default="0"),
        sa.Column("total_fetched", sa.Integer, server_default="0"),
        sa.Column("total_ok", sa.Integer, server_default="0"),
        sa.Column("total_errors", sa.Integer, server_default="0"),
        sa.Column("total_dupes", sa.Integer, server_default="0"),
        sa.Column("params_json", JSONB, nullable=True),
    )

    # -- trendmap_snapshots --
    op.create_table(
        "trendmap_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_json", JSONB, nullable=False),
        sa.Column("meta_json", JSONB, nullable=True),
    )

    # -- subscriptions --
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subscriber_email", sa.String(200), nullable=False),
        sa.Column("query_groups", ARRAY(sa.Text), nullable=False),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("trendmap_snapshots")
    op.drop_table("pipeline_runs")
    op.drop_table("evidence_spans")
    op.drop_index("idx_documents_hash", table_name="documents")
    op.drop_index("idx_documents_source", table_name="documents")
    op.drop_index("idx_documents_run", table_name="documents")
    op.drop_table("documents")
