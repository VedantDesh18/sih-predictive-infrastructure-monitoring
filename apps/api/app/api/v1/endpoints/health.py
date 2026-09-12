"""Liveness, readiness, and application health endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import settings
from app.schemas.health import (
    DependenciesResponse,
    HealthResponse,
    LivenessResponse,
    ReadinessResponse,
)

logger = logging.getLogger(__name__)
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]

# ---------------------------------------------------------------------------
# Infrastructure-level probes (mounted at root, not versioned)
# ---------------------------------------------------------------------------

probe_router = APIRouter(tags=["Health"])


@probe_router.get(
    "/health/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Returns 200 if the API process is alive. No dependency checks.",
)
async def liveness() -> LivenessResponse:
    return LivenessResponse(
        service=settings.SERVICE_NAME,
        version=settings.APP_VERSION,
    )


@probe_router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns 200 if the API can serve requests, including database connectivity.",
)
async def readiness(db: DatabaseSession) -> ReadinessResponse | JSONResponse:
    try:
        await db.execute(text("SELECT 1"))
        return ReadinessResponse(
            status="healthy",
            service=settings.SERVICE_NAME,
            version=settings.APP_VERSION,
            dependencies=DependenciesResponse(database="healthy"),
        )
    except Exception:
        logger.exception("Database readiness check failed")
        response = ReadinessResponse(
            status="unhealthy",
            service=settings.SERVICE_NAME,
            version=settings.APP_VERSION,
            dependencies=DependenciesResponse(database="unhealthy"),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
        )


# ---------------------------------------------------------------------------
# Application-level health (versioned under /api/v1)
# ---------------------------------------------------------------------------

health_router = APIRouter(tags=["Health"])


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health",
    description="Application-level health check with version and environment info.",
)
async def app_health(db: DatabaseSession) -> HealthResponse | JSONResponse:
    try:
        await db.execute(text("SELECT 1"))
        return HealthResponse(
            status="healthy",
            service=settings.SERVICE_NAME,
            version=settings.APP_VERSION,
            dependencies=DependenciesResponse(database="healthy"),
        )
    except Exception:
        logger.exception("Application health database check failed")
        response = HealthResponse(
            status="unhealthy",
            service=settings.SERVICE_NAME,
            version=settings.APP_VERSION,
            dependencies=DependenciesResponse(database="unhealthy"),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
        )
