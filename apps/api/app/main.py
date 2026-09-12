"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.health import probe_router
from app.api.v1.router import v1_router
from app.core.config import settings
from app.db.session import async_session_factory
from app.schemas.common import ErrorInfo, ErrorResponse
from app.services.synthetic_data import seed_synthetic_projects

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Seed the deterministic demo portfolio after Alembic creates the schema."""
    async with async_session_factory() as session:
        await seed_synthetic_projects(session)
    yield


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-Powered Predictive Infrastructure Monitoring & Early Warning System. "
            "A decision-support layer that consumes PAIMANA-compatible data to predict "
            "cost overruns, schedule delays, and implementation risks."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception handlers ---
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        logger.warning(
            "HTTP exception on %s: status=%s", request.url.path, exc.status_code
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorInfo(
                    code=f"HTTP_{exc.status_code}",
                    message="The request could not be completed.",
                )
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorInfo(
                    code="VALIDATION_ERROR",
                    message="The request payload is invalid.",
                )
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorInfo(
                    code="INTERNAL_SERVER_ERROR",
                    message="The requested service is temporarily unavailable.",
                )
            ).model_dump(mode="json"),
        )

    # --- Routers ---
    # Infrastructure probes at root level (/health/live, /health/ready)
    app.include_router(probe_router)

    # Versioned API (/api/v1/...)
    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
