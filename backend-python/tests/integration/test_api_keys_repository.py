"""Integration: SqlAPIKeyRepository against a real Postgres testcontainer."""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.security import generate_api_key, hash_api_key, sha256_lookup
from app.service.domain.entities import APIKey, KeyScope, Organization, User, UserRole
from app.repository.api_keys import SqlAPIKeyRepository
from app.repository.organizations import SqlOrganizationRepository
from app.repository.users import SqlUserRepository


@pytest.mark.asyncio
async def test_add_then_find_by_lookup_hash(db_session: AsyncSession) -> None:
    org = Organization(name="Acme", slug=f"acme-{uuid4().hex[:6]}")
    await SqlOrganizationRepository(db_session).add(org)
    user = User(org_id=org.id, email=f"u-{uuid4().hex[:6]}@example.com", role=UserRole.OWNER)
    await SqlUserRepository(db_session).add(user)

    plaintext = generate_api_key()
    key = APIKey(
        org_id=org.id,
        user_id=user.id,
        name="primary",
        scope=KeyScope.PERSONAL,
        key_hash=hash_api_key(plaintext),
        key_lookup=sha256_lookup(plaintext),
    )
    repo = SqlAPIKeyRepository(db_session)
    await repo.add(key)
    await db_session.commit()

    found = await repo.find_by_lookup_hash(key.key_lookup)
    assert found is not None
    assert found.id == key.id
    assert found.org_id == org.id


@pytest.mark.asyncio
async def test_revoke_sets_revoked_at(db_session: AsyncSession) -> None:
    org = Organization(name="A", slug=f"o-{uuid4().hex[:6]}")
    await SqlOrganizationRepository(db_session).add(org)
    user = User(org_id=org.id, email=f"u-{uuid4().hex[:6]}@example.com")
    await SqlUserRepository(db_session).add(user)

    plaintext = generate_api_key()
    key = APIKey(
        org_id=org.id,
        user_id=user.id,
        name="to-revoke",
        key_hash=hash_api_key(plaintext),
        key_lookup=sha256_lookup(plaintext),
    )
    repo = SqlAPIKeyRepository(db_session)
    await repo.add(key)
    await db_session.commit()

    await repo.revoke(key.id, reason="leaked")
    await db_session.commit()

    refreshed = await repo.get(key.id)
    assert refreshed is not None
    assert refreshed.revoked_at is not None
