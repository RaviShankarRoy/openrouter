"""NATS JetStream event bus.

Pattern: Publisher/Subscriber. The Go gateway publishes UsageEvent on
'gateway.usage'; this backend subscribes via the metering worker.
"""
from __future__ import annotations

import nats
from nats.aio.client import Client as NATS
from nats.js.errors import NotFoundError

from app.shared.config import Settings

_nc: NATS | None = None


async def init_event_bus(settings: Settings) -> None:
    """Connect to NATS and ensure the stream exists. Idempotent.

    The kwargs form (rather than passing a StreamConfig object) avoids
    enum-serialization mismatches across nats-py versions and lets the
    server fill defaults for storage/retention.
    """
    global _nc  # noqa: PLW0603
    _nc = await nats.connect(servers=[settings.nats_url])
    js = _nc.jetstream()
    try:
        await js.stream_info(settings.nats_stream)
    except NotFoundError:
        await js.add_stream(
            name=settings.nats_stream,
            subjects=["gateway.>"],
            max_age=86_400,  # seconds; nats-py converts to ns server-side
        )


async def close_event_bus() -> None:
    if _nc is not None:
        await _nc.drain()


def get_nats() -> NATS:
    if _nc is None:
        raise RuntimeError("Event bus not initialized — call init_event_bus() first")
    return _nc


async def publish(subject: str, payload: bytes) -> None:
    """Fire-and-forget publish. Caller is responsible for serialization."""
    js = get_nats().jetstream()
    await js.publish(subject, payload)
