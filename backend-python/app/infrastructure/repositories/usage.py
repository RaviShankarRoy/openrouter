"""Usage record repository — append-only."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import UsageRecord
from app.domain.repositories import UsageRepository
from app.infrastructure import orm_models as orm


class SqlUsageRepository(UsageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: UsageRecord) -> None:
        row = orm.UsageRecord(
            id=record.id,
            org_id=record.org_id,
            key_id=record.key_id,
            model=record.model,
            provider=record.provider,
            input_tokens=record.tokens.input,
            output_tokens=record.tokens.output,
            cached_input_tokens=record.tokens.cached_input,
            reasoning_tokens=record.tokens.reasoning,
            cost_usd=record.cost.amount,
            latency_ms=record.latency_ms,
            cache_hit=record.cache_hit,
        )
        self._session.add(row)
        await self._session.flush()

    async def aggregate_for_period(
        self, org_id: UUID, start: str, end: str
    ) -> dict[str, float]:
        stmt = (
            select(
                func.sum(orm.UsageRecord.input_tokens).label("input_tokens"),
                func.sum(orm.UsageRecord.output_tokens).label("output_tokens"),
                func.sum(orm.UsageRecord.cost_usd).label("cost_usd"),
                func.count().label("requests"),
            )
            .where(orm.UsageRecord.org_id == org_id)
            .where(orm.UsageRecord.created_at >= start)
            .where(orm.UsageRecord.created_at < end)
        )
        row = (await self._session.execute(stmt)).one()
        return {
            "input_tokens": int(row.input_tokens or 0),
            "output_tokens": int(row.output_tokens or 0),
            "cost_usd": float(row.cost_usd or 0),
            "requests": int(row.requests or 0),
        }
