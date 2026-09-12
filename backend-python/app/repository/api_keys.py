"""API key repository — Data Mapper between domain APIKey and ORM APIKey."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.service.domain.entities import APIKey, KeyScope
from app.service.domain.repositories import APIKeyRepository
from app.repository import orm_models as orm


class SqlAPIKeyRepository(APIKeyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_lookup_hash(self, lookup_hash: str) -> APIKey | None:
        stmt = select(orm.APIKey).where(orm.APIKey.key_lookup == lookup_hash)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get(self, key_id: UUID) -> APIKey | None:
        row = await self._session.get(orm.APIKey, key_id)
        return _to_domain(row) if row else None

    async def list_for_org(self, org_id: UUID) -> list[APIKey]:
        stmt = select(orm.APIKey).where(orm.APIKey.org_id == org_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def add(self, key: APIKey) -> APIKey:
        row = orm.APIKey(
            id=key.id,
            org_id=key.org_id,
            user_id=key.user_id,
            name=key.name,
            scope=key.scope.value,
            key_hash=key.key_hash,
            key_lookup=key.key_lookup,
            allowed_models=list(key.allowed_models),
            denied_models=list(key.denied_models),
            expires_at=key.expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return key

    async def revoke(self, key_id: UUID, reason: str) -> None:
        stmt = (
            update(orm.APIKey)
            .where(orm.APIKey.id == key_id)
            .values(revoked_at=datetime.now(UTC), revocation_reason=reason)
        )
        await self._session.execute(stmt)


def _to_domain(row: orm.APIKey) -> APIKey:
    return APIKey(
        id=row.id,
        org_id=row.org_id,
        user_id=row.user_id,
        name=row.name,
        scope=KeyScope(row.scope),
        key_hash=row.key_hash,
        key_lookup=row.key_lookup,
        allowed_models=list(row.allowed_models or []),
        denied_models=list(row.denied_models or []),
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
    )
