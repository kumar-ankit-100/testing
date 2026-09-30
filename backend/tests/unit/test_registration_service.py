"""Unit tests for the subscriber self-registration service (E2-S2)."""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.repository.subscriber_repository import (
    create_subscriber,
    create_subscription,
    get_subscriber_by_id,
)
from app.service.registration_service import register_subscriber
from app.types.enums import PlanType, SubscriberState
from app.types.exceptions import DuplicateActiveSubscriptionError, InvalidMobileNumberError
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 4, 1, 10, 0, tzinfo=UTC)


def test_register_subscriber_creates_a_pending_kyc_subscription(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-1: valid inputs create a subscription in PENDING_KYC state."""
    subscription = register_subscriber(
        sqlite_connection,
        mobile_number="9876540501",
        identity_proof_ref="AADHAAR-XXXX-XXXX-5501",
        plan_type=PlanType.POSTPAID,
        registered_at=_REGISTERED_AT,
    )

    assert subscription.state == SubscriberState.PENDING_KYC
    assert subscription.plan_type == PlanType.POSTPAID
    assert subscription.mobile_number == "9876540501"


def test_register_subscriber_persists_subscriber_and_subscription_rows(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscription = register_subscriber(
        sqlite_connection,
        mobile_number="9876540502",
        identity_proof_ref="AADHAAR-XXXX-XXXX-5502",
        plan_type=PlanType.PREPAID,
        registered_at=_REGISTERED_AT,
    )

    persisted_subscriber = get_subscriber_by_id(sqlite_connection, subscription.subscriber_id)
    assert persisted_subscriber is not None
    assert persisted_subscriber.mobile_number == "9876540502"
    assert persisted_subscriber.identity_proof_ref == "AADHAAR-XXXX-XXXX-5502"

    row = sqlite_connection.execute(
        "SELECT COUNT(*) FROM subscriptions WHERE subscription_id = ?",
        (subscription.subscription_id,),
    ).fetchone()
    assert row[0] == 1


def test_register_subscriber_rejects_when_mobile_already_has_an_active_subscription(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2: rejected with a specific error, not a generic failure."""
    existing_subscriber = Subscriber(
        subscriber_id="e1f2a3b4-0001-4c11-9d22-333344445555",
        mobile_number="9876540503",
        identity_proof_ref="AADHAAR-XXXX-XXXX-5503",
        created_at=_REGISTERED_AT,
    )
    create_subscriber(sqlite_connection, existing_subscriber)
    create_subscription(
        sqlite_connection,
        Subscription(
            subscription_id="f2a3b4c5-0001-4d22-9e33-444455556666",
            subscriber_id=existing_subscriber.subscriber_id,
            mobile_number=existing_subscriber.mobile_number,
            plan_type=PlanType.POSTPAID,
            state=SubscriberState.ACTIVE,
            current_plan_version_id="PLAN-5G-v1",
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=_REGISTERED_AT,
            updated_at=_REGISTERED_AT,
        ),
    )

    with pytest.raises(DuplicateActiveSubscriptionError):
        register_subscriber(
            sqlite_connection,
            mobile_number="9876540503",
            identity_proof_ref="AADHAAR-XXXX-XXXX-9999",
            plan_type=PlanType.PREPAID,
            registered_at=_REGISTERED_AT,
        )

    subscriber_count = sqlite_connection.execute(
        "SELECT COUNT(*) FROM subscribers WHERE mobile_number = ?", ("9876540503",)
    ).fetchone()[0]
    assert subscriber_count == 1  # no new subscriber row was written


@pytest.mark.parametrize(
    "malformed_mobile_number",
    ["98765", "98765432101", "98765abcde", "", "+919876543210"],
)
def test_register_subscriber_rejects_malformed_mobile_number_before_any_write(
    sqlite_connection: sqlite3.Connection, malformed_mobile_number: str
) -> None:
    """AC-3: rejected before any database write."""
    with pytest.raises(InvalidMobileNumberError):
        register_subscriber(
            sqlite_connection,
            mobile_number=malformed_mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-0000",
            plan_type=PlanType.PREPAID,
            registered_at=_REGISTERED_AT,
        )

    subscriber_count = sqlite_connection.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
    assert subscriber_count == 0
    subscription_count = sqlite_connection.execute(
        "SELECT COUNT(*) FROM subscriptions"
    ).fetchone()[0]
    assert subscription_count == 0


def test_register_subscriber_persists_full_identity_proof_ref_but_masks_it_when_logged(
    sqlite_connection: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-4: full value persisted; only the masked form appears in logs."""
    raw_identity_proof_ref = "AADHAAR-XXXX-XXXX-5504"

    subscription = register_subscriber(
        sqlite_connection,
        mobile_number="9876540504",
        identity_proof_ref=raw_identity_proof_ref,
        plan_type=PlanType.POSTPAID,
        registered_at=_REGISTERED_AT,
    )

    persisted_subscriber = get_subscriber_by_id(sqlite_connection, subscription.subscriber_id)
    assert persisted_subscriber is not None
    assert persisted_subscriber.identity_proof_ref == raw_identity_proof_ref

    captured = capsys.readouterr().out
    assert raw_identity_proof_ref not in captured
    assert "******************5504" in captured
