"""Model pricing — DB source of truth, Redis-cached with 60s TTL.

Cache-aside pattern. Misses fall through to Postgres; writes invalidate by
key (Phase 2 wires invalidation to model_pricing CRUD endpoints).
"""
from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import text

from app.domain.value_objects import ModelPricing
from app.infrastructure.database import get_session_factory
from app.infrastructure.redis_client import get_redis

_CACHE_NS = "pricing:"
_CACHE_TTL_S = 60


class PricingRepository:
    """Read pricing for a `provider/model` key. Both cache and DB are awaited."""

    async def get(self, model_key: str) -> ModelPricing | None:
        cached = await self._cache_get(model_key)
        if cached is not None:
            return cached
        loaded = await self._db_get(model_key)
        if loaded is not None:
            await self._cache_set(model_key, loaded)
        return loaded

    @staticmethod
    async def _cache_get(model_key: str) -> ModelPricing | None:
        raw = await get_redis().get(_CACHE_NS + model_key)
        if raw is None:
            return None
        data = json.loads(raw)
        return ModelPricing(
            input_per_million=Decimal(data["input_per_million"]),
            output_per_million=Decimal(data["output_per_million"]),
            cached_input_per_million=(
                Decimal(data["cached_input_per_million"])
                if data.get("cached_input_per_million") is not None
                else None
            ),
            reasoning_per_million=(
                Decimal(data["reasoning_per_million"])
                if data.get("reasoning_per_million") is not None
                else None
            ),
        )

    @staticmethod
    async def _cache_set(model_key: str, pricing: ModelPricing) -> None:
        body = {
            "input_per_million": str(pricing.input_per_million),
            "output_per_million": str(pricing.output_per_million),
            "cached_input_per_million": (
                str(pricing.cached_input_per_million)
                if pricing.cached_input_per_million is not None
                else None
            ),
            "reasoning_per_million": (
                str(pricing.reasoning_per_million)
                if pricing.reasoning_per_million is not None
                else None
            ),
        }
        await get_redis().set(_CACHE_NS + model_key, json.dumps(body).encode(), ex=_CACHE_TTL_S)

    @staticmethod
    async def _db_get(model_key: str) -> ModelPricing | None:
        factory = get_session_factory()
        async with factory() as session:
            stmt = text(
                """
                SELECT input_per_million, output_per_million,
                       cached_input_per_million, reasoning_per_million
                FROM model_pricing
                WHERE model_key = :model_key AND active = true
                """
            )
            row = (await session.execute(stmt, {"model_key": model_key})).one_or_none()
            if row is None:
                return None
            return ModelPricing(
                input_per_million=Decimal(row.input_per_million),
                output_per_million=Decimal(row.output_per_million),
                cached_input_per_million=(
                    Decimal(row.cached_input_per_million)
                    if row.cached_input_per_million is not None
                    else None
                ),
                reasoning_per_million=(
                    Decimal(row.reasoning_per_million)
                    if row.reasoning_per_million is not None
                    else None
                ),
            )

    async def invalidate(self, model_key: str) -> None:
        await get_redis().delete(_CACHE_NS + model_key)
