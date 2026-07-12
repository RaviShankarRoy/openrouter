"""Billing routes — balance, top-up via Stripe, usage reporting (DRD §12)."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.decorators import audit_log, require_permission
from app.api.dependencies import AuthContext, get_current_auth, get_uow
from app.application.uow import UnitOfWork
from app.infrastructure.billing.stripe_client import StripeClient

router = APIRouter()


class BalanceView(BaseModel):
    available: Decimal
    reserved: Decimal
    monthly_cap: Decimal | None = None
    daily_cap: Decimal | None = None
    hard_stop: bool


class PurchaseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_usd: Decimal = Field(gt=Decimal("0"), le=Decimal("100000"))


class PurchaseResponse(BaseModel):
    client_secret: str
    payment_intent_id: str


class UsageView(BaseModel):
    input_tokens: int
    output_tokens: int
    cost_usd: float
    requests: int


@router.get("/balance", response_model=BalanceView)
@require_permission("billing:read")
async def get_balance(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> BalanceView:
    async with uow:
        balance = await uow.credits.get_for_update(auth.user.org_id)
    return BalanceView(
        available=balance.available,
        reserved=balance.reserved,
        monthly_cap=balance.monthly_cap,
        daily_cap=balance.daily_cap,
        hard_stop=balance.hard_stop,
    )


@router.post("/credits/purchase", response_model=PurchaseResponse)
@audit_log(action="billing.purchase_intent", target_type="org")
@require_permission("billing:write")
async def purchase_credits(
    body: PurchaseBody,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
) -> PurchaseResponse:
    """Create a Stripe PaymentIntent. Credits are applied via webhook (DRD PY-011)."""
    client = StripeClient()
    intent = await client.create_payment_intent(
        amount_usd=body.amount_usd,
        org_id=auth.user.org_id,
        user_id=auth.user.id,
    )
    return PurchaseResponse(
        client_secret=intent["client_secret"],
        payment_intent_id=intent["id"],
    )


@router.get("/usage", response_model=UsageView)
@require_permission("billing:read")
async def get_usage(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
) -> UsageView:
    end = end or datetime.utcnow()
    start = start or (end - timedelta(days=30))
    async with uow:
        agg = await uow.usage.aggregate_for_period(
            auth.user.org_id, start.isoformat(), end.isoformat()
        )
    return UsageView(**agg)
