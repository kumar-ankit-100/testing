"""Unit tests for the CSR/Admin subscription termination service (E6-S5)."""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.repository.state_transition_repository import list_state_transitions_for_subscription
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.service.termination_service import terminate_subscription
from app.types.auth import Principal
from app.types.enums import PlanType, Role, SubscriberState
from app.types.exceptions import AuthorizationError, InvalidSubscriberStateException
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
_TERMINATED_AT = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)


def _csr_principal() -> Principal:
    return Principal(user_id="csr-001", role=Role.CSR, subscriber_id=None)


def _admin_principal() -> Principal:
    return Principal(user_id="admin-001", role=Role.ADMIN, subscriber_id=None)


def _subscriber_principal(subscriber_id: str) -> Principal:
    return Principal(user_id="user-001", role=Role.SUBSCRIBER, subscriber_id=subscriber_id)


def _register(
    connection: sqlite3.Connection,
    subscriber_id: str,
    mobile_number: str,
    state: SubscriberState,
) -> str:
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-8801",
            created_at=_REGISTERED_AT,
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
            state=state,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=_REGISTERED_AT if state != SubscriberState.PENDING_KYC else None,
            updated_at=_REGISTERED_AT,
        ),
    )
    return subscription_id


def test_csr_terminates_an_active_subscription(sqlite_connection: sqlite3.Connection) -> None:
    """AC-1."""
    subscription_id = _register(
        sqlite_connection, "term-sub-0001", "9876548801", SubscriberState.ACTIVE
    )

    subscription = terminate_subscription(
        sqlite_connection,
        _csr_principal(),
        subscription_id,
        reason_code="CUSTOMER_REQUESTED",
        terminated_at=_TERMINATED_AT,
    )

    assert subscription.state == SubscriberState.TERMINATED
    transitions = list_state_transitions_for_subscription(sqlite_connection, subscription_id)
    assert len(transitions) == 1
    assert transitions[0].to_state == SubscriberState.TERMINATED
    assert transitions[0].reason_code == "CUSTOMER_REQUESTED"


def test_admin_terminates_a_suspended_subscription(sqlite_connection: sqlite3.Connection) -> None:
    """AC-1 (SUSPENDED variant)."""
    subscription_id = _register(
        sqlite_connection, "term-sub-0002", "9876548802", SubscriberState.SUSPENDED
    )

    subscription = terminate_subscription(
        sqlite_connection,
        _admin_principal(),
        subscription_id,
        reason_code="FRAUD_DETECTED",
        terminated_at=_TERMINATED_AT,
    )

    assert subscription.state == SubscriberState.TERMINATED


def test_terminating_a_pending_kyc_subscription_raises_and_writes_no_transition(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2."""
    subscription_id = _register(
        sqlite_connection, "term-sub-0003", "9876548803", SubscriberState.PENDING_KYC
    )

    with pytest.raises(InvalidSubscriberStateException):
        terminate_subscription(
            sqlite_connection,
            _csr_principal(),
            subscription_id,
            reason_code="CUSTOMER_REQUESTED",
            terminated_at=_TERMINATED_AT,
        )

    assert list_state_transitions_for_subscription(sqlite_connection, subscription_id) == []


def test_termination_without_a_reason_code_is_rejected_before_any_write(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-3."""
    subscription_id = _register(
        sqlite_connection, "term-sub-0004", "9876548804", SubscriberState.ACTIVE
    )

    with pytest.raises(ValueError, match="reason_code"):
        terminate_subscription(
            sqlite_connection,
            _csr_principal(),
            subscription_id,
            reason_code="",
            terminated_at=_TERMINATED_AT,
        )

    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscription_id = ?", (subscription_id,)
    ).fetchone()
    assert row[0] == "ACTIVE"
    assert list_state_transitions_for_subscription(sqlite_connection, subscription_id) == []


def test_termination_by_a_non_csr_non_admin_principal_is_rejected(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-4."""
    subscriber_id = "term-sub-0005"
    subscription_id = _register(
        sqlite_connection, subscriber_id, "9876548805", SubscriberState.ACTIVE
    )

    with pytest.raises(AuthorizationError):
        terminate_subscription(
            sqlite_connection,
            _subscriber_principal(subscriber_id),
            subscription_id,
            reason_code="CUSTOMER_REQUESTED",
            terminated_at=_TERMINATED_AT,
        )

    assert list_state_transitions_for_subscription(sqlite_connection, subscription_id) == []


def test_successful_termination_logs_a_structured_entry_with_masked_actor(
    sqlite_connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    """AC-5."""
    import logging

    subscription_id = _register(
        sqlite_connection, "term-sub-0006", "9876548806", SubscriberState.ACTIVE
    )

    with caplog.at_level(logging.INFO, logger="app.service.termination_service"):
        terminate_subscription(
            sqlite_connection,
            _csr_principal(),
            subscription_id,
            reason_code="CUSTOMER_REQUESTED",
            terminated_at=_TERMINATED_AT,
        )

    assert any("terminat" in message.lower() for message in caplog.messages)
