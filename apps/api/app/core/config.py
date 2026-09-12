"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _repository_root() -> Path:
    """Locate the repository root without depending on the launch directory."""
    for parent in Path(__file__).resolve().parents:
        if (parent / ".env.example").is_file():
            return parent
    return Path(__file__).resolve().parents[2]


REPOSITORY_ROOT = _repository_root()


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    # PostgreSQL. Docker Compose derives DATABASE_URL from these same values.
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_ADMIN_URL: str | None = None
    DATABASE_URL: str

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_ENV: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # App metadata
    APP_NAME: str = "PAIMANA AI Predictive Infrastructure Monitoring API"
    SERVICE_NAME: str = "paimana-ai-api"
    APP_VERSION: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        extra="ignore",
    )


settings = Settings()
