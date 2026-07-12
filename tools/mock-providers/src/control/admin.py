"""Control-plane HTTP routes — mutate scenarios at runtime, expose stats.

Tests POST to `/control/scenario` to inject behavior, then GET `/control/stats`
to assert that the gateway behaved correctly. Snapshots (replay test fixtures)
live alongside in `src/control/snapshots.py`.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.control.snapshots import SnapshotStore
from src.scenarios import engine

router = APIRouter()
snapshots = SnapshotStore()


class ScenarioRequest(BaseModel):
    """Set or override a scenario for a (provider, route) pair.

    `provider` is the logical gateway provider — `openai|anthropic|google` for
    native APIs, or one of the OpenAI-compatible aggregators
    (`together|fireworks|ollama`). `route` is the logical name used by the
    provider mock (e.g. `chat`, `embeddings`, `messages`, `generateContent`,
    `images`).
    """

    provider: Literal["openai", "anthropic", "google", "together", "fireworks", "ollama"]
    route: str = Field(..., examples=["chat", "embeddings", "messages"])
    latency_ms: float | None = Field(default=None, ge=0)
    error_rate: float | None = Field(default=None, ge=0, le=1)
    rate_limit_rate: float | None = Field(default=None, ge=0, le=1)
    stream_chunk_delay_ms: float | None = Field(default=None, ge=0)
    force_status: int | None = Field(
        default=None,
        description="One-shot forced HTTP status for the next call (e.g. 429, 500, 503).",
    )


@router.post("/scenario", summary="Set a runtime scenario override (DRD §23.2)")
async def set_scenario(req: ScenarioRequest) -> dict[str, object]:
    payload = req.model_dump(exclude_none=True)
    payload.pop("provider", None)
    payload.pop("route", None)
    state = engine.set(req.provider, req.route, **payload)
    return {"ok": True, "state": vars(state)}


@router.post("/reset", summary="Clear all overrides + stats")
async def reset() -> dict[str, bool]:
    engine.reset()
    snapshots.clear()
    return {"ok": True}


@router.get("/stats", summary="Inspect current scenario state and counters")
async def get_stats() -> dict[str, object]:
    return engine.stats()


# ---------------- snapshot replay ---------------------------------------------


class SnapshotEntry(BaseModel):
    """A captured (request, response) pair for replay tests."""

    key: str = Field(..., description="Stable identifier — usually a hash of the request.")
    response: dict[str, object]
    status_code: int = 200


@router.post("/snapshots", summary="Capture a response for later replay")
async def add_snapshot(entry: SnapshotEntry) -> dict[str, bool]:
    snapshots.add(entry.key, entry.response, entry.status_code)
    return {"ok": True}


@router.get("/snapshots/{key}", summary="Fetch a previously captured snapshot")
async def get_snapshot(key: str) -> dict[str, object]:
    snap = snapshots.get(key)
    if snap is None:
        raise HTTPException(status_code=404, detail={"error": {"message": "snapshot not found"}})
    return {"key": key, "response": snap.response, "status_code": snap.status_code}
