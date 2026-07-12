"""Inbound webhooks — Stripe (DRD PY-011).

Webhook handlers are unauthenticated at the Bearer-token layer; integrity is
verified via the provider's signature (HMAC). We never trust webhook payloads
as authoritative — we re-fetch the relevant Stripe object before mutating
local state.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.infrastructure.billing.stripe_client import StripeClient

router = APIRouter()
_log = get_logger(__name__)


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
) -> JSONResponse:
    payload = await request.body()
    client = StripeClient()
    try:
        event = client.verify_webhook(payload, stripe_signature)
    except ValueError as exc:
        _log.warning("stripe_signature_invalid", error=str(exc))
        return JSONResponse(status_code=400, content={"error": "invalid_signature"})
    await client.handle_webhook(event)
    return JSONResponse(content={"received": True})
