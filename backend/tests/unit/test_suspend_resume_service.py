"""Unit tests for the suspend/resume service (E5-S2)."""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.repository.state_transition_repository import list_state_transitions_for_subscription
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.service.suspend_resume_service import resume_subscription, suspend_subscription
from app.types.enums import PlanType, SubscriberState
from app.types.exceptions import InvalidSubscriberStateException
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)


def _register(
    connection: sqlite3.Connection, subscriber_id: str, mobile_number: str, state: SubscriberState
) -> str:
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-7701",
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


def test_suspending_an_active_subscription_transitions_to_suspended(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-1."""
    subscription_id = _register(
        sqlite_connection, "susp-sub-0001", "9876547701", SubscriberState.ACTIVE
    )
    suspended_at = datetime(2026, 4, 2, 10, 0, tzinfo=UTC)

    result = suspend_subscription(
        sqlite_connection, subscription_id, "subscriber:susp-sub-0001", suspended_at
    )

    assert result.state == SubscriberState.SUSPENDED
    transitions = list_state_transitions_for_subscription(sqlite_connection, subscription_id)
    assert len(transitions) == 1
    assert transitions[0].from_state == SubscriberState.ACTIVE
    assert transitions[0].to_state == SubscriberState.SUSPENDED


def test_resuming_a_suspended_subscription_transitions_to_active(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2."""
    subscription_id = _register(
        sqlite_connection, "susp-sub-0002", "9876547702", SubscriberState.SUSPENDED
    )
    resumed_at = datetime(2026, 4, 3, 11, 0, tzinfo=UTC)

    result = resume_subscription(
        sqlite_connection, subscription_id, "subscriber:susp-sub-0002", resumed_at
    )

    assert result.state == SubscriberState.ACTIVE
    transitions = list_state_transitions_for_subscription(sqlite_connection, subscription_id)
    assert len(transitions) == 1
    assert transitions[0].from_state == SubscriberState.SUSPENDED
    assert transitions[0].to_state == SubscriberState.ACTIVE


@pytest.mark.parametrize("state", [SubscriberState.SUSPENDED, SubscriberState.PENDING_KYC])
def test_suspending_a_non_active_subscription_raises_invalid_state_exception(
    sqlite_connection: sqlite3.Connection, state: SubscriberState
) -> None:
    """AC-3."""
    subscription_id = _register(sqlite_connection, f"susp-sub-{state.value}", "9876547703", state)

    with pytest.raises(InvalidSubscriberStateException):
        suspend_subscription(
            sqlite_connection, subscription_id, "subscriber:x", datetime.now(UTC)
        )


@pytest.mark.parametrize("state", [SubscriberState.ACTIVE, SubscriberState.PENDING_KYC])
def test_resuming_a_non_suspended_subscription_raises_invalid_state_exception(
    sqlite_connection: sqlite3.Connection, state: SubscriberState
) -> None:
    """AC-4."""
    subscription_id = _register(sqlite_connection, f"resume-sub-{state.value}", "9876547704", state)

    with pytest.raises(InvalidSubscriberStateException):
        resume_subscription(
            sqlite_connection, subscription_id, "subscriber:x", datetime.now(UTC)
        )


def test_suspend_subscription_raises_for_an_unknown_subscription_id(
    sqlite_connection: sqlite3.Connection,
) -> None:
    with pytest.raises(ValueError, match="No subscription found"):
        suspend_subscription(sqlite_connection, "does-not-exist", "subscriber:x", datetime.now(UTC))
