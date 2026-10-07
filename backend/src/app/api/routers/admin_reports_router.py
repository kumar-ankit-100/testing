"""Admin reporting API endpoint (E7-S3): exposes
reporting_service.get_admin_dashboard, which existed since the Group F
fix-loop work but had no HTTP surface until now.

API layer — imports Types, Config, Repository, Service.
"""

import sqlite3

from fastapi import APIRouter, Depends

from app.api.deps import current_principal, get_db_connection
from app.api.schemas.report_schemas import AdminDashboardResponse
from app.service.reporting_service import get_admin_dashboard
from app.types.auth import Principal

router = APIRouter(prefix="/api/admin/reports", tags=["admin-reports"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def dashboard(
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(current_principal),
) -> AdminDashboardResponse:
    """AC-1/AC-2/AC-3. AC-4 (admin-only) is enforced inside
    get_admin_dashboard itself (system-design.md 5.4's documented
    pattern), so current_principal here resolves the token only — the
    role check is deliberately not duplicated at this layer.
    """
    dashboard_data = get_admin_dashboard(connection, principal)
    return AdminDashboardResponse(**dashboard_data)
