"""User repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import User, UserRole
from app.domain.repositories import UserRepository
from app.infrastructure import orm_models as orm


class SqlUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> User | None:
        row = await self._session.get(orm.User, user_id)
        return _to_domain(row) if row else None

    async def find_by_email(self, email: str) -> User | None:
        stmt = select(orm.User).where(orm.User.email == email)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def add(self, user: User) -> User:
        row = orm.User(
            id=user.id,
            org_id=user.org_id,
            email=user.email,
            role=user.role.value,
        )
        self._session.add(row)
        await self._session.flush()
        return user


def _to_domain(row: orm.User) -> User:
    return User(
        id=row.id,
        org_id=row.org_id,
        email=row.email,
        role=UserRole(row.role),
        created_at=row.created_at,
    )
