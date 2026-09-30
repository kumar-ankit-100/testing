"""Unit tests for billing_repository (E4-S1)."""

import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.repository.billing_repository import (
    create_billing_record,
    list_billing_records_for_subscription,
)
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.billing import BillingRecord
from app.types.enums import PlanType, SubscriberState
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_NOW = datetime(2026, 3, 1, 8, 0, tzinfo=UTC)


@pytest.fixture
def active_subscription_id(sqlite_connection: sqlite3.Connection) -> str:
    subscriber = Subscriber(
        subscriber_id="d1e2f3a4-0001-4b11-9c22-333344445555",
        mobile_number="9876540101",
        identity_proof_ref="AADHAAR-XXXX-XXXX-1111",
        created_at=_NOW,
    )
    create_subscriber(sqlite_connection, subscriber)
    subscription = Subscription(
        subscription_id="e2f3a4b5-0001-4c22-9d33-444455556666",
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


def _build_billing_record(
    billing_record_id: str, subscription_id: str, pro_rata: str, total: str
) -> BillingRecord:
    return BillingRecord(
        billing_record_id=billing_record_id,
        subscription_id=subscription_id,
        from_plan_version_id="PLAN-5G-v1",
        to_plan_version_id="PLAN-5G-v2",
        pro_rata_amount=Decimal(pro_rata),
        charges_total=Decimal(total),
        billing_period_start=date(2026, 3, 1),
        billing_period_end=date(2026, 3, 31),
        created_at=_NOW,
    )


def test_create_and_list_billing_record_round_trips(
    sqlite_connection: sqlite3.Connection, active_subscription_id: str
) -> None:
    record = _build_billing_record(
        "f3a4b5c6-0001-4d33-9e44-555566667777", active_subscription_id, "150.25", "150.25"
    )

    create_billing_record(sqlite_connection, record)
    records = list_billing_records_for_subscription(sqlite_connection, active_subscription_id)

    assert records == [record]


def test_monetary_columns_round_trip_as_exact_decimal(
    sqlite_connection: sqlite3.Connection, active_subscription_id: str
) -> None:
    record = _build_billing_record(
        "f3a4b5c6-0002-4d33-9e44-555566667777", active_subscription_id, "333.33", "333.33"
    )
    create_billing_record(sqlite_connection, record)

    records = list_billing_records_for_subscription(sqlite_connection, active_subscription_id)

    assert isinstance(records[0].pro_rata_amount, Decimal)
    assert isinstance(records[0].charges_total, Decimal)
    assert records[0].pro_rata_amount == Decimal("333.33")
    assert records[0].charges_total == Decimal("333.33")


def test_two_billing_records_for_the_same_subscription_both_remain_retrievable(
    sqlite_connection: sqlite3.Connection, active_subscription_id: str
) -> None:
    first = _build_billing_record(
        "f3a4b5c6-0003-4d33-9e44-555566667777", active_subscription_id, "100.00", "100.00"
    )
    second = _build_billing_record(
        "f3a4b5c6-0004-4d33-9e44-555566667777", active_subscription_id, "200.00", "200.00"
    )

    create_billing_record(sqlite_connection, first)
    create_billing_record(sqlite_connection, second)

    records = list_billing_records_for_subscription(sqlite_connection, active_subscription_id)
    assert {r.billing_record_id for r in records} == {
        first.billing_record_id,
        second.billing_record_id,
    }


def test_list_billing_records_returns_empty_list_for_a_subscription_with_none(
    sqlite_connection: sqlite3.Connection, active_subscription_id: str
) -> None:
    assert list_billing_records_for_subscription(sqlite_connection, active_subscription_id) == []


def test_direct_update_of_a_billing_record_is_rejected(
    sqlite_connection: sqlite3.Connection, active_subscription_id: str
) -> None:
    """AC-3: no update is possible against billing_records, even via raw SQL."""
    record = _build_billing_record(
        "f3a4b5c6-0005-4d33-9e44-555566667777", active_subscription_id, "50.00", "50.00"
    )
    create_billing_record(sqlite_connection, record)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "UPDATE billing_records SET charges_total = ? WHERE billing_record_id = ?",
            ("0.01", record.billing_record_id),
        )


def test_direct_delete_of_a_billing_record_is_rejected(
    sqlite_connection: sqlite3.Connection, active_subscription_id: str
) -> None:
    """AC-3: no delete is possible against billing_records, even via raw SQL."""
    record = _build_billing_record(
        "f3a4b5c6-0006-4d33-9e44-555566667777", active_subscription_id, "75.00", "75.00"
    )
    create_billing_record(sqlite_connection, record)

    with pytest.raises(sqlite3.IntegrityError):
        sqlite_connection.execute(
            "DELETE FROM billing_records WHERE billing_record_id = ?",
            (record.billing_record_id,),
        )


def test_billing_record_with_null_from_plan_version_id_round_trips(
    sqlite_connection: sqlite3.Connection, active_subscription_id: str
) -> None:
    """First-ever billing record for a subscription has no from_plan_version_id."""
    record = BillingRecord(
        billing_record_id="f3a4b5c6-0007-4d33-9e44-555566667777",
        subscription_id=active_subscription_id,
        from_plan_version_id=None,
        to_plan_version_id="PLAN-5G-v1",
        pro_rata_amount=Decimal("0.00"),
        charges_total=Decimal("0.00"),
        billing_period_start=date(2026, 3, 1),
        billing_period_end=date(2026, 3, 31),
        created_at=_NOW,
    )

    create_billing_record(sqlite_connection, record)
    records = list_billing_records_for_subscription(sqlite_connection, active_subscription_id)

    assert records[0].from_plan_version_id is None
