"""Cross-cutting decorators — @audit_log (DRD PY-010), @require_permission (PY-009).

Decorator pattern: wrap route handlers without changing call signatures. Both
decorators are Depends-aware: they pull the AuthContext from kwargs that
FastAPI injects via dependency resolution.
"""
from __future__ import annotations

import functools
from typing import Any, Awaitable, Callable, TypeVar
from uuid import uuid4

from app.api.dependencies import AuthContext
from app.core.logging import get_logger
from app.domain.entities import UserRole
from app.domain.errors import Forbidden
from app.infrastructure import orm_models as orm
from app.infrastructure.database import get_session_factory

T = TypeVar("T")

_log = get_logger(__name__)

# Coarse permission map keyed by (role, permission). Phase-2 work moves this
# into a policy table (DRD PY-009). Kept minimal here so route handlers can
# already declare their permission requirements.
_ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.OWNER: {"keys:write", "keys:read", "billing:write", "billing:read", "admin:write"},
    UserRole.ADMIN: {"keys:write", "keys:read", "billing:read", "admin:write"},
    UserRole.BILLING: {"billing:write", "billing:read"},
    UserRole.MEMBER: {"keys:read"},
}


def require_permission(permission: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Enforce that the caller's role grants `permission`.

    The wrapped handler must declare an `auth: AuthContext = Depends(...)`
    parameter; we read it from kwargs after FastAPI resolves dependencies.
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            auth = _find_auth_context(kwargs)
            if auth is None:
                # Misconfigured route — fail closed.
                raise Forbidden("Missing auth context for permission check")
            if permission not in _ROLE_PERMISSIONS.get(auth.user.role, set()):
                raise Forbidden(f"Permission {permission} denied for role {auth.user.role.value}")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def audit_log(
    action: str,
    target_type: str,
    target_id_arg: str | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Record the call in `audit_logs` after the handler succeeds (DRD PY-010, CO-007).

    `target_id_arg` names the kwarg that identifies the affected resource
    (e.g. "key_id"). Falls back to a generated UUID when absent.
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            result = await func(*args, **kwargs)
            try:
                await _write_audit(
                    action=action,
                    target_type=target_type,
                    target_id=str(kwargs.get(target_id_arg, uuid4())) if target_id_arg else str(uuid4()),
                    auth=_find_auth_context(kwargs),
                )
            except Exception:
                # Never let audit failure break the user-facing request.
                _log.exception("audit_log_write_failed", action=action)
            return result

        return wrapper

    return decorator


def _find_auth_context(kwargs: dict[str, Any]) -> AuthContext | None:
    for value in kwargs.values():
        if isinstance(value, AuthContext):
            return value
    return None


async def _write_audit(
    action: str,
    target_type: str,
    target_id: str,
    auth: AuthContext | None,
) -> None:
    factory = get_session_factory()
    async with factory() as session, session.begin():
        session.add(
            orm.AuditLog(
                id=uuid4(),
                org_id=auth.user.org_id if auth else None,
                actor_user_id=auth.user.id if auth else None,
                action=action,
                target_type=target_type,
                target_id=target_id,
                metadata_json={},
            )
        )
