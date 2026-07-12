"""Billing & metering use cases (DRD Module 9)."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.uow import UnitOfWork
from app.domain.entities import UsageRecord
from app.domain.errors import InsufficientCredits
from app.domain.value_objects import ModelPricing, Money, TokenCounts


@dataclass(frozen=True)
class MeterUsageCommand:
    org_id: UUID
    key_id: UUID
    model: str
    provider: str
    tokens: TokenCounts
    pricing: ModelPricing
    latency_ms: int
    cache_hit: bool = False


class BillingService:
    """Cost calculation, credit deduction, usage record write-through."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def meter(self, cmd: MeterUsageCommand) -> UsageRecord:
        """Apply cost atomically. Credits are deducted via SQL UPDATE...RETURNING
        to prevent overspend on concurrent requests."""
        cost = cmd.pricing.cost(cmd.tokens) if not cmd.cache_hit else Money.zero()
        async with self._uow:
            if cost.amount > 0:
                ok = await self._uow.credits.deduct_atomic(cmd.org_id, cost)
                if not ok:
                    raise InsufficientCredits(
                        f"Could not deduct ${cost.amount} from org {cmd.org_id}"
                    )
            record = UsageRecord(
                org_id=cmd.org_id,
                key_id=cmd.key_id,
                model=cmd.model,
                provider=cmd.provider,
                tokens=cmd.tokens,
                cost=cost,
                latency_ms=cmd.latency_ms,
                cache_hit=cmd.cache_hit,
            )
            await self._uow.usage.add(record)
            await self._uow.commit()
        return record
