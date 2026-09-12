"""Standard API response and safe error structures."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    """Standard envelope for all successful API responses."""

    success: bool = True
    message: str
    data: Any | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ErrorInfo(BaseModel):
    """Safe, client-facing error information."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard envelope for all error responses."""

    success: bool = False
    error: ErrorInfo
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
