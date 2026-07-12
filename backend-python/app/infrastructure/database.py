"""SQLAlchemy 2.0 async engine + session factory.

Pattern: shared metadata object so Alembic autogenerate sees every model.
"""
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings

# Constraint naming convention so Alembic produces stable names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(settings: Settings) -> None:
    """Open the connection pool at startup."""
    global _engine, _session_factory  # noqa: PLW0603
    _engine = create_async_engine(
        settings.postgres_dsn,
        pool_size=settings.postgres_pool_max,
        pool_pre_ping=True,
        echo=False,
    )
    _session_factory = async_sessionmaker(
        _engine, expire_on_commit=False, class_=AsyncSession
    )
    # Import models so SQLAlchemy registers them on the metadata.
    from app.infrastructure import orm_models  # noqa: F401


async def close_db() -> None:
    if _engine is not None:
        await _engine.dispose()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("DB not initialized — call init_db() first")
    return _session_factory
