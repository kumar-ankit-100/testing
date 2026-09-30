"""Plan catalog admin API endpoints (E3-S3).

API layer — imports Types, Config, Repository, Service. Admin role is
checked here via require_role (giving a clean 403 before the handler
even runs) AND independently inside plan_catalog_service (E3-S2's
defense-in-depth pattern) — both paths raise the same AuthorizationError,
mapped once, globally, by error_handlers.py.
"""

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_db_connection, require_role
from app.api.schemas.plan_schemas import (
    CreatePlanVersionRequest,
    CreatePlanVersionResponse,
    PlanVersionListResponse,
    PlanVersionSchema,
    PublishPlanVersionResponse,
    UpdatePlanVersionRequest,
)
from app.repository.plan_repository import get_plan_version_by_id, list_all_plan_versions
from app.service.plan_catalog_service import (
    create_draft_plan_version,
    publish_plan_version,
    update_draft_plan_version,
)
from app.types.auth import Principal
from app.types.enums import ReasonCode, Role

router = APIRouter(prefix="/api/admin/plans", tags=["admin-plans"])


@router.post("", response_model=CreatePlanVersionResponse, status_code=201)
def create_plan(
    request: CreatePlanVersionRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(require_role(Role.ADMIN)),
) -> CreatePlanVersionResponse:
    """AC-1: creates a draft plan version, HTTP 201."""
    draft = create_draft_plan_version(
        connection,
        principal,
        plan_id=request.plan_id,
        plan_name=request.plan_name,
        plan_type=request.plan_type,
        price=request.price,
        terms=request.terms,
        created_at=datetime.now(UTC),
    )
    return CreatePlanVersionResponse(
        plan_version_id=draft.plan_version_id,
        plan_id=draft.plan_id,
        version_number=draft.version_number,
        published=draft.published,
    )


@router.post("/{plan_version_id}/publish", response_model=PublishPlanVersionResponse)
def publish_plan(
    plan_version_id: str,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(require_role(Role.ADMIN)),
) -> PublishPlanVersionResponse | JSONResponse:
    """AC-2: publishes a draft, HTTP 200 with published: true."""
    existing = get_plan_version_by_id(connection, plan_version_id)
    if existing is None:
        return _not_found(plan_version_id)

    published = publish_plan_version(
        connection, principal, existing.plan_id, plan_version_id, datetime.now(UTC)
    )
    assert published.published_at is not None  # guaranteed by publish_plan_version
    return PublishPlanVersionResponse(
        plan_version_id=published.plan_version_id,
        published=published.published,
        published_at=published.published_at,
    )


@router.put("/{plan_version_id}", response_model=PlanVersionSchema)
def update_plan(
    plan_version_id: str,
    request: UpdatePlanVersionRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(require_role(Role.ADMIN)),
) -> PlanVersionSchema | JSONResponse:
    """AC-3: editing an already-published version returns 409
    (PlanVersionImmutableError, mapped by error_handlers.py). Unset
    request fields keep the version's current value.
    """
    existing = get_plan_version_by_id(connection, plan_version_id)
    if existing is None:
        return _not_found(plan_version_id)

    new_price = request.price if request.price is not None else existing.price
    new_terms = request.terms if request.terms is not None else existing.terms
    updated = update_draft_plan_version(
        connection, principal, existing.plan_id, plan_version_id, new_price, new_terms
    )
    return PlanVersionSchema.from_domain(updated)


@router.get("", response_model=PlanVersionListResponse)
def list_plans(
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(require_role(Role.ADMIN)),
) -> PlanVersionListResponse:
    """AC-4: full version history across every plan_id, superseded
    versions included.
    """
    versions = list_all_plan_versions(connection)
    return PlanVersionListResponse(plans=[PlanVersionSchema.from_domain(v) for v in versions])


def _not_found(plan_version_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "reason_code": ReasonCode.NOT_FOUND.value,
                "message": f"Plan version {plan_version_id!r} not found",
                "details": {},
            }
        },
    )
