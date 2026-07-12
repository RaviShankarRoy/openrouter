"""Shared test fixtures.

Unit tests use fakes; integration tests spin up real Postgres + Redis via
testcontainers. Containers are session-scoped so the test suite stays fast
on cold start.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# testcontainers is an optional dep at runtime — guard the import so unit
# tests can run on machines without Docker.
try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
except ImportError:  # pragma: no cover
    PostgresContainer = None  # type: ignore[assignment,misc]
    RedisContainer = None  # type: ignore[assignment,misc]

from app.infrastructure.database import Base


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[str]:
    if PostgresContainer is None:
        pytest.skip("testcontainers not installed")
    with PostgresContainer("postgres:16") as pg:
        # asyncpg needs the driver-prefixed scheme.
        url = pg.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
        yield url


@pytest.fixture(scope="session")
def redis_container() -> Iterator[str]:
    if RedisContainer is None:
        pytest.skip("testcontainers not installed")
    with RedisContainer("redis:7-alpine") as r:
        yield f"redis://{r.get_container_host_ip()}:{r.get_exposed_port(6379)}/0"


@pytest_asyncio.fixture
async def db_session(postgres_container: str) -> AsyncIterator[AsyncSession]:
    """Async session backed by a real Postgres container with schema applied."""
    engine = create_async_engine(postgres_container, echo=False)
    # Import models so metadata is populated before create_all.
    from app.infrastructure import orm_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()
