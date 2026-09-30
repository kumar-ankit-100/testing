"""Unit tests for state_transition_repository (E5-S1)."""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.repository.state_transition_repository import (
    append_state_transition,
    list_state_transitions_for_subscription,
)
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.enums import PlanType, SubscriberState
from app.types.state_transition import StateTransition
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_NOW = datetime(2026, 3, 5, 8, 0, tzinfo=UTC)


@pytest.fixture
def subscription_id(sqlite_connection: sqlite3.Connection) -> str:
    subscriber = Subscriber(
        subscriber_id="a1b2c3d4-0010-4e11-9f22-333344445555",
        mobile_number="9876540201",
        identity_proof_ref="AADHAAR-XXXX-XXXX-2222",
        created_at=_NOW,
    )
    create_subscriber(sqlite_connection, subscriber)
    subscription = Subscription(
        subscription_id="b2c3d4e5-0010-4f22-9a33-444455556666",
        subscriber_id=subscriber.subscriber_id,
        mobile_number=subscriber.mobile_number,
        plan_type=PlanType.PREPAID,
        state=SubscriberState.PENDING_KYC,
        current_plan_version_id=None,
        dealer_code=None,
        created_at=_NOW,
        activated_at=None,
        updated_at=_NOW,
    )
    create_subscription(sqlite_connection, subscription)
    return subscription.subscription_id


def _build_transition(
    transition_id: str,
    subscription_id: str,
    from_state: SubscriberState,
    to_state: SubscriberState,
    created_at: datetime,
) -> StateTransition:
    return StateTransition(
        transition_id=transition_id,
        subscription_id=subscription_id,
        from_state=from_state,
        to_state=to_state,
        reason_code=None,
        actor="system:activation_service",
        created_at=created_at,
    )


def test_append_and_list_state_transition_round_trips(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    transition = _build_transition(
        "c3d4e5f6-0001-4a11-9b22-333344445555",
        subscription_id,
        SubscriberState.PENDING_KYC,
        SubscriberState.ACTIVE,
        _NOW,
    )

    append_state_transition(sqlite_connection, transition)
    transitions = list_state_transitions_for_subscription(sqlite_connection, subscription_id)

    assert transitions == [transition]


def test_three_appended_transitions_remain_retrievable_in_chronological_order(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    first = _build_transition(
        "c3d4e5f6-0002-4a11-9b22-333344445555",
        subscription_id,
        SubscriberState.PENDING_KYC,
        SubscriberState.ACTIVE,
        datetime(2026, 3, 5, 9, 0, tzinfo=UTC),
    )
    second = _build_transition(
        "c3d4e5f6-0003-4a11-9b22-333344445555",
        subscription_id,
        SubscriberState.ACTIVE,
        SubscriberState.SUSPENDED,
        datetime(2026, 3, 6, 9, 0, tzinfo=UTC),
    )
    third = _build_transition(
        "c3d4e5f6-0004-4a11-9b22-333344445555",
        subscription_id,
        SubscriberState.SUSPENDED,
        SubscriberState.ACTIVE,
        datetime(2026, 3, 7, 9, 0, tzinfo=UTC),
    )
    append_state_transition(sqlite_connection, first)
    append_state_transition(sqlite_connection, second)
    append_state_transition(sqlite_connection, third)

    transitions = list_state_transitions_for_subscription(sqlite_connection, subscription_id)

    assert [t.transition_id for t in transitions] == [
        first.transition_id,
        second.transition_id,
        third.transition_id,
    ]


def test_list_state_transitions_returns_empty_list_when_none_exist(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    assert list_state_transitions_for_subscription(sqlite_connection, subscription_id) == []


def test_state_transition_with_reason_code_round_trips(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    transition = StateTransition(
        transition_id="c3d4e5f6-0005-4a11-9b22-333344445555",
        subscription_id=subscription_id,
        from_state=SubscriberState.PENDING_KYC,
        to_state=SubscriberState.PENDING_KYC,
        reason_code="KYC_UNVERIFIED",
        actor="system:activation_service",
        created_at=_NOW,
    )
    append_state_transition(sqlite_connection, transition)

    transitions = list_state_transitions_for_subscription(sqlite_connection, subscription_id)

    assert transitions[0].reason_code == "KYC_UNVERIFIED"


def test_direct_update_of_a_state_transition_is_rejected(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    transition = _build_transition(
        "c3d4e5f6-0006-4a11-9b22-333344445555",
        subscription_id,
        SubscriberState.PENDING_KYC,
        SubscriberState.ACTIVE,
        _NOW,
    )
    append_state_transition(sqlite_connection, transition)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "UPDATE state_transitions SET actor = ? WHERE transition_id = ?",
            ("someone-else", transition.transition_id),
        )


def test_direct_delete_of_a_state_transition_is_rejected(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    transition = _build_transition(
        "c3d4e5f6-0007-4a11-9b22-333344445555",
        subscription_id,
        SubscriberState.PENDING_KYC,
        SubscriberState.ACTIVE,
        _NOW,
    )
    append_state_transition(sqlite_connection, transition)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "DELETE FROM state_transitions WHERE transition_id = ?",
            (transition.transition_id,),
        )
