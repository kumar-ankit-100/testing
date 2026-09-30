"""Unit tests for reporting_repository (E7-S1).

Data-model note: a rejected activation attempt (KYC_UNVERIFIED,
DEALER_INVALID, or MNP_FAILED) writes no row anywhere — the subscription
simply remains PENDING_KYC (system-design.md 3.1, E2-S3 AC-2/3/4). There is
therefore no persisted signal that distinguishes "never attempted
activation" from "attempted and rejected at KYC" from "attempted and
rejected at dealer" from "attempted and rejected at MNP" — all three
intermediate funnel stages collapse to the same count as "activated"
(every subscription that ever reached ACTIVE). AC-2 only requires the
stage counts to be internally consistent (each <= the prior stage), which
holds trivially under equality; these tests assert that documented
behavior explicitly rather than asserting a false distinction the data
cannot support.
"""

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

from app.repository.billing_repository import create_billing_record
from app.repository.reporting_repository import (
    activation_funnel_counts,
    arpu_trend,
    monthly_churn_rate,
    plan_mix_distribution,
)
from app.repository.state_transition_repository import append_state_transition
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.billing import BillingRecord
from app.types.enums import PlanType, SubscriberState
from app.types.state_transition import StateTransition
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_created_counter = 0


def _register(
    connection: sqlite3.Connection,
    plan_type: PlanType,
    state: SubscriberState,
    created_at: datetime,
) -> str:
    """Create a subscriber + subscription pair and return the subscription_id."""
    global _created_counter
    _created_counter += 1
    n = _created_counter
    subscriber = Subscriber(
        subscriber_id=f"11111111-0000-4000-8000-{n:012d}",
        mobile_number=f"90000{n:05d}",
        identity_proof_ref=f"AADHAAR-XXXX-XXXX-{n:04d}",
        created_at=created_at,
    )
    create_subscriber(connection, subscriber)
    subscription = Subscription(
        subscription_id=f"22222222-0000-4000-8000-{n:012d}",
        subscriber_id=subscriber.subscriber_id,
        mobile_number=subscriber.mobile_number,
        plan_type=plan_type,
        state=state,
        current_plan_version_id=None,
        dealer_code=None,
        created_at=created_at,
        activated_at=created_at if state != SubscriberState.PENDING_KYC else None,
        updated_at=created_at,
    )
    create_subscription(connection, subscription)
    return subscription.subscription_id


def _append_transition(
    connection: sqlite3.Connection,
    subscription_id: str,
    from_state: SubscriberState,
    to_state: SubscriberState,
    created_at: datetime,
) -> None:
    global _created_counter
    _created_counter += 1
    append_state_transition(
        connection,
        StateTransition(
            transition_id=f"33333333-0000-4000-8000-{_created_counter:012d}",
            subscription_id=subscription_id,
            from_state=from_state,
            to_state=to_state,
            reason_code=None,
            actor="system:test",
            created_at=created_at,
        ),
    )


def test_activation_funnel_counts_on_an_empty_database_is_all_zero(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """E7-S2 AC-1's repository-level precondition: zero data is valid, not an error."""
    counts = activation_funnel_counts(sqlite_connection)

    assert counts == {
        "registered": 0,
        "kyc_passed": 0,
        "dealer_passed": 0,
        "mnp_passed": 0,
        "activated": 0,
    }


def test_activation_funnel_counts_are_monotonically_non_increasing(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2: each stage count <= the prior stage count."""
    now = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    active_1 = _register(sqlite_connection, PlanType.POSTPAID, SubscriberState.PENDING_KYC, now)
    active_2 = _register(sqlite_connection, PlanType.PREPAID, SubscriberState.PENDING_KYC, now)
    _register(sqlite_connection, PlanType.PREPAID, SubscriberState.PENDING_KYC, now)
    _append_transition(
        sqlite_connection, active_1, SubscriberState.PENDING_KYC, SubscriberState.ACTIVE, now
    )
    _append_transition(
        sqlite_connection, active_2, SubscriberState.PENDING_KYC, SubscriberState.ACTIVE, now
    )

    counts = activation_funnel_counts(sqlite_connection)

    assert counts["registered"] == 3
    assert counts["activated"] == 2
    stages = [
        counts["registered"],
        counts["kyc_passed"],
        counts["dealer_passed"],
        counts["mnp_passed"],
        counts["activated"],
    ]
    assert all(stages[i] >= stages[i + 1] for i in range(len(stages) - 1))


def test_activation_funnel_middle_stages_equal_activated_given_no_partial_signal(
    sqlite_connection: sqlite3.Connection,
) -> None:
    now = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)
    active = _register(sqlite_connection, PlanType.POSTPAID, SubscriberState.PENDING_KYC, now)
    _append_transition(
        sqlite_connection, active, SubscriberState.PENDING_KYC, SubscriberState.ACTIVE, now
    )

    counts = activation_funnel_counts(sqlite_connection)

    assert counts["kyc_passed"] == counts["activated"]
    assert counts["dealer_passed"] == counts["activated"]
    assert counts["mnp_passed"] == counts["activated"]


def test_plan_mix_distribution_counts_only_active_subscriptions_by_plan_type(
    sqlite_connection: sqlite3.Connection,
) -> None:
    now = datetime(2026, 1, 12, 9, 0, tzinfo=UTC)
    _register(sqlite_connection, PlanType.POSTPAID, SubscriberState.ACTIVE, now)
    _register(sqlite_connection, PlanType.POSTPAID, SubscriberState.ACTIVE, now)
    _register(sqlite_connection, PlanType.PREPAID, SubscriberState.ACTIVE, now)
    _register(sqlite_connection, PlanType.PREPAID, SubscriberState.PENDING_KYC, now)

    mix = plan_mix_distribution(sqlite_connection)

    assert mix == {"POSTPAID": 2, "PREPAID": 1}


def test_plan_mix_distribution_on_an_empty_database_is_empty(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert plan_mix_distribution(sqlite_connection) == {}


def test_monthly_churn_rate_divides_churned_count_by_active_base_at_month_start(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-3: PORTED_OUT/TERMINATED transitions in the month, over the active
    base at that month's start."""
    jan_5 = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    jan_10 = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
    feb_10 = datetime(2026, 2, 10, 9, 0, tzinfo=UTC)

    sub_a = _register(sqlite_connection, PlanType.POSTPAID, SubscriberState.PENDING_KYC, jan_5)
    sub_b = _register(sqlite_connection, PlanType.PREPAID, SubscriberState.PENDING_KYC, jan_10)
    _append_transition(
        sqlite_connection, sub_a, SubscriberState.PENDING_KYC, SubscriberState.ACTIVE, jan_5
    )
    _append_transition(
        sqlite_connection, sub_b, SubscriberState.PENDING_KYC, SubscriberState.ACTIVE, jan_10
    )
    # Both A and B are ACTIVE as of Feb 1 (month start) -> active base = 2.
    _append_transition(
        sqlite_connection, sub_a, SubscriberState.ACTIVE, SubscriberState.TERMINATED, feb_10
    )
    # 1 churn event in February.

    rates = monthly_churn_rate(sqlite_connection)

    assert rates["2026-02"] == Decimal("0.50")


def test_monthly_churn_rate_values_are_decimal(sqlite_connection: sqlite3.Connection) -> None:
    jan_5 = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    feb_10 = datetime(2026, 2, 10, 9, 0, tzinfo=UTC)
    sub_a = _register(sqlite_connection, PlanType.POSTPAID, SubscriberState.PENDING_KYC, jan_5)
    _append_transition(
        sqlite_connection, sub_a, SubscriberState.PENDING_KYC, SubscriberState.ACTIVE, jan_5
    )
    _append_transition(
        sqlite_connection, sub_a, SubscriberState.ACTIVE, SubscriberState.PORTED_OUT, feb_10
    )

    rates = monthly_churn_rate(sqlite_connection)

    assert isinstance(rates["2026-02"], Decimal)


def test_monthly_churn_rate_is_zero_when_active_base_at_month_start_is_zero(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """Both the activation and the churn happen inside the same month, so
    there is no one who was already ACTIVE as of that month's start.
    """
    jan_15 = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
    jan_20 = datetime(2026, 1, 20, 9, 0, tzinfo=UTC)
    sub_a = _register(sqlite_connection, PlanType.POSTPAID, SubscriberState.PENDING_KYC, jan_15)
    _append_transition(
        sqlite_connection, sub_a, SubscriberState.PENDING_KYC, SubscriberState.ACTIVE, jan_15
    )
    _append_transition(
        sqlite_connection, sub_a, SubscriberState.ACTIVE, SubscriberState.TERMINATED, jan_20
    )

    rates = monthly_churn_rate(sqlite_connection)

    assert rates["2026-01"] == Decimal("0.00")


def test_monthly_churn_rate_on_an_empty_database_is_empty(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert monthly_churn_rate(sqlite_connection) == {}


def test_arpu_trend_averages_charges_total_per_month_as_decimal(
    sqlite_connection: sqlite3.Connection,
) -> None:
    now = datetime(2026, 3, 1, 8, 0, tzinfo=UTC)
    sub_a = _register(sqlite_connection, PlanType.POSTPAID, SubscriberState.ACTIVE, now)
    sub_b = _register(sqlite_connection, PlanType.PREPAID, SubscriberState.ACTIVE, now)
    create_billing_record(
        sqlite_connection,
        BillingRecord(
            billing_record_id="44444444-0000-4000-8000-000000000001",
            subscription_id=sub_a,
            from_plan_version_id=None,
            to_plan_version_id="PLAN-5G-v1",
            pro_rata_amount=Decimal("100.00"),
            charges_total=Decimal("100.00"),
            billing_period_start=now.date(),
            billing_period_end=now.date(),
            created_at=now,
        ),
    )
    create_billing_record(
        sqlite_connection,
        BillingRecord(
            billing_record_id="44444444-0000-4000-8000-000000000002",
            subscription_id=sub_b,
            from_plan_version_id=None,
            to_plan_version_id="PLAN-4G-v1",
            pro_rata_amount=Decimal("200.00"),
            charges_total=Decimal("200.00"),
            billing_period_start=now.date(),
            billing_period_end=now.date(),
            created_at=now,
        ),
    )

    trend = arpu_trend(sqlite_connection)

    assert trend["2026-03"] == Decimal("150.00")
    assert isinstance(trend["2026-03"], Decimal)


def test_arpu_trend_on_an_empty_database_is_empty(sqlite_connection: sqlite3.Connection) -> None:
    assert arpu_trend(sqlite_connection) == {}
