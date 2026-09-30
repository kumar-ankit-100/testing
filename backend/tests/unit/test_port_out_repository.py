"""Unit tests for port_out_repository (E5-S1)."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.repository.port_out_repository import (
    close_port_out_event,
    create_port_out_event,
    get_active_port_out_event,
)
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.enums import PlanType, PortOutStatus, SubscriberState
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_NOW = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)


@pytest.fixture
def subscription_id(sqlite_connection: sqlite3.Connection) -> str:
    subscriber = Subscriber(
        subscriber_id="d4e5f6a7-0020-4b11-9c22-333344445555",
        mobile_number="9876540301",
        identity_proof_ref="AADHAAR-XXXX-XXXX-3333",
        created_at=_NOW,
    )
    create_subscriber(sqlite_connection, subscriber)
    subscription = Subscription(
        subscription_id="e5f6a7b8-0020-4c22-9d33-444455556666",
        subscriber_id=subscriber.subscriber_id,
        mobile_number=subscriber.mobile_number,
        plan_type=PlanType.POSTPAID,
        state=SubscriberState.ACTIVE,
        current_plan_version_id="PLAN-5G-v1",
        dealer_code=None,
        created_at=_NOW,
        activated_at=_NOW,
        updated_at=_NOW,
    )
    create_subscription(sqlite_connection, subscription)
    return subscription.subscription_id


def test_create_port_out_event_stores_requested_at_and_seven_day_cooling_end(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    """AC-4: cooling_period_end_at is computed as exactly 7 days after requested_at."""
    event = create_port_out_event(sqlite_connection, subscription_id, _NOW)

    assert event.requested_at == _NOW
    assert event.cooling_period_end_at == _NOW + timedelta(days=7)
    assert event.status == PortOutStatus.PENDING
    assert event.closed_at is None


def test_get_active_port_out_event_finds_the_pending_event(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    created = create_port_out_event(sqlite_connection, subscription_id, _NOW)

    active = get_active_port_out_event(sqlite_connection, subscription_id)

    assert active == created


def test_get_active_port_out_event_returns_none_when_no_event_exists(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    assert get_active_port_out_event(sqlite_connection, subscription_id) is None


def test_close_port_out_event_sets_status_and_closed_at_without_deleting_the_row(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    """AC-2: closing sets an end status, it does not delete the row."""
    created = create_port_out_event(sqlite_connection, subscription_id, _NOW)
    closed_at = _NOW + timedelta(days=2)

    close_port_out_event(
        sqlite_connection,
        created.port_out_event_id,
        PortOutStatus.CANCELLED_WITHIN_WINDOW,
        closed_at,
    )

    row = sqlite_connection.execute(
        "SELECT status, closed_at FROM port_out_events WHERE port_out_event_id = ?",
        (created.port_out_event_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "CANCELLED_WITHIN_WINDOW"
    assert row[1] == closed_at.isoformat()


def test_get_active_port_out_event_returns_none_after_the_event_is_closed(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    created = create_port_out_event(sqlite_connection, subscription_id, _NOW)
    close_port_out_event(
        sqlite_connection,
        created.port_out_event_id,
        PortOutStatus.FINALIZED,
        _NOW + timedelta(days=7),
    )

    assert get_active_port_out_event(sqlite_connection, subscription_id) is None


def test_direct_delete_of_a_port_out_event_is_rejected(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    created = create_port_out_event(sqlite_connection, subscription_id, _NOW)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "DELETE FROM port_out_events WHERE port_out_event_id = ?",
            (created.port_out_event_id,),
        )
