"""Inject latency. Async sleep so we never block the event loop."""

from __future__ import annotations

import asyncio
import random


async def sleep_with_jitter(base_ms: float, jitter_ratio: float = 0.2) -> float:
    """Sleep base_ms ± jitter. Returns the actual ms slept (for stats).

    Real providers have jitter; reproducing it keeps p99 measurements honest.
    """
    if base_ms <= 0:
        return 0.0
    jitter = base_ms * jitter_ratio
    actual = max(0.0, base_ms + random.uniform(-jitter, jitter))  # noqa: S311 — not crypto
    await asyncio.sleep(actual / 1000.0)
    return actual
