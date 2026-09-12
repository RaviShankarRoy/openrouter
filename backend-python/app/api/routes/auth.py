"""API key management routes — DRD AK-001..010."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.decorators import audit_log, require_permission
from app.api.dependencies import AuthContext, get_auth_service, get_current_auth, get_uow
from app.service.auth_service import AuthService, CreateKeyCommand
from app.service.uow import UnitOfWork
from app.service.domain.entities import KeyScope

router = APIRouter()


class CreateKeyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    scope: KeyScope = KeyScope.PERSONAL
    allowed_models: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class KeyView(BaseModel):
    id: UUID
    name: str
    scope: KeyScope
    allowed_models: list[str]
    expires_at: datetime | None
    created_at: datetime


class CreatedKeyView(KeyView):
    """Plaintext returned exactly once at creation (DRD AK-001)."""

    plaintext: str


@router.post("/keys", status_code=status.HTTP_201_CREATED, response_model=CreatedKeyView)
@audit_log(action="api_key.create", target_type="api_key")
@require_permission("keys:write")
async def create_key(
    body: CreateKeyBody,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> CreatedKeyView:
    cmd = CreateKeyCommand(
        org_id=auth.user.org_id,
        user_id=auth.user.id,
        name=body.name,
        scope=body.scope,
        allowed_models=tuple(body.allowed_models),
        expires_at=body.expires_at,
    )
    created = await service.create_key(cmd)
    return CreatedKeyView(
        id=created.key.id,
        name=created.key.name,
        scope=created.key.scope,
        allowed_models=list(created.key.allowed_models),
        expires_at=created.key.expires_at,
        created_at=created.key.created_at,
        plaintext=created.plaintext,
    )


@router.get("/keys", response_model=list[KeyView])
@require_permission("keys:read")
async def list_keys(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> list[KeyView]:
    # Pure read — UoW directly. Service stays use-case focused.
    async with uow:
        keys = await uow.api_keys.list_for_org(auth.user.org_id)
    return [
        KeyView(
            id=k.id,
            name=k.name,
            scope=k.scope,
            allowed_models=list(k.allowed_models),
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(action="api_key.revoke", target_type="api_key", target_id_arg="key_id")
@require_permission("keys:write")
async def revoke_key(
    key_id: UUID,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    await service.revoke_key(key_id, reason="user_requested")
