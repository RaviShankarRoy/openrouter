"""Shared pytest fixtures — mounts the FastAPI app on httpx for in-process tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app
from src.scenarios import engine


@pytest.fixture(autouse=True)
def _reset_engine() -> None:
    """Each test starts from a clean scenario state."""
    engine.reset()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://mock") as c:
        yield c
