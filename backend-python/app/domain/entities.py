"""Domain entities. Identity-based equality (compared by ID, not by attributes).

Pydantic v2 models with `model_config = ConfigDict(frozen=False)` so methods
can mutate state. Validation happens at construction.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.errors import (
    BudgetExceeded,
    Forbidden,
    InsufficientCredits,
    InvalidApiKey,
)
from app.domain.value_objects import Money, TokenCounts


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    BILLING = "billing"


class KeyScope(str, Enum):
    PERSONAL = "personal"
    PROJECT = "project"
    TEAM = "team"
    ADMIN = "admin"
    BYOK = "byok"


class Organization(BaseModel):
    """Top of the tenancy tree."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: UUID = Field(default_factory=uuid4)
    name: str
    slug: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class User(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    email: str
    role: UserRole = UserRole.MEMBER
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class APIKey(BaseModel):
    """An API key issued to a user. The plaintext is shown once at creation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    user_id: UUID
    name: str
    scope: KeyScope = KeyScope.PERSONAL
    key_hash: str  # argon2id of plaintext
    key_lookup: str  # SHA-256 hex of plaintext for fast Redis lookup
    allowed_models: list[str] = Field(default_factory=list)
    denied_models: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def assert_usable(self) -> None:
        """Throws if the key is revoked, expired, or otherwise unusable."""
        if self.revoked_at is not None:
            raise InvalidApiKey("Key revoked")
        if self.expires_at and self.expires_at < datetime.now(UTC):
            raise InvalidApiKey("Key expired")

    def assert_model_allowed(self, model: str) -> None:
        """Enforce per-key allowlist/denylist (DRD AK-010)."""
        if self.denied_models and model in self.denied_models:
            raise Forbidden(f"Model {model} denied for this key")
        if self.allowed_models and model not in self.allowed_models:
            raise Forbidden(f"Model {model} not in key allowlist")


class CreditBalance(BaseModel):
    """Per-org credit balance. Atomic deductions happen at the repository layer
    via SQL UPDATE...RETURNING; this class enforces the business invariants."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    org_id: UUID
    available: Decimal = Decimal("0")
    reserved: Decimal = Decimal("0")
    monthly_cap: Decimal | None = None
    daily_cap: Decimal | None = None
    hard_stop: bool = True

    @property
    def usable(self) -> Money:
        return Money(self.available - self.reserved)

    def assert_can_spend(self, amount: Money) -> None:
        if self.usable.amount < amount.amount:
            if self.hard_stop:
                raise InsufficientCredits(
                    f"Need ${amount.amount} but only ${self.usable.amount} available"
                )
            raise BudgetExceeded("Soft cap reached")

    def reserve(self, amount: Money) -> Self:
        """Reserve before request to prevent overspend on concurrent requests."""
        self.assert_can_spend(amount)
        self.reserved += amount.amount
        return self

    def settle(self, reserved: Money, actual: Money) -> Self:
        """After request — release reservation, apply actual cost."""
        self.reserved -= reserved.amount
        self.available -= actual.amount
        return self


class UsageRecord(BaseModel):
    """Immutable record of one billed request (DRD §12.4)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    key_id: UUID
    model: str
    provider: str
    tokens: TokenCounts
    cost: Money
    latency_ms: int
    cache_hit: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VideoJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoJob(BaseModel):
    """Async video generation job (DRD §8.3)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    key_id: UUID
    model: str
    prompt: str
    status: VideoJobStatus = VideoJobStatus.PENDING
    output_urls: list[str] = Field(default_factory=list)
    cost: Money = Field(default_factory=Money.zero)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
