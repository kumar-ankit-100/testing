"""Unit tests for the plan change service (E4-S3)."""

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.config.settings import Settings
from app.repository.billing_repository import list_billing_records_for_subscription
from app.repository.plan_repository import create_plan_version, publish_plan_version
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.service.plan_change_service import commit_plan_change, preview_plan_change
from app.types.enums import PlanType, SubscriberState
from app.types.exceptions import (
    MinTenureNotMetError,
    SubscriptionNotActiveError,
    SubscriptionSuspendedError,
)
from app.types.plan import PlanVersion
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
_FROM_PLAN_ID = "FROM-PLAN-5G-v1"
_TO_PLAN_ID = "TO-PLAN-5G-v1"


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, min_tenure_days=90)


def _seed_plans(connection: sqlite3.Connection) -> None:
    from_plan = PlanVersion(
        plan_version_id=_FROM_PLAN_ID,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        version_number=1,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        published=False,
        created_at=_REGISTERED_AT,
        published_at=None,
    )
    to_plan = PlanVersion(
        plan_version_id=_TO_PLAN_ID,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid Pro",
        plan_type=PlanType.POSTPAID,
        version_number=2,
        price=Decimal("999.00"),
        terms={"data_gb": 200},
        published=False,
        created_at=_REGISTERED_AT,
        published_at=None,
    )
    create_plan_version(connection, from_plan)
    create_plan_version(connection, to_plan)
    publish_plan_version(connection, _FROM_PLAN_ID, _REGISTERED_AT)
    publish_plan_version(connection, _TO_PLAN_ID, _REGISTERED_AT)


def _register_active(
    connection: sqlite3.Connection, subscriber_id: str, mobile_number: str, activated_at: datetime
) -> str:
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-9901",
            created_at=activated_at,
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
            state=SubscriberState.ACTIVE,
            current_plan_version_id=_FROM_PLAN_ID,
            dealer_code=None,
            created_at=activated_at,
            activated_at=activated_at,
            updated_at=activated_at,
        ),
    )
    return subscription_id


def test_plan_change_below_minimum_tenure_is_rejected_with_no_billing_record(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    """AC-1."""
    _seed_plans(sqlite_connection)
    activated_at = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    subscription_id = _register_active(sqlite_connection, "pc-sub-0001", "9876549901", activated_at)
    change_at = activated_at + timedelta(days=10)  # well under 90-day minimum

    with pytest.raises(MinTenureNotMetError):
        commit_plan_change(sqlite_connection, subscription_id, _TO_PLAN_ID, change_at, settings)

    assert list_billing_records_for_subscription(sqlite_connection, subscription_id) == []


def test_plan_change_on_a_suspended_subscription_is_rejected_with_no_billing_record(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    """AC-2."""
    _seed_plans(sqlite_connection)
    activated_at = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id = _register_active(sqlite_connection, "pc-sub-0002", "9876549902", activated_at)
    sqlite_connection.execute(
        "UPDATE subscriptions SET state = 'SUSPENDED' WHERE subscription_id = ?",
        (subscription_id,),
    )
    sqlite_connection.commit()
    change_at = activated_at + timedelta(days=120)

    with pytest.raises(SubscriptionSuspendedError):
        commit_plan_change(sqlite_connection, subscription_id, _TO_PLAN_ID, change_at, settings)

    assert list_billing_records_for_subscription(sqlite_connection, subscription_id) == []


def test_preview_returns_pro_rata_without_persisting_or_changing_plan(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    """AC-3."""
    _seed_plans(sqlite_connection)
    activated_at = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id = _register_active(sqlite_connection, "pc-sub-0003", "9876549903", activated_at)
    change_at = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)

    amount = preview_plan_change(
        sqlite_connection, subscription_id, _TO_PLAN_ID, change_at, settings
    )

    assert isinstance(amount, Decimal)
    assert amount > Decimal("0.00")
    assert list_billing_records_for_subscription(sqlite_connection, subscription_id) == []
    row = sqlite_connection.execute(
        "SELECT current_plan_version_id FROM subscriptions WHERE subscription_id = ?",
        (subscription_id,),
    ).fetchone()
    assert row[0] == _FROM_PLAN_ID


def test_commit_on_an_eligible_subscription_updates_plan_and_persists_matching_billing_record(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    """AC-4."""
    _seed_plans(sqlite_connection)
    activated_at = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id = _register_active(sqlite_connection, "pc-sub-0004", "9876549904", activated_at)
    change_at = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
    previewed = preview_plan_change(
        sqlite_connection, subscription_id, _TO_PLAN_ID, change_at, settings
    )

    record = commit_plan_change(
        sqlite_connection, subscription_id, _TO_PLAN_ID, change_at, settings
    )

    assert record.pro_rata_amount == previewed
    assert record.charges_total == previewed
    row = sqlite_connection.execute(
        "SELECT current_plan_version_id FROM subscriptions WHERE subscription_id = ?",
        (subscription_id,),
    ).fetchone()
    assert row[0] == _TO_PLAN_ID
    records = list_billing_records_for_subscription(sqlite_connection, subscription_id)
    assert len(records) == 1
    assert records[0] == record


def test_two_consecutive_commits_each_produce_an_independent_billing_record(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    """AC-5."""
    _seed_plans(sqlite_connection)
    activated_at = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id = _register_active(sqlite_connection, "pc-sub-0005", "9876549905", activated_at)
    first_change_at = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
    second_change_at = datetime(2026, 7, 20, 11, 0, tzinfo=UTC)

    first_record = commit_plan_change(
        sqlite_connection, subscription_id, _TO_PLAN_ID, first_change_at, settings
    )
    second_record = commit_plan_change(
        sqlite_connection, subscription_id, _FROM_PLAN_ID, second_change_at, settings
    )

    records = list_billing_records_for_subscription(sqlite_connection, subscription_id)
    assert len(records) == 2
    assert {r.billing_record_id for r in records} == {
        first_record.billing_record_id,
        second_record.billing_record_id,
    }
    reloaded_first = next(
        r for r in records if r.billing_record_id == first_record.billing_record_id
    )
    assert reloaded_first.pro_rata_amount == first_record.pro_rata_amount  # never modified


def test_plan_change_raises_for_an_unknown_subscription_id(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    with pytest.raises(ValueError, match="No subscription found"):
        preview_plan_change(
            sqlite_connection, "does-not-exist", _TO_PLAN_ID, datetime.now(UTC), settings
        )


def test_plan_change_on_a_pending_kyc_subscription_raises_not_active_error(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    """Neither ACTIVE nor SUSPENDED — e.g. still PENDING_KYC."""
    _seed_plans(sqlite_connection)
    create_subscriber(
        sqlite_connection,
        Subscriber(
            subscriber_id="pc-sub-0006",
            mobile_number="9876549906",
            identity_proof_ref="AADHAAR-XXXX-XXXX-9906",
            created_at=_REGISTERED_AT,
        ),
    )
    subscription_id = "subn-pc-sub-0006"
    create_subscription(
        sqlite_connection,
        Subscription(
            subscription_id=subscription_id,
            subscriber_id="pc-sub-0006",
            mobile_number="9876549906",
            plan_type=PlanType.POSTPAID,
            state=SubscriberState.PENDING_KYC,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=None,
            updated_at=_REGISTERED_AT,
        ),
    )

    with pytest.raises(SubscriptionNotActiveError):
        preview_plan_change(
            sqlite_connection, subscription_id, _TO_PLAN_ID, datetime.now(UTC), settings
        )


def test_plan_change_raises_when_target_plan_version_does_not_exist(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    _seed_plans(sqlite_connection)
    activated_at = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id = _register_active(sqlite_connection, "pc-sub-0007", "9876549907", activated_at)
    change_at = activated_at + timedelta(days=120)

    with pytest.raises(ValueError, match="not found"):
        preview_plan_change(
            sqlite_connection, subscription_id, "does-not-exist", change_at, settings
        )


def test_plan_change_on_an_active_subscription_with_no_activated_at_raises(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    """Data-integrity impossibility under normal flow (an ACTIVE
    subscription always has activated_at set by activation_service), but
    the service must fail loudly rather than silently if it ever happens.
    """
    _seed_plans(sqlite_connection)
    create_subscriber(
        sqlite_connection,
        Subscriber(
            subscriber_id="pc-sub-0008",
            mobile_number="9876549908",
            identity_proof_ref="AADHAAR-XXXX-XXXX-9908",
            created_at=_REGISTERED_AT,
        ),
    )
    subscription_id = "subn-pc-sub-0008"
    create_subscription(
        sqlite_connection,
        Subscription(
            subscription_id=subscription_id,
            subscriber_id="pc-sub-0008",
            mobile_number="9876549908",
            plan_type=PlanType.POSTPAID,
            state=SubscriberState.ACTIVE,
            current_plan_version_id=_FROM_PLAN_ID,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=None,
            updated_at=_REGISTERED_AT,
        ),
    )

    with pytest.raises(ValueError, match="no activated_at"):
        preview_plan_change(
            sqlite_connection, subscription_id, _TO_PLAN_ID, datetime.now(UTC), settings
        )


def test_plan_change_on_a_subscription_with_no_current_plan_version_raises(
    sqlite_connection: sqlite3.Connection, settings: Settings
) -> None:
    """Another data-integrity-impossibility defensive case: ACTIVE, past
    minimum tenure, but current_plan_version_id somehow unset."""
    _seed_plans(sqlite_connection)
    activated_at = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    create_subscriber(
        sqlite_connection,
        Subscriber(
            subscriber_id="pc-sub-0009",
            mobile_number="9876549909",
            identity_proof_ref="AADHAAR-XXXX-XXXX-9909",
            created_at=activated_at,
        ),
    )
    subscription_id = "subn-pc-sub-0009"
    create_subscription(
        sqlite_connection,
        Subscription(
            subscription_id=subscription_id,
            subscriber_id="pc-sub-0009",
            mobile_number="9876549909",
            plan_type=PlanType.POSTPAID,
            state=SubscriberState.ACTIVE,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=activated_at,
            activated_at=activated_at,
            updated_at=activated_at,
        ),
    )
    change_at = activated_at + timedelta(days=120)

    with pytest.raises(ValueError, match="no current plan version"):
        preview_plan_change(sqlite_connection, subscription_id, _TO_PLAN_ID, change_at, settings)
