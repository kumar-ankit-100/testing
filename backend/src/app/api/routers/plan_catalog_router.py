"""Public (any authenticated role) plan catalog listing — the current
published version of every plan_id, so a subscriber can browse plans
when registering or choosing a plan-change target. Distinct from
plan_router.py's /api/admin/plans, which is admin-only and includes
drafts and superseded versions (full version history).

API layer — imports Types, Config, Repository, Service.
"""

import sqlite3

from fastapi import APIRouter, Depends

from app.api.deps import current_principal, get_db_connection
from app.api.schemas.plan_schemas import PlanVersionListResponse, PlanVersionSchema
from app.service.plan_catalog_service import list_published_catalog
from app.types.auth import Principal

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=PlanVersionListResponse)
def list_published_plans(
    connection: sqlite3.Connection = Depends(get_db_connection),
    _principal: Principal = Depends(current_principal),
) -> PlanVersionListResponse:
    """The current published version of every plan_id. Any authenticated
    role may call this (subscriber, csr, admin) — just not an
    unauthenticated caller.
    """
    versions = list_published_catalog(connection)
    return PlanVersionListResponse(plans=[PlanVersionSchema.from_domain(v) for v in versions])
