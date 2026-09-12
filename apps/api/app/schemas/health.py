"""Health check response schemas."""

from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    """Response for liveness probe."""

    status: Literal["healthy"] = "healthy"
    service: str
    version: str


class DependenciesResponse(BaseModel):
    """Health of application dependencies."""

    database: Literal["healthy", "unhealthy"]


class ReadinessResponse(BaseModel):
    """Response for readiness probe."""

    status: Literal["healthy", "unhealthy"]
    service: str
    version: str
    dependencies: DependenciesResponse


class HealthResponse(ReadinessResponse):
    """Response for application-level health check."""
