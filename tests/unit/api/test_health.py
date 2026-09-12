"""Unit tests for health endpoint behavior and response contracts."""

import pytest
from httpx import AsyncClient


class TestLiveness:
    """GET /health/live must not depend on PostgreSQL."""

    @pytest.mark.asyncio
    async def test_liveness_returns_healthy_contract(self, client: AsyncClient):
        response = await client.get("/health/live")

        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "service": "paimana-ai-api",
            "version": "0.1.0",
        }


class TestReadiness:
    """GET /health/ready must accurately represent database availability."""

    @pytest.mark.asyncio
    async def test_readiness_returns_healthy_when_database_is_available(
        self, client: AsyncClient
    ):
        response = await client.get("/health/ready")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["dependencies"] == {"database": "healthy"}

    @pytest.mark.asyncio
    async def test_readiness_returns_503_without_database_details(
        self, unavailable_client: AsyncClient
    ):
        response = await unavailable_client.get("/health/ready")

        assert response.status_code == 503
        assert response.json()["status"] == "unhealthy"
        assert response.json()["dependencies"] == {"database": "unhealthy"}
        assert "internal details" not in response.text


class TestApplicationHealth:
    """GET /api/v1/health is the dashboard-facing health response."""

    @pytest.mark.asyncio
    async def test_application_health_returns_healthy_contract(
        self, client: AsyncClient
    ):
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "paimana-ai-api"
        assert response.json()["version"] == "0.1.0"
        assert response.json()["dependencies"] == {"database": "healthy"}

    @pytest.mark.asyncio
    async def test_application_health_returns_503_when_database_is_unavailable(
        self, unavailable_client: AsyncClient
    ):
        response = await unavailable_client.get("/api/v1/health")

        assert response.status_code == 503
        assert response.json()["status"] == "unhealthy"
        assert response.json()["dependencies"] == {"database": "unhealthy"}
