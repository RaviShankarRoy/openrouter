"""FastAPI entry point — wires providers and the control plane together."""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI

from src.config import settings
from src.control.admin import router as admin_router
from src.providers.anthropic_mock import router as anthropic_router
from src.providers.google_mock import router as google_router
from src.providers.openai_mock import router as openai_router

logger = logging.getLogger("mock-providers")


def create_app() -> FastAPI:
    """App factory — keeps tests cheap (no module-level side effects)."""
    app = FastAPI(
        title="Mock Providers",
        version="0.1.0",
        description="Emulates OpenAI / Anthropic / Google APIs (DRD §23.2)",
    )

    # Provider routers are mounted at the path real SDKs expect; the gateway
    # config simply swaps base_url and everything works.
    app.include_router(openai_router, prefix="/v1", tags=["openai"])
    app.include_router(anthropic_router, prefix="/v1", tags=["anthropic"])
    app.include_router(google_router, prefix="/v1beta", tags=["google"])
    app.include_router(admin_router, prefix="/control", tags=["control"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    """Console-script entry — `mock-providers` after `pip install`."""
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104 — dev/CI server bound deliberately wide
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    run()
