"""Repository interfaces (Ports). Implementations live in infrastructure/.

Pattern: Repository — abstract persistence behind narrow query methods named
after business intent ("find_by_lookup_hash"), not SQL operations ("select").
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.service.domain.entities import APIKey, CreditBalance, Organization, UsageRecord, User, VideoJob
from app.service.domain.value_objects import Money


class APIKeyRepository(ABC):
    @abstractmethod
    async def find_by_lookup_hash(self, lookup_hash: str) -> APIKey | None: ...

    @abstractmethod
    async def get(self, key_id: UUID) -> APIKey | None: ...

    @abstractmethod
    async def list_for_org(self, org_id: UUID) -> list[APIKey]: ...

    @abstractmethod
    async def add(self, key: APIKey) -> APIKey: ...

    @abstractmethod
    async def revoke(self, key_id: UUID, reason: str) -> None: ...


class UserRepository(ABC):
    @abstractmethod
    async def get(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def add(self, user: User) -> User: ...


class OrganizationRepository(ABC):
    @abstractmethod
    async def get(self, org_id: UUID) -> Organization | None: ...

    @abstractmethod
    async def add(self, org: Organization) -> Organization: ...


class CreditRepository(ABC):
    @abstractmethod
    async def get_for_update(self, org_id: UUID) -> CreditBalance: ...

    @abstractmethod
    async def update(self, balance: CreditBalance) -> None: ...

    @abstractmethod
    async def deduct_atomic(self, org_id: UUID, amount: Money) -> bool:
        """Atomic UPDATE...RETURNING — true if successful, false if insufficient."""
        ...


class UsageRepository(ABC):
    @abstractmethod
    async def add(self, record: UsageRecord) -> None: ...

    @abstractmethod
    async def aggregate_for_period(
        self, org_id: UUID, start: str, end: str
    ) -> dict[str, float]: ...


class VideoJobRepository(ABC):
    @abstractmethod
    async def get(self, job_id: UUID) -> VideoJob | None: ...

    @abstractmethod
    async def add(self, job: VideoJob) -> VideoJob: ...

    @abstractmethod
    async def update(self, job: VideoJob) -> None: ...
