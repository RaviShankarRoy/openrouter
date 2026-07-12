"""SQLAlchemy ORM models. Mapped to domain entities at the repository layer.

We deliberately keep ORM and domain models separate (Data Mapper pattern) so:
  - Domain stays pure Python
  - DB schema can evolve without breaking domain code
  - Alembic autogenerate works cleanly
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="users")


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    scope: Mapped[str] = mapped_column(String(20), default="personal")
    key_hash: Mapped[str] = mapped_column(String(200))  # argon2id encoded
    key_lookup: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # sha256 hex
    allowed_models: Mapped[list[str]] = mapped_column(JSON, default=list)
    denied_models: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CreditBalance(Base):
    __tablename__ = "credit_balances"

    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    available: Mapped[Decimal] = mapped_column(Numeric(precision=14, scale=6), default=0)
    reserved: Mapped[Decimal] = mapped_column(Numeric(precision=14, scale=6), default=0)
    monthly_cap: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=14, scale=6), nullable=True
    )
    daily_cap: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=14, scale=6), nullable=True
    )
    hard_stop: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    key_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL"), index=True
    )
    model: Mapped[str] = mapped_column(String(200), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(precision=14, scale=6))
    latency_ms: Mapped[int] = mapped_column(Integer)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    key_id: Mapped[UUID] = mapped_column(ForeignKey("api_keys.id", ondelete="SET NULL"))
    model: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    output_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(precision=14, scale=6), default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """DRD CO-007 — complete audit trail for admin operations."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    org_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[str] = mapped_column(String(200))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
