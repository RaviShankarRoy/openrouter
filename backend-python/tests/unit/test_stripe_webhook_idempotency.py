"""Stripe webhook redelivery must not credit an organisation twice.

`StripeClient.handle_webhook` describes itself as "Idempotent — Stripe may
redeliver", but nothing anywhere records which event ids have already been
processed, and `_credit_org` performs an unconditional
`balance.available + amount_usd`.

Stripe retries on any non-2xx response and can redeliver an event even after a
successful one, so a replay grants free credit. The docstring's claim makes this
worse than a plain omission: a reviewer reading the method is told the
protection exists.

These tests assert the behaviour we require and are RED until Phase 4 adds an
event-id ledger. The fix must key on `event["id"]`, which Stripe guarantees is
stable across redeliveries of the same event.
"""
from __future__ import annotations

from decimal import Decimal
from types import TracebackType
from typing import Any, Self
from uuid import UUID, uuid4

import pytest

from app.repository import orm_models as orm
from app.repository.billing import stripe_client as stripe_client_module
from app.repository.billing.stripe_client import StripeClient


class _NullTransaction:
    """Stands in for `session.begin()`, which the code uses as an async CM."""

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None


class _FakeSession:
    """Minimal async session over a dict, exposing only what _credit_org uses."""

    def __init__(self, store: dict[UUID, orm.CreditBalance]) -> None:
        self._store = store

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None

    def begin(self) -> _NullTransaction:
        return _NullTransaction()

    async def get(
        self, model: type[Any], pk: UUID, with_for_update: bool = False
    ) -> orm.CreditBalance | None:
        return self._store.get(pk)

    def add(self, obj: orm.CreditBalance) -> None:
        self._store[obj.org_id] = obj


@pytest.fixture
def credit_store(monkeypatch: pytest.MonkeyPatch) -> dict[UUID, orm.CreditBalance]:
    """Replace the real session factory so no database is needed."""
    store: dict[UUID, orm.CreditBalance] = {}

    def _factory() -> _FakeSession:
        return _FakeSession(store)

    monkeypatch.setattr(stripe_client_module, "get_session_factory", lambda: _factory)
    return store


def _payment_succeeded_event(event_id: str, org_id: UUID, amount_cents: int) -> dict[str, Any]:
    return {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": f"pi_{event_id}",
                "amount": amount_cents,
                "metadata": {"org_id": str(org_id), "kind": "credit_topup"},
            }
        },
    }


@pytest.mark.asyncio
async def test_redelivered_event_credits_only_once(
    credit_store: dict[UUID, orm.CreditBalance],
) -> None:
    """The same event id delivered twice must credit the org exactly once."""
    org_id = uuid4()
    event = _payment_succeeded_event("evt_replay_me", org_id, amount_cents=5000)

    client = StripeClient()
    await client.handle_webhook(event)
    await client.handle_webhook(event)  # Stripe redelivery of the *same* event

    balance = credit_store[org_id]
    assert balance.available == Decimal("50"), (
        "replaying one Stripe event credited the org "
        f"${balance.available} instead of $50 — handle_webhook is not idempotent"
    )


@pytest.mark.asyncio
async def test_distinct_events_each_credit(
    credit_store: dict[UUID, orm.CreditBalance],
) -> None:
    """Two genuinely different top-ups must both apply.

    Guards against a Phase 4 fix that suppresses every repeat credit rather than
    deduplicating on event id.
    """
    org_id = uuid4()
    client = StripeClient()
    await client.handle_webhook(_payment_succeeded_event("evt_one", org_id, 5000))
    await client.handle_webhook(_payment_succeeded_event("evt_two", org_id, 2500))

    assert credit_store[org_id].available == Decimal("75")


@pytest.mark.asyncio
async def test_event_without_org_id_credits_nobody(
    credit_store: dict[UUID, orm.CreditBalance],
) -> None:
    """A payment intent with no org_id metadata must be ignored, not guessed at."""
    event = _payment_succeeded_event("evt_no_org", uuid4(), 5000)
    event["data"]["object"]["metadata"] = {}

    await StripeClient().handle_webhook(event)

    assert credit_store == {}
