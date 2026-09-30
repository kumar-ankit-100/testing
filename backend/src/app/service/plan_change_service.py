"""Plan change service — upgrade/downgrade with minimum-tenure rule
(E4-S3).

Service layer — imports Types, Config, Repository, and
billing_calculation_service (E4-S2). preview_plan_change and
commit_plan_change call the exact same pro-rata formula so they can
never disagree (system-design.md 5.6).
"""

import calendar
import sqlite3
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.config.settings import Settings
from app.repository.billing_repository import create_billing_record
from app.repository.plan_repository import get_plan_version_by_id
from app.repository.subscriber_repository import get_subscription_by_id, update_subscription_plan
from app.service.billing_calculation_service import calculate_pro_rata_charge
from app.types.billing import BillingRecord
from app.types.enums import SubscriberState
from app.types.exceptions import (
    MinTenureNotMetError,
    SubscriptionNotActiveError,
    SubscriptionSuspendedError,
)
from app.types.plan import PlanVersion
from app.types.subscription import Subscription


def preview_plan_change(
    connection: sqlite3.Connection,
    subscription_id: str,
    target_plan_version_id: str,
    change_at: datetime,
    settings: Settings,
) -> Decimal:
    """Return the pro-rata charge for switching subscription_id to
    target_plan_version_id, with no persistence (AC-3).
    """
    subscription = _eligible_subscription(connection, subscription_id, change_at, settings)
    return _pro_rata_for_change(connection, subscription, target_plan_version_id, change_at)


def commit_plan_change(
    connection: sqlite3.Connection,
    subscription_id: str,
    target_plan_version_id: str,
    change_at: datetime,
    settings: Settings,
) -> BillingRecord:
    """Recompute the same pro-rata amount, persist it as a new
    BillingRecord, and update the subscription's current plan (AC-4).

    Every call appends a new, independent BillingRecord — the prior
    record is never modified (AC-5), matching billing_repository's
    append-only design.
    """
    subscription = _eligible_subscription(connection, subscription_id, change_at, settings)
    pro_rata_amount = _pro_rata_for_change(
        connection, subscription, target_plan_version_id, change_at
    )
    cycle_start, cycle_end = _billing_cycle_bounds(change_at.date())

    record = BillingRecord(
        billing_record_id=str(uuid.uuid4()),
        subscription_id=subscription_id,
        from_plan_version_id=subscription.current_plan_version_id,
        to_plan_version_id=target_plan_version_id,
        pro_rata_amount=pro_rata_amount,
        charges_total=pro_rata_amount,
        billing_period_start=cycle_start,
        billing_period_end=cycle_end,
        created_at=change_at,
    )
    create_billing_record(connection, record)
    update_subscription_plan(connection, subscription_id, target_plan_version_id, change_at)

    return record


def _pro_rata_for_change(
    connection: sqlite3.Connection,
    subscription: Subscription,
    target_plan_version_id: str,
    change_at: datetime,
) -> Decimal:
    if subscription.current_plan_version_id is None:
        raise ValueError(
            f"Subscription {subscription.subscription_id!r} has no current plan version"
        )
    current_plan = _plan_version_or_raise(connection, subscription.current_plan_version_id)
    target_plan = _plan_version_or_raise(connection, target_plan_version_id)
    cycle_start, cycle_end = _billing_cycle_bounds(change_at.date())

    return calculate_pro_rata_charge(
        current_plan.price, target_plan.price, change_at.date(), cycle_start, cycle_end
    )


def _plan_version_or_raise(
    connection: sqlite3.Connection, plan_version_id: str
) -> PlanVersion:
    plan_version = get_plan_version_by_id(connection, plan_version_id)
    if plan_version is None:
        raise ValueError(f"Plan version {plan_version_id!r} not found")
    return plan_version


def _eligible_subscription(
    connection: sqlite3.Connection,
    subscription_id: str,
    change_at: datetime,
    settings: Settings,
) -> Subscription:
    subscription = get_subscription_by_id(connection, subscription_id)
    if subscription is None:
        raise ValueError(f"No subscription found for subscription_id {subscription_id!r}")

    if subscription.state == SubscriberState.SUSPENDED:
        raise SubscriptionSuspendedError(subscription_id)
    if subscription.state != SubscriberState.ACTIVE:
        raise SubscriptionNotActiveError(subscription_id, subscription.state)

    _require_minimum_tenure(subscription, change_at, settings)
    return subscription


def _require_minimum_tenure(
    subscription: Subscription, change_at: datetime, settings: Settings
) -> None:
    if subscription.activated_at is None:
        raise ValueError(
            f"ACTIVE subscription {subscription.subscription_id!r} has no activated_at"
        )
    tenure_days = (change_at.date() - subscription.activated_at.date()).days
    if tenure_days < settings.min_tenure_days:
        raise MinTenureNotMetError(subscription.subscription_id)


def _billing_cycle_bounds(change_date: date) -> tuple[date, date]:
    """The calendar month containing change_date, as (first_day, last_day)."""
    last_day_number = calendar.monthrange(change_date.year, change_date.month)[1]
    return (
        change_date.replace(day=1),
        change_date.replace(day=last_day_number),
    )
