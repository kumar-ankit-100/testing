"""Persistence for Subscriber and Subscription records (E2-S1).

Repository layer — imports Types and Config only.
"""

import sqlite3
from datetime import UTC, datetime

from app.types.enums import PlanType, SubscriberState
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_SUBSCRIBER_COLUMNS = "subscriber_id, mobile_number, identity_proof_ref, created_at"

_SUBSCRIPTION_COLUMNS = (
    "subscription_id, subscriber_id, mobile_number, plan_type, state, "
    "current_plan_version_id, dealer_code, created_at, activated_at, updated_at"
)

_INSERT_SUBSCRIPTION_SQL = f"""
    INSERT INTO subscriptions ({_SUBSCRIPTION_COLUMNS})
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def create_subscriber(connection: sqlite3.Connection, subscriber: Subscriber) -> None:
    """Insert a new subscriber row."""
    connection.execute(
        f"INSERT INTO subscribers ({_SUBSCRIBER_COLUMNS}) VALUES (?, ?, ?, ?)",
        (
            subscriber.subscriber_id,
            subscriber.mobile_number,
            subscriber.identity_proof_ref,
            subscriber.created_at.isoformat(),
        ),
    )
    connection.commit()


def get_subscriber_by_id(connection: sqlite3.Connection, subscriber_id: str) -> Subscriber | None:
    """Return the subscriber with subscriber_id, or None if not found."""
    row = connection.execute(
        f"SELECT {_SUBSCRIBER_COLUMNS} FROM subscribers WHERE subscriber_id = ?",
        (subscriber_id,),
    ).fetchone()
    return _row_to_subscriber(row)


def get_subscriber_by_mobile(
    connection: sqlite3.Connection, mobile_number: str
) -> Subscriber | None:
    """Return the subscriber with mobile_number, or None if not found."""
    row = connection.execute(
        f"SELECT {_SUBSCRIBER_COLUMNS} FROM subscribers WHERE mobile_number = ?",
        (mobile_number,),
    ).fetchone()
    return _row_to_subscriber(row)


def create_subscription(connection: sqlite3.Connection, subscription: Subscription) -> None:
    """Insert a new subscription row.

    Raises sqlite3.IntegrityError if this would create a second ACTIVE
    subscription for the same mobile number (the partial unique index
    idx_subscriptions_active_mobile, per E2-S1 AC-2/AC-4).
    """
    connection.execute(
        _INSERT_SUBSCRIPTION_SQL,
        (
            subscription.subscription_id,
            subscription.subscriber_id,
            subscription.mobile_number,
            subscription.plan_type.value,
            subscription.state.value,
            subscription.current_plan_version_id,
            subscription.dealer_code,
            subscription.created_at.isoformat(),
            subscription.activated_at.isoformat() if subscription.activated_at else None,
            subscription.updated_at.isoformat(),
        ),
    )
    connection.commit()


def get_active_subscription_by_mobile(
    connection: sqlite3.Connection, mobile_number: str
) -> Subscription | None:
    """Return the ACTIVE subscription for mobile_number, or None.

    Used by registration_service (E2-S2) to give a clean, typed rejection
    for a duplicate-active registration attempt, ahead of the DB-level
    partial unique index that backstops the same rule under a race.
    """
    row = connection.execute(
        f"""
        SELECT {_SUBSCRIPTION_COLUMNS} FROM subscriptions
        WHERE mobile_number = ? AND state = ?
        """,
        (mobile_number, SubscriberState.ACTIVE.value),
    ).fetchone()
    return _row_to_subscription(row)


def get_subscription_by_subscriber_id(
    connection: sqlite3.Connection, subscriber_id: str
) -> Subscription | None:
    """Return the subscription belonging to subscriber_id, or None.

    Used by activation_service (E2-S3) to look up the subscription named
    by the {subscriber_id} path parameter before evaluating any rule.
    """
    row = connection.execute(
        f"SELECT {_SUBSCRIPTION_COLUMNS} FROM subscriptions WHERE subscriber_id = ?",
        (subscriber_id,),
    ).fetchone()
    return _row_to_subscription(row)


def activate_subscription(
    connection: sqlite3.Connection, subscription_id: str, activated_at: datetime
) -> None:
    """Flip a subscription to ACTIVE, stamping activated_at and updated_at.

    Raises sqlite3.IntegrityError if this would create a second ACTIVE
    subscription for the same mobile number — the partial unique index
    idx_subscriptions_active_mobile guards UPDATE, not just INSERT, which
    is the mechanism behind E2-S3 AC-6's double-activation race guard.
    The FSM-validity check (is this subscription currently PENDING_KYC)
    is the service layer's job, evaluated before calling this function.
    """
    connection.execute(
        "UPDATE subscriptions SET state = ?, activated_at = ?, updated_at = ? "
        "WHERE subscription_id = ?",
        (
            SubscriberState.ACTIVE.value,
            activated_at.isoformat(),
            activated_at.isoformat(),
            subscription_id,
        ),
    )
    connection.commit()


def _row_to_subscriber(row: tuple[object, ...] | None) -> Subscriber | None:
    if row is None:
        return None
    subscriber_id, mobile_number, identity_proof_ref, created_at = row
    return Subscriber(
        subscriber_id=str(subscriber_id),
        mobile_number=str(mobile_number),
        identity_proof_ref=str(identity_proof_ref),
        created_at=datetime.fromisoformat(str(created_at)).replace(tzinfo=UTC),
    )


def _row_to_subscription(row: tuple[object, ...] | None) -> Subscription | None:
    if row is None:
        return None
    (
        subscription_id,
        subscriber_id,
        mobile_number,
        plan_type,
        state,
        current_plan_version_id,
        dealer_code,
        created_at,
        activated_at,
        updated_at,
    ) = row
    return Subscription(
        subscription_id=str(subscription_id),
        subscriber_id=str(subscriber_id),
        mobile_number=str(mobile_number),
        plan_type=PlanType(str(plan_type)),
        state=SubscriberState(str(state)),
        current_plan_version_id=_as_optional_str(current_plan_version_id),
        dealer_code=_as_optional_str(dealer_code),
        created_at=datetime.fromisoformat(str(created_at)).replace(tzinfo=UTC),
        activated_at=_as_optional_datetime(activated_at),
        updated_at=datetime.fromisoformat(str(updated_at)).replace(tzinfo=UTC),
    )


def _as_optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _as_optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(str(value)).replace(tzinfo=UTC)

