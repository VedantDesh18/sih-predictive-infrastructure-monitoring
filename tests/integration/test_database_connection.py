"""Integration checks against the PostgreSQL instance configured in root .env."""

import pytest
from app.core.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_configured_database_user_and_connection():
    """Verify the configured database, user, and a basic query with no mocks."""
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            database_name = await connection.scalar(text("SELECT current_database()"))
            user_name = await connection.scalar(text("SELECT current_user"))
            user_exists = await connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :role)"),
                {"role": settings.POSTGRES_USER},
            )
            basic_query = await connection.scalar(text("SELECT 1"))

        assert database_name == settings.POSTGRES_DB
        assert user_name == settings.POSTGRES_USER
        assert user_exists is True
        assert basic_query == 1
    finally:
        await engine.dispose()
