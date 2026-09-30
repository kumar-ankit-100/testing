"""Health check endpoint (E1-S5).

API layer — imports Types, Config, Repository, Service only.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return HTTP 200 immediately; no dependency checks, no auth required."""
    return HealthResponse(status="ok")
