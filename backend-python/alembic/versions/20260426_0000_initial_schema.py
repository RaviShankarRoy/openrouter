"""initial schema

Revision ID: 20260426_0000
Revises:
Create Date: 2026-04-26 00:00:00

Creates every table referenced by app.infrastructure.orm_models, plus:
  - pgvector extension (semantic cache, DRD §13.4)
  - model_pricing table (DRD MK-010, BL-011)
  - audit_logs table (DRD CO-007)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# revision identifiers
revision = "20260426_0000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions required by Phase-3 features. IF NOT EXISTS keeps reruns safe.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "organizations",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "api_keys",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False, server_default="personal"),
        sa.Column("key_hash", sa.String(200), nullable=False),
        sa.Column("key_lookup", sa.String(64), nullable=False, unique=True),
        sa.Column("allowed_models", JSONB, nullable=False, server_default="[]"),
        sa.Column("denied_models", JSONB, nullable=False, server_default="[]"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_api_keys_key_lookup", "api_keys", ["key_lookup"])
    op.create_index("ix_api_keys_org_id", "api_keys", ["org_id"])

    op.create_table(
        "credit_balances",
        sa.Column(
            "org_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("available", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("monthly_cap", sa.Numeric(14, 6), nullable=True),
        sa.Column("daily_cap", sa.Numeric(14, 6), nullable=True),
        sa.Column("hard_stop", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "usage_records",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "key_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cached_input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reasoning_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("cache_hit", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_usage_records_org_id", "usage_records", ["org_id"])
    op.create_index("ix_usage_records_key_id", "usage_records", ["key_id"])
    op.create_index("ix_usage_records_model", "usage_records", ["model"])
    op.create_index("ix_usage_records_provider", "usage_records", ["provider"])
    op.create_index("ix_usage_records_created_at", "usage_records", ["created_at"])

    op.create_table(
        "video_jobs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "key_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("output_urls", JSONB, nullable=False, server_default="[]"),
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_video_jobs_status", "video_jobs", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(200), nullable=False),
        sa.Column("metadata_json", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_org_id", "audit_logs", ["org_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "model_pricing",
        sa.Column("model_key", sa.String(200), primary_key=True),  # "provider/model"
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("input_per_million", sa.Numeric(14, 6), nullable=False),
        sa.Column("output_per_million", sa.Numeric(14, 6), nullable=False),
        sa.Column("cached_input_per_million", sa.Numeric(14, 6), nullable=True),
        sa.Column("reasoning_per_million", sa.Numeric(14, 6), nullable=True),
        sa.Column("context_window", sa.Integer, nullable=True),
        sa.Column("modalities", JSONB, nullable=False, server_default="[]"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_model_pricing_provider", "model_pricing", ["provider"])
    op.create_index("ix_model_pricing_active", "model_pricing", ["active"])


def downgrade() -> None:
    # Forward-only in prod (per ARCHITECTURE.md §2.6); downgrade exists for dev only.
    for tbl in (
        "model_pricing",
        "audit_logs",
        "video_jobs",
        "usage_records",
        "credit_balances",
        "api_keys",
        "users",
        "organizations",
    ):
        op.drop_table(tbl)
