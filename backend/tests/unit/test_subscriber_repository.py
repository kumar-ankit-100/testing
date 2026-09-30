"""Unit tests for subscriber_repository (E2-S1)."""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.repository.subscriber_repository import (
    activate_subscription,
    create_subscriber,
    create_subscription,
    get_active_subscription_by_mobile,
    get_subscriber_by_id,
    get_subscriber_by_mobile,
    get_subscription_by_subscriber_id,
)
from app.types.enums import PlanType, SubscriberState
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_NOW = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)


def _build_subscriber(subscriber_id: str, mobile_number: str) -> Subscriber:
    return Subscriber(
        subscriber_id=subscriber_id,
        mobile_number=mobile_number,
        identity_proof_ref="AADHAAR-XXXX-XXXX-4321",
        created_at=_NOW,
    )


def _build_subscription(
    subscription_id: str, subscriber_id: str, mobile_number: str, state: SubscriberState
) -> Subscription:
    return Subscription(
        subscription_id=subscription_id,
        subscriber_id=subscriber_id,
        mobile_number=mobile_number,
        plan_type=PlanType.PREPAID,
        state=state,
        current_plan_version_id=None,
        dealer_code=None,
        created_at=_NOW,
        activated_at=None,
        updated_at=_NOW,
    )


def test_create_and_get_subscriber_by_id_round_trips(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber = _build_subscriber("b1a2c3d4-0001-4e11-9f22-333344445555", "9876540001")

    create_subscriber(sqlite_connection, subscriber)
    fetched = get_subscriber_by_id(sqlite_connection, subscriber.subscriber_id)

    assert fetched == subscriber


def test_get_subscriber_by_id_returns_none_when_not_found(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_subscriber_by_id(sqlite_connection, "does-not-exist") is None


def test_get_subscriber_by_mobile_finds_the_matching_row(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber = _build_subscriber("b1a2c3d4-0002-4e11-9f22-333344445555", "9876540002")
    create_subscriber(sqlite_connection, subscriber)

    fetched = get_subscriber_by_mobile(sqlite_connection, "9876540002")

    assert fetched == subscriber


def test_get_subscriber_by_mobile_returns_none_when_not_found(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_subscriber_by_mobile(sqlite_connection, "9000000001") is None


def test_create_subscription_persists_a_pending_kyc_row(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber = _build_subscriber("b1a2c3d4-0003-4e11-9f22-333344445555", "9876540003")
    create_subscriber(sqlite_connection, subscriber)
    subscription = _build_subscription(
        "c2b3d4e5-0001-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.PENDING_KYC,
    )

    create_subscription(sqlite_connection, subscription)

    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscription_id = ?",
        (subscription.subscription_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "PENDING_KYC"


def test_second_active_subscription_for_same_mobile_raises_integrity_error(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-4 (double-activation race guard): the partial unique index on
    subscriptions(mobile_number) WHERE state='ACTIVE' rejects a second
    ACTIVE row for the same mobile number at the database level.
    """
    subscriber = _build_subscriber("b1a2c3d4-0004-4e11-9f22-333344445555", "9876540004")
    create_subscriber(sqlite_connection, subscriber)
    first_active = _build_subscription(
        "c2b3d4e5-0002-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.ACTIVE,
    )
    second_active = _build_subscription(
        "c2b3d4e5-0003-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.ACTIVE,
    )
    create_subscription(sqlite_connection, first_active)

    with pytest.raises(sqlite3.IntegrityError):
        create_subscription(sqlite_connection, second_active)


def test_non_active_subscriptions_for_same_mobile_do_not_conflict(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """The unique index is partial (WHERE state='ACTIVE') — two non-ACTIVE
    rows for the same mobile number (e.g. a re-registration attempt still
    pending KYC) must not collide.
    """
    subscriber = _build_subscriber("b1a2c3d4-0005-4e11-9f22-333344445555", "9876540005")
    create_subscriber(sqlite_connection, subscriber)
    first_pending = _build_subscription(
        "c2b3d4e5-0004-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.PENDING_KYC,
    )
    second_pending = _build_subscription(
        "c2b3d4e5-0005-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.PENDING_KYC,
    )

    create_subscription(sqlite_connection, first_pending)
    create_subscription(sqlite_connection, second_pending)

    count_row = sqlite_connection.execute(
        "SELECT COUNT(*) FROM subscriptions WHERE mobile_number = ?",
        (subscriber.mobile_number,),
    ).fetchone()
    assert count_row[0] == 2


def test_get_active_subscription_by_mobile_finds_the_active_row(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber = _build_subscriber("b1a2c3d4-0006-4e11-9f22-333344445555", "9876540006")
    create_subscriber(sqlite_connection, subscriber)
    active = _build_subscription(
        "c2b3d4e5-0006-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.ACTIVE,
    )
    create_subscription(sqlite_connection, active)

    found = get_active_subscription_by_mobile(sqlite_connection, subscriber.mobile_number)

    assert found == active


def test_get_active_subscription_by_mobile_returns_none_when_only_pending(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber = _build_subscriber("b1a2c3d4-0007-4e11-9f22-333344445555", "9876540007")
    create_subscriber(sqlite_connection, subscriber)
    pending = _build_subscription(
        "c2b3d4e5-0007-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.PENDING_KYC,
    )
    create_subscription(sqlite_connection, pending)

    assert get_active_subscription_by_mobile(sqlite_connection, subscriber.mobile_number) is None


def test_get_active_subscription_by_mobile_returns_none_when_no_subscription_exists(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_active_subscription_by_mobile(sqlite_connection, "9000000009") is None


def test_get_active_subscription_by_mobile_round_trips_a_real_activated_at(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber = _build_subscriber("b1a2c3d4-0008-4e11-9f22-333344445555", "9876540008")
    create_subscriber(sqlite_connection, subscriber)
    active = Subscription(
        subscription_id="c2b3d4e5-0008-4f22-8a33-444455556666",
        subscriber_id=subscriber.subscriber_id,
        mobile_number=subscriber.mobile_number,
        plan_type=PlanType.POSTPAID,
        state=SubscriberState.ACTIVE,
        current_plan_version_id="PLAN-5G-v1",
        dealer_code="DLR-BLR-001",
        created_at=_NOW,
        activated_at=_NOW,
        updated_at=_NOW,
    )
    create_subscription(sqlite_connection, active)

    found = get_active_subscription_by_mobile(sqlite_connection, subscriber.mobile_number)

    assert found == active
    assert found is not None
    assert found.activated_at == _NOW


def test_get_subscription_by_subscriber_id_finds_the_matching_row(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber = _build_subscriber("b1a2c3d4-0009-4e11-9f22-333344445555", "9876540009")
    create_subscriber(sqlite_connection, subscriber)
    subscription = _build_subscription(
        "c2b3d4e5-0009-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.PENDING_KYC,
    )
    create_subscription(sqlite_connection, subscription)

    found = get_subscription_by_subscriber_id(sqlite_connection, subscriber.subscriber_id)

    assert found == subscription


def test_get_subscription_by_subscriber_id_returns_none_when_not_found(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_subscription_by_subscriber_id(sqlite_connection, "does-not-exist") is None


def test_activate_subscription_sets_active_state_and_timestamps(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber = _build_subscriber("b1a2c3d4-0010-4e11-9f22-333344445555", "9876540010")
    create_subscriber(sqlite_connection, subscriber)
    subscription = _build_subscription(
        "c2b3d4e5-0010-4f22-8a33-444455556666",
        subscriber.subscriber_id,
        subscriber.mobile_number,
        SubscriberState.PENDING_KYC,
    )
    create_subscription(sqlite_connection, subscription)
    activated_at = datetime(2026, 2, 2, 10, 0, tzinfo=UTC)

    activate_subscription(sqlite_connection, subscription.subscription_id, activated_at)

    reloaded = get_subscription_by_subscriber_id(sqlite_connection, subscriber.subscriber_id)
    assert reloaded is not None
    assert reloaded.state == SubscriberState.ACTIVE
    assert reloaded.activated_at == activated_at
    assert reloaded.updated_at == activated_at


def test_activate_subscription_raises_integrity_error_for_a_second_active_mobile(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """The partial unique index also guards UPDATE, not just INSERT — this
    is the mechanism behind E2-S3 AC-6's double-activation race guard.
    """
    subscriber_a = _build_subscriber("b1a2c3d4-0011-4e11-9f22-333344445555", "9876540011")
    create_subscriber(sqlite_connection, subscriber_a)
    subscription_a = _build_subscription(
        "c2b3d4e5-0011-4f22-8a33-444455556666",
        subscriber_a.subscriber_id,
        subscriber_a.mobile_number,
        SubscriberState.ACTIVE,
    )
    create_subscription(sqlite_connection, subscription_a)

    subscriber_b = _build_subscriber("b1a2c3d4-0012-4e11-9f22-333344445555", "9876540011")
    create_subscriber(sqlite_connection, subscriber_b)
    subscription_b = _build_subscription(
        "c2b3d4e5-0012-4f22-8a33-444455556666",
        subscriber_b.subscriber_id,
        subscriber_b.mobile_number,
        SubscriberState.PENDING_KYC,
    )
    create_subscription(sqlite_connection, subscription_b)

    with pytest.raises(sqlite3.IntegrityError):
        activate_subscription(sqlite_connection, subscription_b.subscription_id, _NOW)
