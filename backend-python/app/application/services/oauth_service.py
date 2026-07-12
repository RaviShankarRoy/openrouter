"""OAuth token exchange — converts a third-party access token into a backend JWT.

Used by the Next.js dashboard (DRD FE-012). The frontend's NextAuth callback
posts {provider, access_token} here on first sign-in; we resolve the user via
the provider's userinfo endpoint, find-or-create the User+Organization, and
return a backend JWT that encodes user_id, org_id, role.

Refresh tokens and rotation are Phase 1 work — the JWT we issue is short-lived
(default 1 hour) so a stolen one expires quickly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal
from uuid import uuid4

import httpx

from app.application.uow import UnitOfWork
from app.core.security import encode_jwt
from app.domain.entities import Organization, User, UserRole
from app.domain.errors import InvalidApiKey

Provider = Literal["google", "github"]

_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
_GITHUB_USER_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

_DEFAULT_TTL = timedelta(hours=1)


@dataclass(frozen=True)
class OAuthExchangeCommand:
    provider: Provider
    access_token: str


@dataclass(frozen=True)
class IssuedBackendJwt:
    access_token: str
    expires_in_seconds: int
    user_id: str
    org_id: str
    role: str


class OAuthService:
    """Exchange a provider access token for a backend JWT."""

    def __init__(self, uow: UnitOfWork, http_client: httpx.AsyncClient | None = None) -> None:
        self._uow = uow
        # Inject for tests; default to a per-call client.
        self._http = http_client

    async def exchange(self, cmd: OAuthExchangeCommand) -> IssuedBackendJwt:
        email = await self._resolve_email(cmd.provider, cmd.access_token)
        if not email:
            raise InvalidApiKey("OAuth token has no associated email")

        async with self._uow:
            user = await self._uow.users.find_by_email(email)
            if user is None:
                user = await self._provision_user(email)
            org_id = user.org_id
            role = user.role
            user_id = user.id
            await self._uow.commit()

        ttl = _DEFAULT_TTL
        token = encode_jwt(
            {
                "sub": str(user_id),
                "org_id": str(org_id),
                "role": role.value,
            },
            expires_in=ttl,
        )
        return IssuedBackendJwt(
            access_token=token,
            expires_in_seconds=int(ttl.total_seconds()),
            user_id=str(user_id),
            org_id=str(org_id),
            role=role.value,
        )

    async def _provision_user(self, email: str) -> User:
        """Create a new User + a new Organization for them. They become OWNER."""
        org = Organization(name=f"{email.split('@')[0]}'s workspace", slug=f"org-{uuid4().hex[:12]}")
        await self._uow.organizations.add(org)
        user = User(org_id=org.id, email=email, role=UserRole.OWNER)
        await self._uow.users.add(user)
        return user

    async def _resolve_email(self, provider: Provider, access_token: str) -> str | None:
        client = self._http or httpx.AsyncClient(timeout=5.0)
        owns_client = self._http is None
        try:
            if provider == "google":
                return await self._google_email(client, access_token)
            if provider == "github":
                return await self._github_email(client, access_token)
            raise InvalidApiKey(f"Unsupported provider: {provider}")
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    async def _google_email(client: httpx.AsyncClient, token: str) -> str | None:
        resp = await client.get(_GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            raise InvalidApiKey(f"Google userinfo failed: {resp.status_code}")
        data = resp.json()
        return data.get("email")

    @staticmethod
    async def _github_email(client: httpx.AsyncClient, token: str) -> str | None:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        # /user can hide the email if it's set to private; /user/emails always
        # returns the verified primary.
        resp = await client.get(_GITHUB_EMAILS_URL, headers=headers)
        if resp.status_code != 200:
            raise InvalidApiKey(f"GitHub emails failed: {resp.status_code}")
        for entry in resp.json():
            if entry.get("primary") and entry.get("verified"):
                return entry.get("email")
        return None
