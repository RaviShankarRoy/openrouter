"""Async Stripe wrapper (DRD PY-011).

The Stripe Python SDK is sync-only; we wrap it with `asyncio.to_thread` to
keep the FastAPI event loop unblocked. Webhook signature verification is
synchronous and cheap, so it stays inline.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any
from uuid import UUID

import stripe

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.database import get_session_factory
from app.infrastructure import orm_models as orm

_log = get_logger(__name__)

# Convert dollars to the integer-cent unit Stripe APIs expect.
_CENTS_PER_DOLLAR = Decimal("100")


class StripeClient:
    def __init__(self) -> None:
        stripe.api_key = settings.stripe_api_key.get_secret_value()
        self._webhook_secret = settings.stripe_webhook_secret.get_secret_value()

    async def create_payment_intent(
        self,
        amount_usd: Decimal,
        org_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        amount_cents = int((amount_usd * _CENTS_PER_DOLLAR).to_integral_value())

        def _create() -> Any:
            return stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata={
                    "org_id": str(org_id),
                    "user_id": str(user_id),
                    "kind": "credit_topup",
                },
                automatic_payment_methods={"enabled": True},
            )

        intent = await asyncio.to_thread(_create)
        return {"id": intent.id, "client_secret": intent.client_secret}

    def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """Validate the HMAC signature and parse the event. Raises ValueError on mismatch."""
        try:
            return stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise ValueError(str(exc)) from exc

    async def handle_webhook(self, event: dict[str, Any]) -> None:
        """Dispatch on event type. Idempotent — Stripe may redeliver."""
        event_type = event.get("type", "")
        obj = event.get("data", {}).get("object", {})
        if event_type == "payment_intent.succeeded":
            await self._credit_org(obj)
        elif event_type == "invoice.paid":
            # Subscription invoices apply credits keyed by Stripe customer ID.
            _log.info("stripe_invoice_paid", invoice_id=obj.get("id"))
        elif event_type in ("charge.failed", "payment_intent.payment_failed"):
            _log.warning(
                "stripe_payment_failed",
                event_id=event.get("id"),
                code=obj.get("failure_code"),
                message=obj.get("failure_message"),
            )
        else:
            _log.debug("stripe_event_ignored", event_type=event_type)

    @staticmethod
    async def _credit_org(payment_intent: dict[str, Any]) -> None:
        meta = payment_intent.get("metadata") or {}
        org_id_str = meta.get("org_id")
        if not org_id_str:
            _log.warning("stripe_missing_org_id", intent_id=payment_intent.get("id"))
            return
        org_id = UUID(org_id_str)
        amount_usd = Decimal(payment_intent.get("amount", 0)) / _CENTS_PER_DOLLAR
        factory = get_session_factory()
        async with factory() as session, session.begin():
            balance = await session.get(orm.CreditBalance, org_id, with_for_update=True)
            if balance is None:
                balance = orm.CreditBalance(org_id=org_id, available=amount_usd)
                session.add(balance)
            else:
                balance.available = balance.available + amount_usd
        _log.info("credits_applied", org_id=str(org_id), amount_usd=str(amount_usd))
