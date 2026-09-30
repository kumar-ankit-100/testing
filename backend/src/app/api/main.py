"""FastAPI application factory for TelcoLane (E1-S5, extended E3-S3, E2-S4).

API layer — imports Types, Config, Repository, Service only.

Each subsequent API story mounts its own router here (per
specs/design/component-map.md's cross-cutting file notes) rather than
introducing a second app factory. The lifespan applies the DB schema
once at startup (idempotent — safe to run against an already-migrated
database) so routers that touch the DB never race an unmigrated schema.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.routers.health_router import router as health_router
from app.api.routers.plan_router import router as plan_router
from app.api.routers.subscriber_router import router as subscriber_router
from app.config.db import create_connection
from app.config.settings import get_settings
from app.repository.schema import apply_schema


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = create_connection(settings.db_path)
    try:
        apply_schema(connection)
    finally:
        connection.close()
    yield


def create_app() -> FastAPI:
    """Build and return the TelcoLane FastAPI application."""
    app = FastAPI(title="TelcoLane API", version="1.0.0", lifespan=_lifespan)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(plan_router)
    app.include_router(subscriber_router)
    return app


app = create_app()
