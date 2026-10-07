"""CSR override API endpoints (E6-S3): expose csr_override_service's
override_rejected_activation/override_rejected_plan_change, which
existed since the Group F fix-loop work but had no HTTP surface until
now — the same "orphaned service" gap as the auth-login endpoint.

API layer — imports Types, Config, Repository, Service. require_role
here is the same defense-in-depth pattern as plan_router.py: the
service's own _require_csr check (403) is the authoritative gate, this
just gives a clean 403 before the request body is even touched.
"""

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_db_connection, require_role
from app.api.schemas.csr_schemas import (
    OverrideActivationRequest,
    OverrideActivationResponse,
    OverridePlanChangeRequest,
    OverridePlanChangeResponse,
)
from app.config.settings import Settings, get_settings
from app.service.csr_override_service import (
    override_rejected_activation,
    override_rejected_plan_change,
)
from app.types.auth import Principal
from app.types.enums import Role

router = APIRouter(prefix="/api/csr/overrides", tags=["csr"])


@router.post(
    "/activation/{subscriber_id}",
    response_model=OverrideActivationResponse,
)
def override_activation(
    subscriber_id: str,
    request: OverrideActivationRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_role(Role.CSR)),
) -> OverrideActivationResponse:
    """AC-1."""
    subscription = override_rejected_activation(
        connection,
        principal,
        subscriber_id,
        request.dealer_code,
        settings,
        datetime.now(UTC),
        request.reason_code,
        request.original_rejection_reason,
    )
    return OverrideActivationResponse(
        subscriber_id=subscriber_id, state=subscription.state.value
    )


@router.post(
    "/plan-change/{subscription_id}",
    response_model=OverridePlanChangeResponse,
)
def override_plan_change(
    subscription_id: str,
    request: OverridePlanChangeRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_role(Role.CSR)),
) -> OverridePlanChangeResponse:
    """AC-2."""
    record = override_rejected_plan_change(
        connection,
        principal,
        subscription_id,
        request.target_plan_version_id,
        datetime.now(UTC),
        settings,
        request.reason_code,
        request.original_rejection_reason,
    )
    return OverridePlanChangeResponse(
        billing_record_id=record.billing_record_id,
        subscription_id=record.subscription_id,
        pro_rata_amount=record.pro_rata_amount,
    )
