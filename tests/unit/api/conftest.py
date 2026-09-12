"""Fixtures for isolated API unit tests."""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Unit tests replace the database dependency before a request is made. These
# defaults only let the app construct an async engine when no local .env exists.
os.environ.setdefault("POSTGRES_USER", "unit_user")
os.environ.setdefault("POSTGRES_PASSWORD", "unit_password")
os.environ.setdefault("POSTGRES_DB", "unit_database")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://unit_user:unit_password@localhost:5432/unit_database",
)

from app.api.dependencies import get_db
from app.main import app


class MockSession:
    """Minimal successful database session replacement."""

    async def execute(self, *args, **kwargs):
        return True

    async def close(self) -> None:
        return None


class UnavailableSession:
    """Database session replacement used to test degraded health responses."""

    async def execute(self, *args, **kwargs):
        raise RuntimeError(
            "database connection failed: internal details must stay private"
        )

    async def close(self) -> None:
        return None


@pytest_asyncio.fixture
async def client():
    """Async client with a healthy mock database session."""

    async def override_get_db():
        yield MockSession()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as api_client:
        yield api_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unavailable_client():
    """Async client with an unavailable mock database session."""

    async def override_get_db():
        yield UnavailableSession()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as api_client:
        yield api_client
    app.dependency_overrides.clear()
