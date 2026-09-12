"""Initialise a native local PostgreSQL database from root .env settings.

The script uses asyncpg, the same PostgreSQL driver as the API. It requires a
PostgreSQL administrator URL in POSTGRES_ADMIN_URL and never embeds credentials.
"""

import asyncio
import re
import sys
from pathlib import Path

import asyncpg

REPOSITORY_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPOSITORY_ROOT / "apps" / "api"))

from app.core.config import settings


def quote_identifier(value: str) -> str:
    """Quote and validate a PostgreSQL identifier supplied through configuration."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(
            "PostgreSQL user and database names must be simple identifiers."
        )
    return f'"{value}"'


async def quoted_literal(connection: asyncpg.Connection, value: str) -> str:
    """Return a PostgreSQL-quoted literal without interpolating a secret in Python."""
    return await connection.fetchval("SELECT quote_literal($1)", value)


async def initialise_database() -> None:
    """Create or align the configured role and database using an administrator URL."""
    if not settings.POSTGRES_ADMIN_URL:
        raise RuntimeError(
            "POSTGRES_ADMIN_URL is required. Set it in the repository-root .env before running this script."
        )

    user = quote_identifier(settings.POSTGRES_USER)
    database = quote_identifier(settings.POSTGRES_DB)
    admin_connection = await asyncpg.connect(settings.POSTGRES_ADMIN_URL)
    try:
        password = await quoted_literal(admin_connection, settings.POSTGRES_PASSWORD)
        role_exists = await admin_connection.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1", settings.POSTGRES_USER
        )
        if role_exists:
            await admin_connection.execute(
                f"ALTER ROLE {user} WITH LOGIN PASSWORD {password}"
            )
            print(f"Role {settings.POSTGRES_USER} updated")
        else:
            await admin_connection.execute(
                f"CREATE ROLE {user} WITH LOGIN PASSWORD {password}"
            )
            print(f"Role {settings.POSTGRES_USER} created")

        database_exists = await admin_connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", settings.POSTGRES_DB
        )
        if database_exists:
            await admin_connection.execute(f"ALTER DATABASE {database} OWNER TO {user}")
            print(f"Database {settings.POSTGRES_DB} ownership aligned")
        else:
            await admin_connection.execute(f"CREATE DATABASE {database} OWNER {user}")
            print(f"Database {settings.POSTGRES_DB} created")
    finally:
        await admin_connection.close()

    project_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )
    project_connection = await asyncpg.connect(project_url)
    try:
        await project_connection.execute(f"GRANT ALL ON SCHEMA public TO {user}")
    finally:
        await project_connection.close()

    print("Local PostgreSQL initialization complete")


if __name__ == "__main__":
    asyncio.run(initialise_database())
