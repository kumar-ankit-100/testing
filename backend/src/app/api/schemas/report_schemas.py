"""Pydantic response model for the admin reporting API (E7-S3).

API layer. reporting_service.get_admin_dashboard already returns a
presentation-ready dict (AC-1/2/3), so this wraps it as-is rather than
re-deriving a parallel typed shape.
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class AdminDashboardResponse(BaseModel):
    """GET /api/admin/reports/dashboard 200 response."""

    activation_funnel: dict[str, int]
    plan_mix: dict[str, int]
    plan_mix_percentages: dict[str, Decimal]
    churn: dict[str, Decimal]
    arpu_trend: dict[str, Decimal]
    metadata: dict[str, Any]
