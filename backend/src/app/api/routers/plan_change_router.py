"""Plan change API endpoints (E4-S4): preview and commit a plan upgrade/
downgrade for a subscription.

API layer — imports Types, Config, Repository, Service. Ownership is
enforced here (subscriber principals may only act on their own
subscription_id) since require_own_subscriber is keyed on a
subscriber_id path param, not subscription_id (AC-5); staff roles pass
through unchecked, same as require_own_subscriber's own documented
pattern.
"""

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.deps import current_principal, get_db_connection
from app.api.schemas.plan_change_schemas import (
    PlanChangeCommitResponse,
    PlanChangePreviewResponse,
    PlanChangeRequest,
)
from app.config.settings import Settings, get_settings
from app.repository.subscriber_repository import get_subscription_by_id
from app.service.plan_change_service import commit_plan_change, preview_plan_change
from app.types.auth import Principal
from app.types.enums import Role
from app.types.exceptions import AuthorizationError

router = APIRouter(prefix="/api/subscriptions", tags=["plan-change"])


def _require_own_subscription(
    connection: sqlite3.Connection, subscription_id: str, principal: Principal
) -> None:
    if principal.role != Role.SUBSCRIBER:
        return
    subscription = get_subscription_by_id(connection, subscription_id)
    if subscription is None or subscription.subscriber_id != principal.subscriber_id:
        raise AuthorizationError("Subscribers may only access their own subscription data")


@router.post(
    "/{subscription_id}/plan-change/preview", response_model=PlanChangePreviewResponse
)
def preview(
    subscription_id: str,
    request: PlanChangeRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(current_principal),
) -> PlanChangePreviewResponse:
    """AC-1/AC-5."""
    _require_own_subscription(connection, subscription_id, principal)
    pro_rata_amount = preview_plan_change(
        connection, subscription_id, request.target_plan_version_id, datetime.now(UTC), settings
    )
    return PlanChangePreviewResponse(pro_rata_amount=pro_rata_amount)


@router.post("/{subscription_id}/plan-change/commit", response_model=PlanChangeCommitResponse)
def commit(
    subscription_id: str,
    request: PlanChangeRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(current_principal),
) -> PlanChangeCommitResponse:
    """AC-2/AC-3/AC-4/AC-5."""
    _require_own_subscription(connection, subscription_id, principal)
    record = commit_plan_change(
        connection, subscription_id, request.target_plan_version_id, datetime.now(UTC), settings
    )
    return PlanChangeCommitResponse(
        billing_record_id=record.billing_record_id,
        subscription_id=record.subscription_id,
        from_plan_version_id=record.from_plan_version_id,
        to_plan_version_id=record.to_plan_version_id,
        pro_rata_amount=record.pro_rata_amount,
        billing_period_start=record.billing_period_start,
        billing_period_end=record.billing_period_end,
    )
