"""Admin reporting service (E7-S2): wraps the read-only aggregation
queries in reporting_repository with admin-role enforcement, checked
here independently of the API layer (system-design.md 5.4's documented
exception pattern, also used by plan_catalog_service's E3-S2 checks).

Service layer — imports Types, Config, Repository.
"""

import sqlite3
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.repository.reporting_repository import (
    activation_funnel_counts,
    arpu_trend,
    monthly_churn_rate,
    plan_mix_distribution,
)
from app.types.auth import Principal
from app.types.enums import Role
from app.types.exceptions import AuthorizationError


def get_admin_dashboard(connection: sqlite3.Connection, principal: Principal) -> dict[str, Any]:
    """Assemble a presentation-ready admin dashboard: activation funnel,
    plan mix (counts and percentages), monthly churn rate, and a stubbed
    ARPU trend (AC-1/2/3).

    Raises AuthorizationError if principal is not an admin (AC-4),
    checked before any aggregation query runs.
    """
    _require_admin(principal)

    funnel = activation_funnel_counts(connection)
    plan_mix = plan_mix_distribution(connection)
    churn = monthly_churn_rate(connection)
    arpu = arpu_trend(connection)

    return {
        "activation_funnel": funnel,
        "plan_mix": plan_mix,
        "plan_mix_percentages": _as_percentages(plan_mix),
        "churn": churn,
        "arpu_trend": arpu,
        "metadata": {
            "arpu_trend_is_stubbed": True,
            "arpu_trend_note": "ARPU is synthetic/stubbed: billing_records are test "
            "fixtures, not real usage-rated charges.",
        },
    }


def _as_percentages(plan_mix: dict[str, int]) -> dict[str, Decimal]:
    """Convert raw counts to percentages of the whole, summing to exactly
    100.00 by giving any rounding remainder to the largest bucket (AC-2).
    """
    total = sum(plan_mix.values())
    if total == 0:
        return {}

    raw: dict[str, Decimal] = {
        plan_type: (Decimal(count) * Decimal(100) / Decimal(total)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        for plan_type, count in plan_mix.items()
    }
    remainder = Decimal("100.00") - sum(raw.values())
    if remainder != Decimal("0.00"):
        largest_key = max(plan_mix, key=lambda key: plan_mix[key])
        raw[largest_key] = raw[largest_key] + remainder
    return raw


def _require_admin(principal: Principal) -> None:
    if principal.role != Role.ADMIN:
        raise AuthorizationError(f"Role {principal.role.value} may not view admin reports")
