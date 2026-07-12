"""BillingService unit tests with in-memory repos."""
from __future__ import annotations

from decimal import Decimal
from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

import pytest

from app.application.services.billing_service import BillingService, MeterUsageCommand
from app.application.uow import UnitOfWork
from app.domain.entities import CreditBalance, UsageRecord
from app.domain.errors import InsufficientCredits
from app.domain.repositories import CreditRepository, UsageRepository
from app.domain.value_objects import ModelPricing, Money, TokenCounts


class _InMemCreditRepo(CreditRepository):
    def __init__(self, available: Decimal) -> None:
        self._balances: dict[UUID, CreditBalance] = {}
        self._default = available

    async def get_for_update(self, org_id: UUID) -> CreditBalance:
        return self._balances.setdefault(
            org_id, CreditBalance(org_id=org_id, available=self._default)
        )

    async def update(self, balance: CreditBalance) -> None:
        self._balances[balance.org_id] = balance

    async def deduct_atomic(self, org_id: UUID, amount: Money) -> bool:
        bal = await self.get_for_update(org_id)
        if bal.available < amount.amount:
            return False
        bal.available -= amount.amount
        return True


class _InMemUsageRepo(UsageRepository):
    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    async def add(self, record: UsageRecord) -> None:
        self.records.append(record)

    async def aggregate_for_period(
        self, org_id: UUID, start: str, end: str
    ) -> dict[str, float]:
        return {}


class _UoW(UnitOfWork):
    def __init__(self, credit_balance: Decimal) -> None:
        self.credits = _InMemCreditRepo(credit_balance)
        self.usage = _InMemUsageRepo()
        self.api_keys = None  # type: ignore[assignment]
        self.users = None  # type: ignore[assignment]
        self.organizations = None  # type: ignore[assignment]
        self.video_jobs = None  # type: ignore[assignment]
        self.commits = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


@pytest.mark.asyncio
async def test_meter_deducts_and_records() -> None:
    uow = _UoW(credit_balance=Decimal("100"))
    svc = BillingService(uow)
    cmd = MeterUsageCommand(
        org_id=uuid4(),
        key_id=uuid4(),
        model="gpt-4o-mini",
        provider="openai",
        tokens=TokenCounts(input=1_000_000, output=1_000_000),
        pricing=ModelPricing(
            input_per_million=Decimal("0.15"), output_per_million=Decimal("0.60")
        ),
        latency_ms=42,
    )
    record = await svc.meter(cmd)
    assert record.cost.amount == Decimal("0.75")
    assert len(uow.usage.records) == 1
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_meter_raises_on_insufficient_credits() -> None:
    uow = _UoW(credit_balance=Decimal("0.01"))
    svc = BillingService(uow)
    cmd = MeterUsageCommand(
        org_id=uuid4(),
        key_id=uuid4(),
        model="claude-opus-4-20250514",
        provider="anthropic",
        tokens=TokenCounts(input=1_000_000, output=1_000_000),
        pricing=ModelPricing(
            input_per_million=Decimal("15"), output_per_million=Decimal("75")
        ),
        latency_ms=10,
    )
    with pytest.raises(InsufficientCredits):
        await svc.meter(cmd)


@pytest.mark.asyncio
async def test_cache_hit_costs_zero() -> None:
    uow = _UoW(credit_balance=Decimal("100"))
    svc = BillingService(uow)
    cmd = MeterUsageCommand(
        org_id=uuid4(),
        key_id=uuid4(),
        model="gpt-4o",
        provider="openai",
        tokens=TokenCounts(input=1000, output=1000),
        pricing=ModelPricing(
            input_per_million=Decimal("2.50"), output_per_million=Decimal("10")
        ),
        latency_ms=2,
        cache_hit=True,
    )
    record = await svc.meter(cmd)
    assert record.cost.amount == Decimal("0")
    assert record.cache_hit is True
