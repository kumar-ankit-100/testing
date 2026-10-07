"""Suspend/resume + port-out API endpoints (E5-S4).

API layer — imports Types, Config, Repository, Service. Ownership is
enforced the same way as plan_change_router: subscriber principals may
only act on their own subscription_id, staff roles pass through
unchecked.
"""

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import current_principal, get_db_connection
from app.api.schemas.lifecycle_schemas import (
    LifecycleStateResponse,
    PortOutEventResponse,
    TerminateRequest,
)
from app.repository.subscriber_repository import get_subscription_by_id
from app.service.port_out_service import cancel_port_out, finalize_port_out, request_port_out
from app.service.suspend_resume_service import resume_subscription, suspend_subscription
from app.service.termination_service import terminate_subscription
from app.types.auth import Principal
from app.types.enums import Role, SubscriberState
from app.types.exceptions import AuthorizationError
from app.types.port_out import PortOutEvent

router = APIRouter(prefix="/api/subscriptions", tags=["lifecycle"])


def _require_own_subscription(
    connection: sqlite3.Connection, subscription_id: str, principal: Principal
) -> None:
    if principal.role != Role.SUBSCRIBER:
        return
    subscription = get_subscription_by_id(connection, subscription_id)
    if subscription is None or subscription.subscriber_id != principal.subscriber_id:
        raise AuthorizationError("Subscribers may only access their own subscription data")


def _actor(principal: Principal) -> str:
    return f"{principal.role.value}:{principal.user_id}"


@router.post("/{subscription_id}/suspend", response_model=LifecycleStateResponse)
def suspend(
    subscription_id: str,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(current_principal),
) -> LifecycleStateResponse:
    """AC-1."""
    _require_own_subscription(connection, subscription_id, principal)
    subscription = suspend_subscription(
        connection, subscription_id, _actor(principal), datetime.now(UTC)
    )
    return LifecycleStateResponse(
        subscription_id=subscription.subscription_id, state=subscription.state
    )


@router.post("/{subscription_id}/resume", response_model=LifecycleStateResponse)
def resume(
    subscription_id: str,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(current_principal),
) -> LifecycleStateResponse:
    """AC-2."""
    _require_own_subscription(connection, subscription_id, principal)
    subscription = resume_subscription(
        connection, subscription_id, _actor(principal), datetime.now(UTC)
    )
    return LifecycleStateResponse(
        subscription_id=subscription.subscription_id, state=subscription.state
    )


@router.post("/{subscription_id}/port-out/request", response_model=PortOutEventResponse)
def port_out_request(
    subscription_id: str,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(current_principal),
) -> PortOutEventResponse:
    """AC-3."""
    _require_own_subscription(connection, subscription_id, principal)
    event = request_port_out(connection, subscription_id, _actor(principal), datetime.now(UTC))
    return _event_response(event)


@router.post("/{subscription_id}/port-out/cancel", response_model=LifecycleStateResponse)
def port_out_cancel(
    subscription_id: str,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(current_principal),
) -> LifecycleStateResponse:
    """AC-4."""
    _require_own_subscription(connection, subscription_id, principal)
    cancel_port_out(connection, subscription_id, _actor(principal), datetime.now(UTC))
    return LifecycleStateResponse(subscription_id=subscription_id, state=SubscriberState.ACTIVE)


@router.post("/{subscription_id}/port-out/finalize", response_model=PortOutEventResponse)
def port_out_finalize(
    subscription_id: str,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(current_principal),
) -> PortOutEventResponse:
    """AC-5."""
    _require_own_subscription(connection, subscription_id, principal)
    event = finalize_port_out(connection, subscription_id, _actor(principal), datetime.now(UTC))
    return _event_response(event)


@router.post("/{subscription_id}/terminate", response_model=LifecycleStateResponse)
def terminate(
    subscription_id: str,
    request: TerminateRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    principal: Principal = Depends(current_principal),
) -> LifecycleStateResponse:
    """E6-S6: CSR/admin-only termination. termination_service itself
    enforces the CSR-or-ADMIN role check and raises ValueError for an
    unknown subscription_id — checked here first so that case maps to a
    clean 404 rather than an unhandled 500 (termination_service.py has no
    typed not-found exception of its own; see its module docstring).
    """
    if get_subscription_by_id(connection, subscription_id) is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription = terminate_subscription(
        connection, principal, subscription_id, request.reason_code, datetime.now(UTC)
    )
    return LifecycleStateResponse(
        subscription_id=subscription.subscription_id, state=subscription.state
    )


def _event_response(event: PortOutEvent) -> PortOutEventResponse:
    return PortOutEventResponse(
        port_out_event_id=event.port_out_event_id,
        subscription_id=event.subscription_id,
        requested_at=event.requested_at,
        cooling_period_end_at=event.cooling_period_end_at,
        status=event.status.value,
    )
