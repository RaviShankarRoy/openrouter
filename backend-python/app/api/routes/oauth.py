"""OAuth token exchange route — DRD FE-012.

The dashboard (Next.js + NextAuth) calls this on first sign-in to swap a
Google or GitHub access token for a backend JWT carrying user_id / org_id.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_uow
from app.service.oauth_service import (
    OAuthExchangeCommand,
    OAuthService,
)
from app.service.uow import UnitOfWork

router = APIRouter()


class OAuthExchangeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["google", "github"]
    access_token: str = Field(min_length=10, max_length=4096)


class OAuthExchangeResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int
    user_id: str
    org_id: str
    role: str


async def _get_oauth_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> OAuthService:
    return OAuthService(uow)


@router.post("/exchange", status_code=status.HTTP_200_OK, response_model=OAuthExchangeResponse)
async def exchange(
    body: OAuthExchangeBody,
    service: Annotated[OAuthService, Depends(_get_oauth_service)],
) -> OAuthExchangeResponse:
    issued = await service.exchange(
        OAuthExchangeCommand(provider=body.provider, access_token=body.access_token),
    )
    return OAuthExchangeResponse(
        access_token=issued.access_token,
        expires_in=issued.expires_in_seconds,
        user_id=issued.user_id,
        org_id=issued.org_id,
        role=issued.role,
    )
