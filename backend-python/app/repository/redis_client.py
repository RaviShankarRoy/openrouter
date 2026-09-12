"""Redis connection pool. Single shared client with hiredis parser."""
from __future__ import annotations

from redis.asyncio import Redis

from app.shared.config import Settings

_client: Redis | None = None


async def init_redis(settings: Settings) -> None:
    global _client  # noqa: PLW0603
    _client = Redis.from_url(
        settings.redis_url,
        max_connections=settings.redis_pool_size,
        decode_responses=False,  # raw bytes; callers decode as needed
    )
    await _client.ping()


async def close_redis() -> None:
    if _client is not None:
        await _client.aclose()


def get_redis() -> Redis:
    if _client is None:
        raise RuntimeError("Redis not initialized — call init_redis() first")
    return _client
