"""Inject 429/500/503 responses based on configured rates.

Why one module: the gateway's circuit breaker (LB-003) and backoff (RL-006) need
predictable, configurable failure injection — not ad-hoc per-provider hacks.
"""

from __future__ import annotations

import random
from typing import Literal

from fastapi import HTTPException

from src.scenarios import engine

ErrorKind = Literal["rate_limit", "server_error", "service_unavailable"]


def _make_openai_error(message: str, code: str, http_status: int) -> HTTPException:
    """OpenAI-shaped error envelope — matches what the real API returns."""
    return HTTPException(
        status_code=http_status,
        detail={
            "error": {
                "message": message,
                "type": code,
                "param": None,
                "code": code,
            }
        },
        headers={"Retry-After": "1"} if http_status == 429 else None,
    )


def maybe_inject_error(provider: str, route: str) -> None:
    """Raise an HTTPException if the configured rates trigger.

    Honors `force_status` first (deterministic), then probability-based
    rate_limit_rate (RL-006), then error_rate (LB-003). Order matters: tests
    that set both probabilities should still see rate-limit behavior tested
    independently.
    """
    forced = engine.take_force_status(provider, route)
    if forced is not None:
        if forced == 429:
            engine.record(latency_ms=0.0, rate_limit=True)
            raise _make_openai_error("Rate limit exceeded (forced)", "rate_limit_exceeded", 429)
        if forced >= 500:
            engine.record(latency_ms=0.0, error=True)
            raise _make_openai_error("Forced server error", "server_error", forced)

    if random.random() < engine.rate_limit_rate(provider, route):  # noqa: S311
        engine.record(latency_ms=0.0, rate_limit=True)
        raise _make_openai_error(
            "Rate limit reached for requests",
            "rate_limit_exceeded",
            429,
        )

    if random.random() < engine.error_rate(provider, route):  # noqa: S311
        # Mix 500 and 503 50/50 so circuit-breaker tests see both shapes.
        status = 503 if random.random() < 0.5 else 500  # noqa: S311
        engine.record(latency_ms=0.0, error=True)
        raise _make_openai_error(
            "The server had an error processing your request",
            "server_error",
            status,
        )
