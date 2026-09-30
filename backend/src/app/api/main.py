"""FastAPI application factory for TelcoLane (E1-S5).

API layer — imports Types, Config, Repository, Service only.

Each subsequent API story mounts its own router here (per
specs/design/component-map.md's cross-cutting file notes) rather than
introducing a second app factory.
"""

from fastapi import FastAPI

from app.api.routers.health_router import router as health_router


def create_app() -> FastAPI:
    """Build and return the TelcoLane FastAPI application."""
    app = FastAPI(title="TelcoLane API", version="1.0.0")
    app.include_router(health_router)
    return app


app = create_app()
