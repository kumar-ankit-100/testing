"""Unit tests for the port-out request service with 7-day cooling period
(E5-S3).
"""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.repository.state_transition_repository import list_state_transitions_for_subscription
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.service.port_out_service import (
    cancel_port_out,
    finalize_port_out,
    request_port_out,
)
from app.types.enums import PlanType, PortOutStatus, SubscriberState
from app.types.exceptions import CoolingPeriodNotElapsedError, InvalidSubscriberStateException
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)


def _register(
    connection: sqlite3.Connection, subscriber_id: str, mobile_number: str, state: SubscriberState
) -> str:
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-8801",
            created_at=_REGISTERED_AT,
        ),
    )
    subscription_id = f"subn-{subscriber_id}"
    create_subscription(
        connection,
        Subscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            plan_type=PlanType.POSTPAID,
            state=state,
            current_plan_version_id="PLAN-5G-v1",
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=_REGISTERED_AT if state != SubscriberState.PENDING_KYC else None,
            updated_at=_REGISTERED_AT,
        ),
    )
    return subscription_id


def test_requesting_port_out_on_active_transitions_and_creates_event(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-1."""
    subscription_id = _register(
        sqlite_connection, "port-sub-0001", "9876548801", SubscriberState.ACTIVE
    )
    requested_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)

    event = request_port_out(
        sqlite_connection, subscription_id, "subscriber:port-sub-0001", requested_at
    )

    assert event.status == PortOutStatus.PENDING
    assert event.cooling_period_end_at == requested_at + timedelta(days=7)
    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscription_id = ?", (subscription_id,)
    ).fetchone()
    assert row[0] == "PORT_OUT_REQUESTED"
    transitions = list_state_transitions_for_subscription(sqlite_connection, subscription_id)
    assert len(transitions) == 1
    assert transitions[0].to_state == SubscriberState.PORT_OUT_REQUESTED


def test_cancelling_within_window_returns_to_active_and_closes_event(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2."""
    subscription_id = _register(
        sqlite_connection, "port-sub-0002", "9876548802", SubscriberState.ACTIVE
    )
    requested_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    request_port_out(sqlite_connection, subscription_id, "subscriber:port-sub-0002", requested_at)
    cancelled_at = requested_at + timedelta(days=3)

    event = cancel_port_out(
        sqlite_connection, subscription_id, "subscriber:port-sub-0002", cancelled_at
    )

    assert event.status == PortOutStatus.CANCELLED_WITHIN_WINDOW
    assert event.closed_at == cancelled_at
    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscription_id = ?", (subscription_id,)
    ).fetchone()
    assert row[0] == "ACTIVE"


def test_finalizing_after_window_elapsed_transitions_to_ported_out(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-3."""
    subscription_id = _register(
        sqlite_connection, "port-sub-0003", "9876548803", SubscriberState.ACTIVE
    )
    requested_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    request_port_out(sqlite_connection, subscription_id, "subscriber:port-sub-0003", requested_at)
    finalized_at = requested_at + timedelta(days=7, seconds=1)

    event = finalize_port_out(
        sqlite_connection, subscription_id, "subscriber:port-sub-0003", finalized_at
    )

    assert event.status == PortOutStatus.FINALIZED
    assert event.closed_at == finalized_at
    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscription_id = ?", (subscription_id,)
    ).fetchone()
    assert row[0] == "PORTED_OUT"


def test_finalizing_before_window_elapsed_is_rejected(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-4."""
    subscription_id = _register(
        sqlite_connection, "port-sub-0004", "9876548804", SubscriberState.ACTIVE
    )
    requested_at = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    request_port_out(sqlite_connection, subscription_id, "subscriber:port-sub-0004", requested_at)
    too_early = requested_at + timedelta(days=6)

    with pytest.raises(CoolingPeriodNotElapsedError):
        finalize_port_out(
            sqlite_connection, subscription_id, "subscriber:port-sub-0004", too_early
        )

    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscription_id = ?", (subscription_id,)
    ).fetchone()
    assert row[0] == "PORT_OUT_REQUESTED"


@pytest.mark.parametrize(
    "state", [SubscriberState.PENDING_KYC, SubscriberState.SUSPENDED]
)
def test_requesting_port_out_on_a_non_active_subscription_raises_invalid_state_exception(
    sqlite_connection: sqlite3.Connection, state: SubscriberState
) -> None:
    """AC-5."""
    subscription_id = _register(sqlite_connection, f"port-sub-{state.value}", "9876548805", state)

    with pytest.raises(InvalidSubscriberStateException):
        request_port_out(sqlite_connection, subscription_id, "subscriber:x", datetime.now(UTC))


def test_request_port_out_raises_for_an_unknown_subscription_id(
    sqlite_connection: sqlite3.Connection,
) -> None:
    with pytest.raises(ValueError, match="No subscription found"):
        request_port_out(sqlite_connection, "does-not-exist", "subscriber:x", datetime.now(UTC))


def test_cancel_port_out_raises_when_no_active_port_out_event_exists(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """A subscription genuinely in PORT_OUT_REQUESTED with no locatable
    event is a data-integrity impossibility under normal flow, but the
    service must fail loudly rather than silently, if it ever happens."""
    subscription_id = _register(
        sqlite_connection, "port-sub-0006", "9876548806", SubscriberState.PORT_OUT_REQUESTED
    )

    with pytest.raises(ValueError, match="No active port-out event"):
        cancel_port_out(sqlite_connection, subscription_id, "subscriber:x", datetime.now(UTC))
