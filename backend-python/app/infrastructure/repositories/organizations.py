"""Organization repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Organization
from app.domain.repositories import OrganizationRepository
from app.infrastructure import orm_models as orm


class SqlOrganizationRepository(OrganizationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, org_id: UUID) -> Organization | None:
        row = await self._session.get(orm.Organization, org_id)
        return _to_domain(row) if row else None

    async def add(self, org: Organization) -> Organization:
        row = orm.Organization(id=org.id, name=org.name, slug=org.slug)
        self._session.add(row)
        await self._session.flush()
        return org


def _to_domain(row: orm.Organization) -> Organization:
    return Organization(id=row.id, name=row.name, slug=row.slug, created_at=row.created_at)
