"""AuthService unit tests against an in-memory UoW fake."""
from __future__ import annotations

from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

import pytest

from app.service.auth_service import AuthService, CreateKeyCommand
from app.service.uow import UnitOfWork
from app.service.domain.entities import APIKey
from app.service.domain.errors import Forbidden, InvalidApiKey, NotFound
from app.service.domain.repositories import APIKeyRepository


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


@pytest.mark.asyncio
async def test_revoke_key_refuses_cross_tenant_revocation() -> None:
    """A caller scoped to org A must not be able to revoke org B's key.

    Broken Object Level Authorization (OWASP API1:2023). `revoke_key` loads the
    key, uses it only for a None check, then revokes — the key's `org_id` is
    never compared against the caller. There is no caller identity in the
    signature at all, so the method cannot authorize even in principle: anyone
    who learns or enumerates a key id can revoke another tenant's key.

    This asserts the behaviour we require, so it is RED until Phase 4 adds the
    ownership check. Expected shape of the fix: an explicit caller org argument
    that raises Forbidden (or NotFound, to avoid confirming the id exists) when
    it does not match the key's owner.
    """
    uow = _FakeUoW()
    svc = AuthService(uow)

    victim = await svc.create_key(
        CreateKeyCommand(org_id=uuid4(), user_id=uuid4(), name="victim-key")
    )
    attacker_org_id = uuid4()
    assert attacker_org_id != victim.key.org_id

    try:
        await svc.revoke_key(
            victim.key.id, reason="attacker", caller_org_id=attacker_org_id
        )
    except TypeError as exc:
        pytest.fail(
            "revoke_key takes no caller identity, so cross-tenant revocation "
            f"cannot be refused: {exc}"
        )
    except (Forbidden, NotFound):
        pass  # Correct: the cross-tenant caller was refused.

    surviving = await uow.api_keys.get(victim.key.id)
    assert surviving is not None
    assert surviving.revoked_at is None, (
        "victim's key was revoked by a caller belonging to a different org"
    )


@pytest.mark.asyncio
async def test_revoke_key_allows_the_owning_org() -> None:
    """The legitimate owner must still be able to revoke. Guards the fix.

    Written alongside the BOLA test so that Phase 4 cannot "fix" the
    vulnerability by refusing every revocation.
    """
    uow = _FakeUoW()
    svc = AuthService(uow)
    org_id = uuid4()
    created = await svc.create_key(
        CreateKeyCommand(org_id=org_id, user_id=uuid4(), name="own-key")
    )

    try:
        await svc.revoke_key(created.key.id, reason="rotated", caller_org_id=org_id)
    except TypeError:
        pytest.skip("revoke_key has no caller-identity parameter yet (see BOLA test)")

    revoked = await uow.api_keys.get(created.key.id)
    assert revoked is not None
    assert revoked.revoked_at is not None, "owner's own revocation did not take effect"
