"""HTTP route registration. One router per bounded context."""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import admin, auth, billing, health, models, oauth, webhooks


def register_routes(app: FastAPI) -> None:
    """Wire all routers under their canonical prefixes."""
    app.include_router(health.router)  # /health, /ready — no version prefix
    app.include_router(auth.router, prefix="/v1", tags=["auth"])
    app.include_router(oauth.router, prefix="/v1/oauth", tags=["oauth"])
    app.include_router(billing.router, prefix="/v1/billing", tags=["billing"])
    app.include_router(models.router, prefix="/v1", tags=["models"])
    app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])
    app.include_router(webhooks.router, prefix="/v1/webhooks", tags=["webhooks"])
