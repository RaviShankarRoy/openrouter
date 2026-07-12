"""AuthService unit tests against an in-memory UoW fake."""
from __future__ import annotations

from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

import pytest

from app.application.services.auth_service import AuthService, CreateKeyCommand
from app.application.uow import UnitOfWork
from app.domain.entities import APIKey
from app.domain.errors import InvalidApiKey, NotFound
from app.domain.repositories import APIKeyRepository


class _InMemoryKeyRepo(APIKeyRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, APIKey] = {}
        self._by_lookup: dict[str, APIKey] = {}

    async def find_by_lookup_hash(self, lookup_hash: str) -> APIKey | None:
        return self._by_lookup.get(lookup_hash)

    async def get(self, key_id: UUID) -> APIKey | None:
        return self._by_id.get(key_id)

    async def list_for_org(self, org_id: UUID) -> list[APIKey]:
        return [k for k in self._by_id.values() if k.org_id == org_id]

    async def add(self, key: APIKey) -> APIKey:
        self._by_id[key.id] = key
        self._by_lookup[key.key_lookup] = key
        return key

    async def revoke(self, key_id: UUID, reason: str) -> None:
        from datetime import UTC, datetime

        key = self._by_id[key_id]
        self._by_id[key_id] = key.model_copy(update={"revoked_at": datetime.now(UTC)})


class _FakeUoW(UnitOfWork):
    def __init__(self) -> None:
        self.api_keys = _InMemoryKeyRepo()
        self.users = None  # type: ignore[assignment]
        self.organizations = None  # type: ignore[assignment]
        self.credits = None  # type: ignore[assignment]
        self.usage = None  # type: ignore[assignment]
        self.video_jobs = None  # type: ignore[assignment]
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.asyncio
async def test_create_key_returns_plaintext_once() -> None:
    uow = _FakeUoW()
    svc = AuthService(uow)
    org_id, user_id = uuid4(), uuid4()
    created = await svc.create_key(
        CreateKeyCommand(org_id=org_id, user_id=user_id, name="test-key")
    )
    assert created.plaintext.startswith("sk-or-v1-")
    assert uow.committed is True


@pytest.mark.asyncio
async def test_validate_unknown_key_raises() -> None:
    svc = AuthService(_FakeUoW())
    with pytest.raises(InvalidApiKey):
        await svc.validate_for_request("sk-or-v1-deadbeef", model="gpt-4o")


@pytest.mark.asyncio
async def test_validate_round_trip() -> None:
    uow = _FakeUoW()
    svc = AuthService(uow)
    created = await svc.create_key(
        CreateKeyCommand(org_id=uuid4(), user_id=uuid4(), name="rt")
    )
    resolved = await svc.validate_for_request(created.plaintext, model="gpt-4o")
    assert resolved.id == created.key.id


@pytest.mark.asyncio
async def test_revoke_unknown_raises() -> None:
    svc = AuthService(_FakeUoW())
    with pytest.raises(NotFound):
        await svc.revoke_key(uuid4(), reason="manual")
