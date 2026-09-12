"""Admin routes — RBAC-restricted operations (DRD PY-009, CO-007)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.decorators import audit_log, require_permission
from app.api.dependencies import AuthContext, get_current_auth, get_uow
from app.service.uow import UnitOfWork
from app.service.domain.errors import NotFound

router = APIRouter()


@router.post("/users/{user_id}/suspend", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(action="user.suspend", target_type="user", target_id_arg="user_id")
@require_permission("admin:write")
async def suspend_user(
    user_id: UUID,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> None:
    """Suspend a user by revoking all their API keys.

    Phase-2 work adds a `suspended_at` column; for now we revoke keys to
    achieve the same observable effect without a schema change.
    """
    async with uow:
        user = await uow.users.get(user_id)
        if user is None:
            raise NotFound("User not found")
        if user.org_id != auth.user.org_id:
            raise NotFound("User not in your organization")
        keys = await uow.api_keys.list_for_org(user.org_id)
        for k in keys:
            if k.user_id == user_id and k.revoked_at is None:
                await uow.api_keys.revoke(k.id, reason="user_suspended")
        await uow.commit()
