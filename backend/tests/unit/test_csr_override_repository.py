"""Unit tests for csr_override_repository (E6-S1)."""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.repository.csr_override_repository import (
    create_csr_override,
    list_csr_overrides_for_subscription,
)
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.csr_override import CSROverride
from app.types.enums import OverriddenAction, PlanType, SubscriberState
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_NOW = datetime(2026, 3, 15, 14, 0, tzinfo=UTC)


@pytest.fixture
def subscription_id(sqlite_connection: sqlite3.Connection) -> str:
    subscriber = Subscriber(
        subscriber_id="f6a7b8c9-0030-4b11-9c22-333344445555",
        mobile_number="9876540401",
        identity_proof_ref="AADHAAR-XXXX-XXXX-4444",
        created_at=_NOW,
    )
    create_subscriber(sqlite_connection, subscriber)
    subscription = Subscription(
        subscription_id="a7b8c9d0-0030-4c22-9d33-444455556666",
        subscriber_id=subscriber.subscriber_id,
        mobile_number=subscriber.mobile_number,
        plan_type=PlanType.PREPAID,
        state=SubscriberState.PENDING_KYC,
        current_plan_version_id=None,
        dealer_code="DEALER-FAIL",
        created_at=_NOW,
        activated_at=None,
        updated_at=_NOW,
    )
    create_subscription(sqlite_connection, subscription)
    return subscription.subscription_id


def _build_override(override_id: str, subscription_id: str, actor: str) -> CSROverride:
    return CSROverride(
        override_id=override_id,
        subscription_id=subscription_id,
        actor=actor,
        reason_code="GOODWILL_EXCEPTION",
        overridden_action=OverriddenAction.ACTIVATION,
        original_rejection_reason="DEALER_INVALID",
        created_at=_NOW,
    )


def test_create_and_list_csr_override_round_trips(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    override = _build_override(
        "b8c9d0e1-0001-4a11-9b22-333344445555", subscription_id, "csr:agent-42"
    )

    create_csr_override(sqlite_connection, override)
    overrides = list_csr_overrides_for_subscription(sqlite_connection, subscription_id)

    assert overrides == [override]


def test_every_override_has_non_null_actor_reason_code_and_timestamp(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    override = _build_override(
        "b8c9d0e1-0002-4a11-9b22-333344445555", subscription_id, "csr:agent-07"
    )
    create_csr_override(sqlite_connection, override)

    fetched = list_csr_overrides_for_subscription(sqlite_connection, subscription_id)[0]

    assert fetched.actor
    assert fetched.reason_code
    assert fetched.created_at is not None


def test_two_overrides_for_the_same_subscription_both_remain_retrievable(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    first = _build_override(
        "b8c9d0e1-0003-4a11-9b22-333344445555", subscription_id, "csr:agent-42"
    )
    second = CSROverride(
        override_id="b8c9d0e1-0004-4a11-9b22-333344445555",
        subscription_id=subscription_id,
        actor="csr:agent-88",
        reason_code="MIN_TENURE_WAIVER",
        overridden_action=OverriddenAction.PLAN_CHANGE,
        original_rejection_reason="MIN_TENURE_NOT_MET",
        created_at=_NOW,
    )

    create_csr_override(sqlite_connection, first)
    create_csr_override(sqlite_connection, second)

    overrides = list_csr_overrides_for_subscription(sqlite_connection, subscription_id)
    assert {o.override_id for o in overrides} == {first.override_id, second.override_id}
    assert {o.overridden_action for o in overrides} == {
        OverriddenAction.ACTIVATION,
        OverriddenAction.PLAN_CHANGE,
    }


def test_list_csr_overrides_returns_empty_list_when_none_exist(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    assert list_csr_overrides_for_subscription(sqlite_connection, subscription_id) == []


def test_direct_update_of_a_csr_override_is_rejected(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    override = _build_override(
        "b8c9d0e1-0005-4a11-9b22-333344445555", subscription_id, "csr:agent-42"
    )
    create_csr_override(sqlite_connection, override)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "UPDATE csr_overrides SET actor = ? WHERE override_id = ?",
            ("someone-else", override.override_id),
        )


def test_direct_delete_of_a_csr_override_is_rejected(
    sqlite_connection: sqlite3.Connection, subscription_id: str
) -> None:
    override = _build_override(
        "b8c9d0e1-0006-4a11-9b22-333344445555", subscription_id, "csr:agent-42"
    )
    create_csr_override(sqlite_connection, override)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "DELETE FROM csr_overrides WHERE override_id = ?", (override.override_id,)
        )
