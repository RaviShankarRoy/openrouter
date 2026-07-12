"""FastAPI dependency factories — DI for repositories, services, auth context.

Scope rules:
  - get_uow: per-request, fresh session_factory bound UoW.
  - get_current_user: per-request, derived from Bearer token.
  - require_role: returns a Depends-able callable that enforces RBAC.
  - get_provider_registry: process-wide singleton.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends, Header, status
from fastapi.exceptions import HTTPException

from app.application.services.auth_service import AuthService
from app.application.services.billing_service import BillingService
from app.application.uow import UnitOfWork
from app.core.security import sha256_lookup, verify_api_key
from app.domain.entities import APIKey, User, UserRole
from app.domain.errors import Forbidden, InvalidApiKey
from app.infrastructure.database import get_session_factory
from app.infrastructure.providers.registry import ProviderRegistry
from app.infrastructure.uow import SqlUnitOfWork


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Resolved auth context attached to every authenticated request."""

    user: User
    api_key: APIKey


# --- Composition root helpers ---


async def get_uow() -> UnitOfWork:
    """Per-request UoW. Caller is responsible for `async with` lifecycle."""
    return SqlUnitOfWork(get_session_factory())


async def get_auth_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> AuthService:
    return AuthService(uow)


async def get_billing_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> BillingService:
    return BillingService(uow)


def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry.instance()


# --- Authn / Authz ---


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise InvalidApiKey("Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


async def get_current_auth(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Resolve the API key and its owning user from the Bearer token.

    The hot path is in the Go gateway; this dependency exists so backend-internal
    routes (key management, billing, admin) can authenticate the same way.
    """
    plaintext = _extract_bearer(authorization)
    lookup = sha256_lookup(plaintext)
    async with uow:
        key = await uow.api_keys.find_by_lookup_hash(lookup)
        if key is None or not verify_api_key(plaintext, key.key_hash):
            raise InvalidApiKey("Unknown API key")
        key.assert_usable()
        user = await uow.users.get(key.user_id)
        if user is None:
            raise InvalidApiKey("Key owner not found")
    return AuthContext(user=user, api_key=key)


async def get_current_user(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
) -> User:
    return auth.user


def require_role(*allowed: UserRole) -> Callable[..., User]:
    """Return a Depends-able that enforces one of the allowed roles."""
    allowed_set = set(allowed)

    async def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed_set:
            raise Forbidden(f"Role {user.role.value} not permitted")
        return user

    return _dep


async def get_org_id(
    auth: Annotated[AuthContext, Depends(get_current_auth)],
) -> UUID:
    return auth.user.org_id


def http_401(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
