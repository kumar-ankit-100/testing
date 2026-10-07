"""Unit tests for the subscriber-facing subscription detail view —
closes the "subscriber dashboard has no way to see its own plan" gap.
"""

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.service.plan_catalog_service import create_draft_plan_version, publish_plan_version
from app.service.registration_service import register_subscriber
from app.service.subscription_detail_service import get_subscription_detail
from app.types.auth import Principal
from app.types.enums import PlanType, Role

_ADMIN = Principal(user_id="admin-1", role=Role.ADMIN, subscriber_id=None)
_NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def _register(connection: sqlite3.Connection, mobile_number: str) -> str:
    subscription = register_subscriber(
        connection,
        mobile_number=mobile_number,
        identity_proof_ref="AADHAAR-XXXX-0001",
        plan_type=PlanType.POSTPAID,
        registered_at=_NOW,
    )
    return subscription.subscriber_id


def test_get_subscription_detail_returns_subscription_with_no_plan_before_activation(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber_id = _register(sqlite_connection, "9876511001")

    detail = get_subscription_detail(sqlite_connection, subscriber_id)

    assert detail.subscription.subscriber_id == subscriber_id
    assert detail.subscription.state.value == "PENDING_KYC"
    assert detail.current_plan is None


def test_get_subscription_detail_includes_current_plan_once_set(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber_id = _register(sqlite_connection, "9876511002")
    draft = create_draft_plan_version(
        sqlite_connection,
        _ADMIN,
        plan_id="PLAN-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        price=Decimal("799.00"),
        terms={"data_gb": 100},
        created_at=_NOW,
    )
    publish_plan_version(sqlite_connection, _ADMIN, "PLAN-5G", draft.plan_version_id, _NOW)
    sqlite_connection.execute(
        "UPDATE subscriptions SET current_plan_version_id = ? WHERE subscriber_id = ?",
        (draft.plan_version_id, subscriber_id),
    )
    sqlite_connection.commit()

    detail = get_subscription_detail(sqlite_connection, subscriber_id)

    assert detail.current_plan is not None
    assert detail.current_plan.plan_id == "PLAN-5G"
    assert detail.current_plan.price == Decimal("799.00")


def test_get_subscription_detail_raises_for_an_unknown_subscriber(
    sqlite_connection: sqlite3.Connection,
) -> None:
    with pytest.raises(ValueError, match="not found"):
        get_subscription_detail(sqlite_connection, "does-not-exist")
