"""FastAPI application entry point.

Composition root: wires concrete adapters into use cases.
Single responsibility — assemble, run, shut down. No business logic.
"""
from __future__ import annotations

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app import __version__
from app.api.routes import register_routes
from app.api.middleware import register_middleware
from app.api.errors import register_exception_handlers
from app.service.routing.config import reload_routing_config
from app.shared.config import settings
from app.shared.logging import configure_logging, get_logger
from app.shared.tracing import init_tracing
from app.repository.database import init_db, close_db
from app.repository.redis_client import init_redis, close_redis
from app.repository.events.bus import init_event_bus, close_event_bus


_log = get_logger(__name__)


def _install_sighup_handler() -> bool:
    """Reload routing.yaml on SIGHUP without restarting the process.

    Mirrors the Go gateway's SIGHUP behaviour for providers.yaml so operators
    can add models to `openrouter/auto` with zero downtime. SIGHUP isn't
    available on Windows; we no-op there.
    """
    if not hasattr(signal, "SIGHUP"):
        return False

    def _handler() -> None:
        try:
            cfg = reload_routing_config()
            _log.info("routing_config_reloaded", pool_size=len(cfg.pool))
        except Exception as exc:  # noqa: BLE001 — log + keep serving old config
            _log.error("routing_config_reload_failed", error=str(exc))

    loop = asyncio.get_event_loop()
    try:
        loop.add_signal_handler(signal.SIGHUP, _handler)
    except NotImplementedError:
        # add_signal_handler isn't supported on every event loop (e.g. uvloop
        # on some Windows builds); fall back to the threadsafe signal API.
        signal.signal(signal.SIGHUP, lambda *_: _handler())
    return True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown — open connections, fail fast on bad config."""
    configure_logging(settings.environment, settings.log_level)
    init_tracing(settings)
    await init_db(settings)
    await init_redis(settings)
    await init_event_bus(settings)
    _install_sighup_handler()
    yield
    await close_event_bus()
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenRouter Backend",
        version=__version__,
        lifespan=lifespan,
        # OpenAPI is the source of truth — not generated from FastAPI.
        # We expose docs but the canonical spec lives in shared/openapi/.
        docs_url="/docs" if settings.environment != "prod" else None,
        redoc_url="/redoc" if settings.environment != "prod" else None,
    )
    # CORS for the dashboard (DRD SE-007).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_middleware(app)
    register_exception_handlers(app)
    register_routes(app)

    # Prometheus on the same process, separate path.
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
