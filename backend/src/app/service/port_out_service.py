"""Port-out request service with a 7-day cooling period (E5-S3).

Service layer — imports Types, Config, Repository.
"""

import sqlite3
import uuid
from datetime import datetime

from app.repository.port_out_repository import (
    close_port_out_event,
    create_port_out_event,
    get_active_port_out_event,
)
from app.repository.state_transition_repository import append_state_transition
from app.repository.subscriber_repository import get_subscription_by_id, update_subscription_state
from app.types.enums import PortOutStatus, SubscriberState
from app.types.exceptions import CoolingPeriodNotElapsedError
from app.types.fsm import transition
from app.types.port_out import PortOutEvent
from app.types.state_transition import StateTransition
from app.types.subscription import Subscription


def request_port_out(
    connection: sqlite3.Connection, subscription_id: str, actor: str, requested_at: datetime
) -> PortOutEvent:
    """Transition an ACTIVE subscription to PORT_OUT_REQUESTED, creating a
    PortOutEvent with a 7-day cooling window (AC-1).

    Raises InvalidSubscriberStateException if not currently ACTIVE (AC-5).
    """
    subscription = _get_subscription_or_raise(connection, subscription_id)
    transition(subscription.state, SubscriberState.PORT_OUT_REQUESTED)

    event = create_port_out_event(connection, subscription_id, requested_at)
    update_subscription_state(
        connection, subscription_id, SubscriberState.PORT_OUT_REQUESTED, requested_at
    )
    _log_transition(
        connection, subscription_id, subscription.state, SubscriberState.PORT_OUT_REQUESTED,
        actor, requested_at,
    )
    return event


def cancel_port_out(
    connection: sqlite3.Connection, subscription_id: str, actor: str, cancelled_at: datetime
) -> PortOutEvent:
    """Cancel a pending port-out within the cooling window, returning the
    subscription to ACTIVE (AC-2).
    """
    subscription = _get_subscription_or_raise(connection, subscription_id)
    transition(subscription.state, SubscriberState.ACTIVE)

    event = _get_active_event_or_raise(connection, subscription_id)
    close_port_out_event(
        connection, event.port_out_event_id, PortOutStatus.CANCELLED_WITHIN_WINDOW, cancelled_at
    )
    update_subscription_state(connection, subscription_id, SubscriberState.ACTIVE, cancelled_at)
    _log_transition(
        connection, subscription_id, subscription.state, SubscriberState.ACTIVE, actor, cancelled_at
    )

    return _closed_event(event, PortOutStatus.CANCELLED_WITHIN_WINDOW, cancelled_at)


def finalize_port_out(
    connection: sqlite3.Connection, subscription_id: str, actor: str, finalized_at: datetime
) -> PortOutEvent:
    """Finalize a port-out after its cooling window has elapsed,
    transitioning the subscription to PORTED_OUT (AC-3).

    Raises CoolingPeriodNotElapsedError if called too early (AC-4).
    """
    subscription = _get_subscription_or_raise(connection, subscription_id)
    transition(subscription.state, SubscriberState.PORTED_OUT)

    event = _get_active_event_or_raise(connection, subscription_id)
    if finalized_at < event.cooling_period_end_at:
        raise CoolingPeriodNotElapsedError(subscription_id)

    close_port_out_event(connection, event.port_out_event_id, PortOutStatus.FINALIZED, finalized_at)
    update_subscription_state(connection, subscription_id, SubscriberState.PORTED_OUT, finalized_at)
    _log_transition(
        connection, subscription_id, subscription.state, SubscriberState.PORTED_OUT, actor,
        finalized_at,
    )

    return _closed_event(event, PortOutStatus.FINALIZED, finalized_at)


def _get_subscription_or_raise(
    connection: sqlite3.Connection, subscription_id: str
) -> Subscription:
    subscription = get_subscription_by_id(connection, subscription_id)
    if subscription is None:
        raise ValueError(f"No subscription found for subscription_id {subscription_id!r}")
    return subscription


def _get_active_event_or_raise(
    connection: sqlite3.Connection, subscription_id: str
) -> PortOutEvent:
    event = get_active_port_out_event(connection, subscription_id)
    if event is None:
        raise ValueError(f"No active port-out event found for subscription_id {subscription_id!r}")
    return event


def _closed_event(
    event: PortOutEvent, status: PortOutStatus, closed_at: datetime
) -> PortOutEvent:
    return PortOutEvent(
        port_out_event_id=event.port_out_event_id,
        subscription_id=event.subscription_id,
        requested_at=event.requested_at,
        cooling_period_end_at=event.cooling_period_end_at,
        status=status,
        closed_at=closed_at,
    )


def _log_transition(
    connection: sqlite3.Connection,
    subscription_id: str,
    from_state: SubscriberState,
    to_state: SubscriberState,
    actor: str,
    created_at: datetime,
) -> None:
    append_state_transition(
        connection,
        StateTransition(
            transition_id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            from_state=from_state,
            to_state=to_state,
            reason_code=None,
            actor=actor,
            created_at=created_at,
        ),
    )
