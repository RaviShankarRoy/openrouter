"""Video job repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import VideoJob, VideoJobStatus
from app.domain.repositories import VideoJobRepository
from app.domain.value_objects import Money
from app.infrastructure import orm_models as orm


class SqlVideoJobRepository(VideoJobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, job_id: UUID) -> VideoJob | None:
        row = await self._session.get(orm.VideoJob, job_id)
        return _to_domain(row) if row else None

    async def add(self, job: VideoJob) -> VideoJob:
        row = orm.VideoJob(
            id=job.id,
            org_id=job.org_id,
            key_id=job.key_id,
            model=job.model,
            prompt=job.prompt,
            status=job.status.value,
            output_urls=list(job.output_urls),
            cost_usd=job.cost.amount,
            error=job.error,
        )
        self._session.add(row)
        await self._session.flush()
        return job

    async def update(self, job: VideoJob) -> None:
        stmt = (
            update(orm.VideoJob)
            .where(orm.VideoJob.id == job.id)
            .values(
                status=job.status.value,
                output_urls=list(job.output_urls),
                cost_usd=job.cost.amount,
                error=job.error,
                completed_at=job.completed_at,
            )
        )
        await self._session.execute(stmt)


def _to_domain(row: orm.VideoJob) -> VideoJob:
    return VideoJob(
        id=row.id,
        org_id=row.org_id,
        key_id=row.key_id,
        model=row.model,
        prompt=row.prompt,
        status=VideoJobStatus(row.status),
        output_urls=list(row.output_urls or []),
        cost=Money(row.cost_usd),
        error=row.error,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )
