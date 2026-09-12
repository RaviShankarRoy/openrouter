"""SQLAlchemy implementation of the Unit of Work pattern."""
from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.service.uow import UnitOfWork
from app.repository.api_keys import SqlAPIKeyRepository
from app.repository.credits import SqlCreditRepository
from app.repository.organizations import SqlOrganizationRepository
from app.repository.usage import SqlUsageRepository
from app.repository.users import SqlUserRepository
from app.repository.video_jobs import SqlVideoJobRepository


class SqlUnitOfWork(UnitOfWork):
    """One DB session per use case invocation. Repositories share the session."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlUnitOfWork":
        self._session = self._session_factory()
        # Wire repositories with the session — late binding keeps them stateless.
        self.api_keys = SqlAPIKeyRepository(self._session)
        self.users = SqlUserRepository(self._session)
        self.organizations = SqlOrganizationRepository(self._session)
        self.credits = SqlCreditRepository(self._session)
        self.usage = SqlUsageRepository(self._session)
        self.video_jobs = SqlVideoJobRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
