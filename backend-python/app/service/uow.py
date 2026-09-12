"""Unit of Work pattern — transactional boundary across repositories."""
from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from app.service.domain.repositories import (
    APIKeyRepository,
    CreditRepository,
    OrganizationRepository,
    UsageRepository,
    UserRepository,
    VideoJobRepository,
)


class UnitOfWork(ABC):
    """All repositories share one DB transaction. Commit on success; rollback on exception."""

    api_keys: APIKeyRepository
    users: UserRepository
    organizations: OrganizationRepository
    credits: CreditRepository
    usage: UsageRepository
    video_jobs: VideoJobRepository

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
