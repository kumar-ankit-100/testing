"""Registration and activation API endpoints (E2-S4), auth-gated per
api-contracts.md now that E1-S6 built the login endpoint these routes
were originally waiting on.

API layer — imports Types, Config, Repository, Service.
"""

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_db_connection, require_own_subscriber, require_role
from app.api.schemas.subscriber_schemas import (
    ActivateSubscriberRequest,
    ActivateSubscriberResponse,
    RegisterSubscriberRequest,
    RegisterSubscriberResponse,
)
from app.config.settings import Settings, get_settings
from app.service.activation_service import activate_subscriber
from app.service.auth_service import create_access_token
from app.service.registration_service import register_subscriber
from app.types.auth import Principal
from app.types.enums import Role

router = APIRouter(prefix="/api/subscribers", tags=["subscribers"])


@router.post("/register", response_model=RegisterSubscriberResponse, status_code=201)
def register(
    request: RegisterSubscriberRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    settings: Settings = Depends(get_settings),
    _principal: Principal = Depends(require_role(Role.SUBSCRIBER)),
) -> RegisterSubscriberResponse:
    """AC-1: valid input creates a subscription in PENDING_KYC, HTTP 201.

    Requires a subscriber-role token (the pre-registration token from
    POST /api/auth/login). Returns a fresh access_token with
    subscriber_id now populated, per api-contracts.md, so the caller can
    use it for the subsequent activate call.
    """
    subscription = register_subscriber(
        connection,
        mobile_number=request.mobile_number,
        identity_proof_ref=request.identity_proof_ref,
        plan_type=request.plan_type,
        registered_at=datetime.now(UTC),
    )
    token = create_access_token(
        Principal(
            user_id=subscription.mobile_number,
            role=Role.SUBSCRIBER,
            subscriber_id=subscription.subscriber_id,
        ),
        settings,
    )
    return RegisterSubscriberResponse(
        subscriber_id=subscription.subscriber_id,
        subscription_id=subscription.subscription_id,
        state=subscription.state,
        access_token=token,
    )


@router.post("/{subscriber_id}/activate", response_model=ActivateSubscriberResponse)
def activate(
    subscriber_id: str,
    request: ActivateSubscriberRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    settings: Settings = Depends(get_settings),
    _principal: Principal = Depends(require_own_subscriber),
) -> ActivateSubscriberResponse:
    """AC-2: all stub flags passing -> 200 ACTIVE. AC-3: a failing flag ->
    422 with its reason code. AC-4: already-ACTIVE -> 409. All three
    outcomes are mapped by error_handlers.py from the exceptions
    activate_subscriber raises — this handler has no try/except of its
    own.
    """
    subscription = activate_subscriber(
        connection, subscriber_id, request.dealer_code, settings, datetime.now(UTC)
    )
    assert subscription.activated_at is not None  # guaranteed on the success path
    return ActivateSubscriberResponse(
        subscriber_id=subscriber_id,
        state=subscription.state,
        activated_at=subscription.activated_at,
    )
