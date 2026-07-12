"""Verify the scenario engine — latency injection, error rates, control plane."""

from __future__ import annotations

import time

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_force_status_429(client: AsyncClient) -> None:
    """RL-006 — force_status lets a test deterministically trigger 429."""
    r = await client.post(
        "/control/scenario",
        json={"provider": "openai", "route": "chat", "force_status": 429},
    )
    assert r.status_code == 200

    r = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 429
    assert r.headers.get("retry-after") == "1"


@pytest.mark.asyncio
async def test_force_status_503_then_clears(client: AsyncClient) -> None:
    """LB-003 — one-shot 503, the next call succeeds (force_status is consumed)."""
    await client.post(
        "/control/scenario",
        json={"provider": "openai", "route": "chat", "force_status": 503},
    )
    bad = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]},
    )
    assert bad.status_code == 503

    good = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]},
    )
    assert good.status_code == 200


@pytest.mark.asyncio
async def test_latency_override_is_applied(client: AsyncClient) -> None:
    """NFR-002 — latency override actually sleeps before responding."""
    await client.post(
        "/control/scenario",
        json={"provider": "openai", "route": "chat", "latency_ms": 200},
    )
    t0 = time.perf_counter()
    r = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]},
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert r.status_code == 200
    # Allow generous slack — CI runners are slow; we only need to prove sleep happened.
    assert elapsed_ms >= 100


@pytest.mark.asyncio
async def test_stats_counters_increment(client: AsyncClient) -> None:
    await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]},
    )
    stats = (await client.get("/control/stats")).json()
    assert stats["requests"] >= 1


@pytest.mark.asyncio
async def test_snapshot_round_trip(client: AsyncClient) -> None:
    payload = {
        "key": "abc123",
        "response": {"hello": "world"},
        "status_code": 200,
    }
    add = await client.post("/control/snapshots", json=payload)
    assert add.status_code == 200

    got = await client.get("/control/snapshots/abc123")
    assert got.status_code == 200
    assert got.json()["response"] == {"hello": "world"}


@pytest.mark.asyncio
async def test_reset_clears_state(client: AsyncClient) -> None:
    await client.post(
        "/control/scenario",
        json={"provider": "openai", "route": "chat", "latency_ms": 500},
    )
    await client.post("/control/reset")
    stats = (await client.get("/control/stats")).json()
    assert stats["overrides"] == {}
