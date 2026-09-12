"""Authentication & API key issuance use cases (DRD Module 8)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from uuid import UUID

from app.service.uow import UnitOfWork
from app.shared.security import generate_api_key, hash_api_key, sha256_lookup, verify_api_key
from app.service.domain.entities import APIKey, KeyScope
from app.service.domain.errors import InvalidApiKey, NotFound


@dataclass(frozen=True)
class CreateKeyCommand:
    org_id: UUID
    user_id: UUID
    name: str
    scope: KeyScope = KeyScope.PERSONAL
    allowed_models: Sequence[str] = ()
    expires_at: datetime | None = None


@dataclass(frozen=True)
class CreatedKey:
    key: APIKey
    plaintext: str  # shown once at creation, never stored


class AuthService:
    """Use cases around API key lifecycle."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create_key(self, cmd: CreateKeyCommand) -> CreatedKey:
        """Issue a new API key. The plaintext is returned to the caller exactly once."""
        plaintext = generate_api_key()
        key = APIKey(
            org_id=cmd.org_id,
            user_id=cmd.user_id,
            name=cmd.name,
            scope=cmd.scope,
            key_hash=hash_api_key(plaintext),
            key_lookup=sha256_lookup(plaintext),
            allowed_models=list(cmd.allowed_models),
            expires_at=cmd.expires_at,
        )
        async with self._uow:
            await self._uow.api_keys.add(key)
            await self._uow.commit()
        return CreatedKey(key=key, plaintext=plaintext)

    async def validate_for_request(self, plaintext: str, model: str) -> APIKey:
        """Validate a key for a specific request. Two-step lookup: SHA-256 → argon2 verify."""
        lookup = sha256_lookup(plaintext)
        async with self._uow:
            key = await self._uow.api_keys.find_by_lookup_hash(lookup)
            if key is None:
                raise InvalidApiKey("Unknown API key")
            if not verify_api_key(plaintext, key.key_hash):
                raise InvalidApiKey("Invalid API key")
            key.assert_usable()
            key.assert_model_allowed(model)
            return key

    async def revoke_key(self, key_id: UUID, reason: str) -> None:
        """Revoke a key. The gateway picks this up via Redis pub/sub within 5s (DRD AK-004)."""
        async with self._uow:
            key = await self._uow.api_keys.get(key_id)
            if key is None:
                raise NotFound("API key not found")
            await self._uow.api_keys.revoke(key_id, reason)
            await self._uow.commit()
        # Publish revocation event so gateway invalidates its caches immediately.
        # Implemented in Phase 2 via app.repository.events.bus.
