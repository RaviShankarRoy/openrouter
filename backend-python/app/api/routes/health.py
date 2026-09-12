"""Health and readiness probes.

/health  — liveness; lightweight, never depends on downstreams (k8s liveness).
/ready   — readiness; pings every critical dependency (k8s readiness gate).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app import __version__
from app.shared.logging import get_logger
from app.repository.database import get_session_factory
from app.repository.redis_client import get_redis

router = APIRouter()
_log = get_logger(__name__)


class DependencyStatus(BaseModel):
    status: str
    latency_ms: int


class HealthResponse(BaseModel):
    status: str
    version: str
    dependencies: dict[str, DependencyStatus] = {}


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="healthy", version=__version__)


@router.get("/ready", response_model=HealthResponse)
async def ready(response: Response) -> HealthResponse:
    deps: dict[str, DependencyStatus] = {}
    overall = "healthy"

    deps["postgres"] = await _check_postgres()
    deps["redis"] = await _check_redis()

    if any(d.status != "healthy" for d in deps.values()):
        overall = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status=overall, version=__version__, dependencies=deps)


async def _check_postgres() -> DependencyStatus:
    start = time.perf_counter()
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return DependencyStatus(status="healthy", latency_ms=_elapsed(start))
    except Exception as exc:  # noqa: BLE001 — health probe must not raise
        _log.warning("postgres_health_failed", error=str(exc))
        return DependencyStatus(status="unhealthy", latency_ms=_elapsed(start))


async def _check_redis() -> DependencyStatus:
    start = time.perf_counter()
    try:
        await get_redis().ping()
        return DependencyStatus(status="healthy", latency_ms=_elapsed(start))
    except Exception as exc:  # noqa: BLE001
        _log.warning("redis_health_failed", error=str(exc))
        return DependencyStatus(status="unhealthy", latency_ms=_elapsed(start))


def _elapsed(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)
