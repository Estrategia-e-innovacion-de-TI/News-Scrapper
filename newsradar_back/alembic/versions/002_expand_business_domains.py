"""Expand business-domain persistence and auditability.

Revision ID: 002
Revises: 001
Create Date: 2026-03-31 12:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_key", sa.String(length=32), nullable=False),
        sa.Column("business_flow", sa.String(length=50), nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("source_scope", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="started"),
        sa.Column("window_months", sa.Integer(), nullable=True),
        sa.Column("config_hash", sa.String(length=64), nullable=True),
        sa.Column("config_json", JSONB, nullable=True),
        sa.Column("metrics_json", JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.UniqueConstraint("run_key"),
    )
    op.create_index("idx_executions_flow_status", "executions", ["business_flow", "status"])
    op.add_column("documents", sa.Column("execution_id", UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("business_flow", sa.String(length=50), nullable=True))
    op.add_column("documents", sa.Column("source_type", sa.String(length=40), nullable=True))
    op.add_column("documents", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("text_capped", sa.Boolean(), server_default="false", nullable=True))
    op.add_column("documents", sa.Column("query_terms", JSONB, nullable=True))
    op.add_column("documents", sa.Column("query_range", JSONB, nullable=True))
    op.add_column("documents", sa.Column("classifier_mode", sa.String(length=20), nullable=True))
    op.add_column("documents", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("documents", sa.Column("matched_keywords", JSONB, nullable=True))
    op.add_column("documents", sa.Column("materialized_events", JSONB, nullable=True))
    op.create_foreign_key(
        "fk_documents_execution_id",
        "documents",
        "executions",
        ["execution_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("subscriptions", sa.Column("subscriber_name", sa.String(length=200), nullable=True))

    op.create_table(
        "clusters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cluster_id", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("keywords", JSONB, nullable=True),
        sa.Column("item_count", sa.Integer(), server_default="0", nullable=True),
        sa.Column("impact_score", sa.Float(), server_default="0", nullable=True),
        sa.Column("horizon_score", sa.Float(), server_default="0", nullable=True),
        sa.Column("hull_polygon", JSONB, nullable=True),
        sa.Column("avg_score", sa.Float(), server_default="0", nullable=True),
        sa.Column("x_embed", sa.Float(), server_default="0", nullable=True),
        sa.Column("y_embed", sa.Float(), server_default="0", nullable=True),
        sa.Column("relevance", sa.String(length=10), server_default="media", nullable=True),
        sa.Column("cluster_kind", sa.String(length=50), nullable=True),
        sa.Column("business_flow", sa.String(length=50), nullable=True),
        sa.Column("snapshot_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cluster_id"),
    )
    op.create_table(
        "trends",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trend", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("momentum", sa.Float(), server_default="0", nullable=True),
        sa.Column("maturity_stage", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("impact_on_finance", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("group_id", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("term_count", sa.Integer(), server_default="0", nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id"),
    )
    op.create_table(
        "execution_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("execution_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("discovered", sa.Integer(), server_default="0", nullable=True),
        sa.Column("fetched_ok", sa.Integer(), server_default="0", nullable=True),
        sa.Column("text_ok", sa.Integer(), server_default="0", nullable=True),
        sa.Column("dupes", sa.Integer(), server_default="0", nullable=True),
        sa.Column("skipped", sa.Integer(), server_default="0", nullable=True),
        sa.Column("errors", sa.Integer(), server_default="0", nullable=True),
        sa.Column("classified_ok", sa.Integer(), server_default="0", nullable=True),
        sa.Column("classified_error", sa.Integer(), server_default="0", nullable=True),
        sa.Column("severity_h", sa.Integer(), server_default="0", nullable=True),
        sa.Column("severity_m", sa.Integer(), server_default="0", nullable=True),
        sa.Column("severity_l", sa.Integer(), server_default="0", nullable=True),
        sa.Column("matched_candidates", sa.Integer(), server_default="0", nullable=True),
        sa.Column("selected_candidates", sa.Integer(), server_default="0", nullable=True),
        sa.Column("avg_text_len", sa.Float(), server_default="0", nullable=True),
        sa.Column("errors_by_type", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("execution_id", "source_id", name="uq_execution_source"),
    )
    op.create_index("idx_execution_sources_source", "execution_sources", ["source_id"])
    op.create_index("idx_documents_flow_published", "documents", ["business_flow", "published_at"])
    op.create_index("idx_documents_query_type", "documents", ["query_type"])
    op.create_table(
        "document_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", UUID(as_uuid=True), nullable=True),
        sa.Column("score_type", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("model_id", sa.String(length=150), nullable=True),
        sa.Column("prompt_version", sa.String(length=60), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_document_scores_type", "document_scores", ["score_type"])
    op.create_table(
        "document_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("topic_type", sa.String(length=40), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_method", sa.String(length=40), nullable=True),
        sa.Column("cluster_ref", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_document_topics_type_value", "document_topics", ["topic_type", "value"])
    op.create_table(
        "report_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_key", sa.String(length=80), nullable=False),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("business_flow", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_months", sa.Integer(), nullable=True),
        sa.Column("source_execution_id", UUID(as_uuid=True), nullable=True),
        sa.Column("config_hash", sa.String(length=64), nullable=True),
        sa.Column("summary_json", JSONB, nullable=True),
        sa.Column("parameters_json", JSONB, nullable=True),
        sa.Column("data_json", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["source_execution_id"], ["executions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("snapshot_key"),
    )
    op.create_index("idx_report_snapshots_type_generated", "report_snapshots", ["report_type", "generated_at"])
    op.create_table(
        "trend_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_id", UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("top_topics_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["report_snapshots.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "risk_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_id", UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("dominant_risks_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["report_snapshots.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "subscription_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subscription_id", UUID(as_uuid=True), nullable=False),
        sa.Column("topic_key", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("subscription_id", "topic_key", name="uq_subscription_topic"),
    )
    op.create_table(
        "subscription_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subscription_id", UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("content_json", JSONB, nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "search_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("search_kind", sa.String(length=40), nullable=False),
        sa.Column("query_mode", sa.String(length=40), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("issuer", sa.String(length=255), nullable=True),
        sa.Column("nit", sa.String(length=80), nullable=True),
        sa.Column("term", sa.String(length=255), nullable=True),
        sa.Column("terms_json", JSONB, nullable=True),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("parameters_json", JSONB, nullable=True),
        sa.Column("results_json", JSONB, nullable=True),
        sa.Column("results_count", sa.Integer(), server_default="0", nullable=True),
        sa.Column("export_id", UUID(as_uuid=True), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
    )
    op.create_index("idx_search_audit_kind_requested", "search_audit", ["search_kind", "requested_at"])
    op.create_table(
        "exports_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("export_kind", sa.String(length=40), nullable=False),
        sa.Column("search_audit_id", UUID(as_uuid=True), nullable=True),
        sa.Column("execution_id", UUID(as_uuid=True), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="created"),
        sa.Column("row_count", sa.Integer(), server_default="0", nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["search_audit_id"], ["search_audit.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "llm_prompts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("prompt_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=60), nullable=False),
        sa.Column("model_id", sa.String(length=150), nullable=True),
        sa.Column("prompt_file", sa.String(length=255), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("content_json", JSONB, nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.UniqueConstraint("prompt_key", "version", name="uq_prompt_version"),
    )
    op.create_table(
        "flow_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("flow_name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=60), nullable=False),
        sa.Column("config_path", sa.String(length=255), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=True),
        sa.Column("config_json", JSONB, nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.UniqueConstraint("flow_name", "version", name="uq_flow_config_version"),
    )
    op.create_table(
        "source_catalog",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("business_flow", sa.String(length=50), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=True),
        sa.Column("config_path", sa.String(length=255), nullable=True),
        sa.Column("config_json", JSONB, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.UniqueConstraint("source_id"),
    )
    op.create_table(
        "job_status",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("job_group", sa.String(length=50), nullable=False),
        sa.Column("schedule", sa.String(length=100), nullable=True),
        sa.Column("last_status", sa.String(length=20), nullable=False, server_default="idle"),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_execution_id", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["last_execution_id"], ["executions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("job_name"),
    )


def downgrade() -> None:
    op.drop_table("job_status")
    op.drop_table("source_catalog")
    op.drop_table("flow_configs")
    op.drop_table("llm_prompts")
    op.drop_table("exports_audit")
    op.drop_index("idx_search_audit_kind_requested", table_name="search_audit")
    op.drop_table("search_audit")
    op.drop_table("subscription_deliveries")
    op.drop_table("subscription_topics")
    op.drop_table("risk_reports")
    op.drop_table("trend_reports")
    op.drop_index("idx_report_snapshots_type_generated", table_name="report_snapshots")
    op.drop_table("report_snapshots")
    op.drop_index("idx_document_topics_type_value", table_name="document_topics")
    op.drop_table("document_topics")
    op.drop_index("idx_document_scores_type", table_name="document_scores")
    op.drop_table("document_scores")
    op.drop_index("idx_documents_query_type", table_name="documents")
    op.drop_index("idx_documents_flow_published", table_name="documents")
    op.drop_constraint("fk_documents_execution_id", "documents", type_="foreignkey")
    op.drop_index("idx_execution_sources_source", table_name="execution_sources")
    op.drop_table("execution_sources")
    op.drop_index("idx_executions_flow_status", table_name="executions")
    op.drop_table("executions")
    op.drop_table("topics")
    op.drop_table("trends")
    op.drop_table("clusters")
    op.drop_column("subscriptions", "subscriber_name")
    op.drop_column("documents", "materialized_events")
    op.drop_column("documents", "matched_keywords")
    op.drop_column("documents", "confidence")
    op.drop_column("documents", "classifier_mode")
    op.drop_column("documents", "query_range")
    op.drop_column("documents", "query_terms")
    op.drop_column("documents", "text_capped")
    op.drop_column("documents", "source_url")
    op.drop_column("documents", "source_type")
    op.drop_column("documents", "business_flow")
    op.drop_column("documents", "execution_id")
