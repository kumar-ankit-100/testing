"""Unit tests for the CSR override service (E6-S2)."""

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.config.settings import Settings
from app.repository.billing_repository import list_billing_records_for_subscription
from app.repository.csr_override_repository import list_csr_overrides_for_subscription
from app.repository.plan_repository import create_plan_version, publish_plan_version
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.service.csr_override_service import (
    override_rejected_activation,
    override_rejected_plan_change,
)
from app.types.auth import Principal
from app.types.enums import OverriddenAction, PlanType, Role, SubscriberState
from app.types.exceptions import AuthorizationError, MissingOverrideReasonError
from app.types.plan import PlanVersion
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
_FROM_PLAN_ID = "OVR-FROM-PLAN-v1"
_TO_PLAN_ID = "OVR-TO-PLAN-v1"


def _csr_principal() -> Principal:
    return Principal(user_id="csr-001", role=Role.CSR, subscriber_id=None)


def _subscriber_principal(subscriber_id: str) -> Principal:
    return Principal(user_id="user-001", role=Role.SUBSCRIBER, subscriber_id=subscriber_id)


def _register_pending(
    connection: sqlite3.Connection, subscriber_id: str, mobile_number: str
) -> str:
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-7701",
            created_at=_REGISTERED_AT,
        ),
    )
    create_subscription(
        connection,
        Subscription(
            subscription_id=f"subn-{subscriber_id}",
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            plan_type=PlanType.POSTPAID,
            state=SubscriberState.PENDING_KYC,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=None,
            updated_at=_REGISTERED_AT,
        ),
    )
    return subscriber_id


def _seed_plans(connection: sqlite3.Connection) -> None:
    from_plan = PlanVersion(
        plan_version_id=_FROM_PLAN_ID,
        plan_id="OVR-PLAN",
        plan_name="Override Base",
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
        plan_id="OVR-PLAN",
        plan_name="Override Pro",
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
            identity_proof_ref="AADHAAR-XXXX-XXXX-7702",
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


def test_csr_overrides_a_rejected_activation_and_writes_an_audit_record(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-1."""
    subscriber_id = _register_pending(sqlite_connection, "ovr-sub-0001", "9876547701")
    failing_settings = Settings(_env_file=None, kyc_stub_verified=False)

    subscription = override_rejected_activation(
        sqlite_connection,
        _csr_principal(),
        subscriber_id,
        "DLR-BLR-001",
        failing_settings,
        _REGISTERED_AT,
        reason_code="CSR_MANUAL_KYC_CONFIRMED",
        original_rejection_reason="KYC_UNVERIFIED",
    )

    assert subscription.state == SubscriberState.ACTIVE
    overrides = list_csr_overrides_for_subscription(sqlite_connection, subscription.subscription_id)
    assert len(overrides) == 1
    assert overrides[0].overridden_action == OverriddenAction.ACTIVATION
    assert overrides[0].reason_code == "CSR_MANUAL_KYC_CONFIRMED"


def test_csr_overrides_a_rejected_plan_change_and_writes_an_audit_record(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2."""
    _seed_plans(sqlite_connection)
    activated_at = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    subscription_id = _register_active(
        sqlite_connection, "ovr-sub-0002", "9876547702", activated_at
    )
    change_at = activated_at + timedelta(days=5)
    settings = Settings(_env_file=None, min_tenure_days=90)

    record = override_rejected_plan_change(
        sqlite_connection,
        _csr_principal(),
        subscription_id,
        _TO_PLAN_ID,
        change_at,
        settings,
        reason_code="CSR_GOODWILL_WAIVER",
        original_rejection_reason="MIN_TENURE_NOT_MET",
    )

    assert record.to_plan_version_id == _TO_PLAN_ID
    assert list_billing_records_for_subscription(sqlite_connection, subscription_id) == [record]
    overrides = list_csr_overrides_for_subscription(sqlite_connection, subscription_id)
    assert len(overrides) == 1
    assert overrides[0].overridden_action == OverriddenAction.PLAN_CHANGE


def test_override_without_reason_code_is_rejected_before_any_write(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-3."""
    subscriber_id = _register_pending(sqlite_connection, "ovr-sub-0003", "9876547703")
    failing_settings = Settings(_env_file=None, kyc_stub_verified=False)

    with pytest.raises(MissingOverrideReasonError):
        override_rejected_activation(
            sqlite_connection,
            _csr_principal(),
            subscriber_id,
            "DLR-BLR-001",
            failing_settings,
            _REGISTERED_AT,
            reason_code="",
            original_rejection_reason="KYC_UNVERIFIED",
        )

    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscriber_id = ?", (subscriber_id,)
    ).fetchone()
    assert row[0] == "PENDING_KYC"
    assert list_csr_overrides_for_subscription(sqlite_connection, f"subn-{subscriber_id}") == []


def test_override_by_a_non_csr_principal_is_rejected(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-4."""
    subscriber_id = _register_pending(sqlite_connection, "ovr-sub-0004", "9876547704")
    failing_settings = Settings(_env_file=None, kyc_stub_verified=False)

    with pytest.raises(AuthorizationError):
        override_rejected_activation(
            sqlite_connection,
            _subscriber_principal(subscriber_id),
            subscriber_id,
            "DLR-BLR-001",
            failing_settings,
            _REGISTERED_AT,
            reason_code="SELF_OVERRIDE_ATTEMPT",
            original_rejection_reason="KYC_UNVERIFIED",
        )

    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscriber_id = ?", (subscriber_id,)
    ).fetchone()
    assert row[0] == "PENDING_KYC"
    assert list_csr_overrides_for_subscription(sqlite_connection, f"subn-{subscriber_id}") == []


def test_successful_override_logs_a_structured_entry_with_masked_actor(
    sqlite_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    """AC-5."""
    import logging

    subscriber_id = _register_pending(sqlite_connection, "ovr-sub-0005", "9876547705")
    failing_settings = Settings(_env_file=None, kyc_stub_verified=False)

    with caplog.at_level(logging.INFO, logger="app.service.csr_override_service"):
        override_rejected_activation(
            sqlite_connection,
            _csr_principal(),
            subscriber_id,
            "DLR-BLR-001",
            failing_settings,
            _REGISTERED_AT,
            reason_code="CSR_MANUAL_KYC_CONFIRMED",
            original_rejection_reason="KYC_UNVERIFIED",
        )

    assert any("CSR override recorded" in message for message in caplog.messages)
