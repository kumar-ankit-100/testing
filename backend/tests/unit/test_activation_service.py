"""Unit tests for the rule-based activation engine (E2-S3)."""

import sqlite3
from datetime import UTC, datetime

import pytest

from app.config.settings import Settings
from app.repository.state_transition_repository import list_state_transitions_for_subscription
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.service.activation_service import activate_subscriber
from app.types.enums import PlanType, ReasonCode, SubscriberState
from app.types.exceptions import (
    ActivationRejectedError,
    DuplicateActiveSubscriptionError,
    InvalidSubscriberStateException,
)
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
_ACTIVATED_AT = datetime(2026, 6, 2, 10, 0, tzinfo=UTC)
_VALID_DEALER_CODE = "DLR-BLR-001"


def _register_pending(
    connection: sqlite3.Connection, subscriber_id: str, mobile_number: str
) -> str:
    """Create a Subscriber + PENDING_KYC Subscription pair; return subscriber_id."""
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-6601",
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


@pytest.fixture
def all_flags_pass_settings() -> Settings:
    return Settings(_env_file=None, kyc_stub_verified=True, mnp_stub_success=True)


def test_activation_with_all_checks_passing_transitions_to_active_and_appends_transition(
    sqlite_connection: sqlite3.Connection, all_flags_pass_settings: Settings
) -> None:
    """AC-1."""
    subscriber_id = _register_pending(sqlite_connection, "act-sub-0001", "9876546601")

    subscription = activate_subscriber(
        sqlite_connection,
        subscriber_id,
        _VALID_DEALER_CODE,
        all_flags_pass_settings,
        _ACTIVATED_AT,
    )

    assert subscription.state == SubscriberState.ACTIVE
    assert subscription.activated_at == _ACTIVATED_AT

    transitions = list_state_transitions_for_subscription(
        sqlite_connection, subscription.subscription_id
    )
    assert len(transitions) == 1
    assert transitions[0].from_state == SubscriberState.PENDING_KYC
    assert transitions[0].to_state == SubscriberState.ACTIVE


def test_activation_with_unverified_kyc_is_rejected_and_subscription_remains_pending(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-2."""
    subscriber_id = _register_pending(sqlite_connection, "act-sub-0002", "9876546602")
    settings = Settings(_env_file=None, kyc_stub_verified=False, mnp_stub_success=True)

    with pytest.raises(ActivationRejectedError) as exc_info:
        activate_subscriber(
            sqlite_connection, subscriber_id, _VALID_DEALER_CODE, settings, _ACTIVATED_AT
        )

    assert exc_info.value.reason_code == ReasonCode.KYC_UNVERIFIED
    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscriber_id = ?", (subscriber_id,)
    ).fetchone()
    assert row[0] == "PENDING_KYC"
    assert list_state_transitions_for_subscription(sqlite_connection, f"subn-{subscriber_id}") == []


def test_activation_with_dealer_fail_sentinel_is_rejected_and_subscription_remains_pending(
    sqlite_connection: sqlite3.Connection, all_flags_pass_settings: Settings
) -> None:
    """AC-3."""
    subscriber_id = _register_pending(sqlite_connection, "act-sub-0003", "9876546603")

    with pytest.raises(ActivationRejectedError) as exc_info:
        activate_subscriber(
            sqlite_connection, subscriber_id, "DEALER-FAIL", all_flags_pass_settings, _ACTIVATED_AT
        )

    assert exc_info.value.reason_code == ReasonCode.DEALER_INVALID
    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscriber_id = ?", (subscriber_id,)
    ).fetchone()
    assert row[0] == "PENDING_KYC"


def test_activation_with_an_unknown_dealer_code_is_also_rejected(
    sqlite_connection: sqlite3.Connection, all_flags_pass_settings: Settings
) -> None:
    """Dealer validation is a real DealerMaster lookup, not just a
    hardcoded sentinel-string comparison — an unseeded code is rejected
    the same way as the DEALER-FAIL sentinel."""
    subscriber_id = _register_pending(sqlite_connection, "act-sub-0004", "9876546604")

    with pytest.raises(ActivationRejectedError) as exc_info:
        activate_subscriber(
            sqlite_connection,
            subscriber_id,
            "DLR-DOES-NOT-EXIST",
            all_flags_pass_settings,
            _ACTIVATED_AT,
        )

    assert exc_info.value.reason_code == ReasonCode.DEALER_INVALID


def test_activation_with_mnp_fail_flag_is_rejected_and_subscription_remains_pending(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """AC-4."""
    subscriber_id = _register_pending(sqlite_connection, "act-sub-0005", "9876546605")
    settings = Settings(_env_file=None, kyc_stub_verified=True, mnp_stub_success=False)

    with pytest.raises(ActivationRejectedError) as exc_info:
        activate_subscriber(
            sqlite_connection, subscriber_id, _VALID_DEALER_CODE, settings, _ACTIVATED_AT
        )

    assert exc_info.value.reason_code == ReasonCode.MNP_FAILED
    row = sqlite_connection.execute(
        "SELECT state FROM subscriptions WHERE subscriber_id = ?", (subscriber_id,)
    ).fetchone()
    assert row[0] == "PENDING_KYC"


def test_activating_an_already_active_subscription_raises_invalid_state_exception(
    sqlite_connection: sqlite3.Connection, all_flags_pass_settings: Settings
) -> None:
    """AC-5."""
    subscriber_id = _register_pending(sqlite_connection, "act-sub-0006", "9876546606")
    activate_subscriber(
        sqlite_connection, subscriber_id, _VALID_DEALER_CODE, all_flags_pass_settings, _ACTIVATED_AT
    )

    with pytest.raises(InvalidSubscriberStateException):
        activate_subscriber(
            sqlite_connection,
            subscriber_id,
            _VALID_DEALER_CODE,
            all_flags_pass_settings,
            _ACTIVATED_AT,
        )


def test_two_pending_registrations_for_the_same_mobile_only_one_reaches_active(
    sqlite_connection: sqlite3.Connection, all_flags_pass_settings: Settings
) -> None:
    """AC-6 (NFR-07 double-activation race, exercised sequentially): two
    different subscriber/subscription pairs registered for the same
    mobile number (E2-S2 only blocks a duplicate mobile against an
    existing ACTIVE row, not another PENDING_KYC one) both attempt
    activation; only the first succeeds.
    """
    shared_mobile = "9876546607"
    subscriber_a = _register_pending(sqlite_connection, "act-sub-0007a", shared_mobile)
    subscriber_b = _register_pending(sqlite_connection, "act-sub-0007b", shared_mobile)

    winner = activate_subscriber(
        sqlite_connection, subscriber_a, _VALID_DEALER_CODE, all_flags_pass_settings, _ACTIVATED_AT
    )
    assert winner.state == SubscriberState.ACTIVE

    with pytest.raises(DuplicateActiveSubscriptionError):
        activate_subscriber(
            sqlite_connection,
            subscriber_b,
            _VALID_DEALER_CODE,
            all_flags_pass_settings,
            _ACTIVATED_AT,
        )

    active_count = sqlite_connection.execute(
        "SELECT COUNT(*) FROM subscriptions WHERE mobile_number = ? AND state = 'ACTIVE'",
        (shared_mobile,),
    ).fetchone()[0]
    assert active_count == 1


def test_activate_subscriber_raises_for_an_unknown_subscriber_id(
    sqlite_connection: sqlite3.Connection, all_flags_pass_settings: Settings
) -> None:
    with pytest.raises(ValueError, match="No subscription found"):
        activate_subscriber(
            sqlite_connection,
            "does-not-exist",
            _VALID_DEALER_CODE,
            all_flags_pass_settings,
            _ACTIVATED_AT,
        )


def test_activate_subscriber_with_skip_rule_checks_succeeds_despite_a_failing_flag(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """E6-S2: CSR override support — skip_rule_checks bypasses KYC/dealer/
    MNP evaluation entirely, so a CSR can force activation through
    despite whichever rule originally rejected it.
    """
    subscriber_id = _register_pending(sqlite_connection, "act-sub-0008", "9876546608")
    failing_settings = Settings(_env_file=None, kyc_stub_verified=False, mnp_stub_success=False)

    subscription = activate_subscriber(
        sqlite_connection,
        subscriber_id,
        "DEALER-FAIL",
        failing_settings,
        _ACTIVATED_AT,
        skip_rule_checks=True,
    )

    assert subscription.state == SubscriberState.ACTIVE


def test_activate_subscriber_with_skip_rule_checks_still_enforces_the_fsm(
    sqlite_connection: sqlite3.Connection, all_flags_pass_settings: Settings
) -> None:
    """Bypassing rule checks doesn't bypass FSM validity — an
    already-ACTIVE subscription still can't be "activated" again.
    """
    subscriber_id = _register_pending(sqlite_connection, "act-sub-0009", "9876546609")
    activate_subscriber(
        sqlite_connection, subscriber_id, _VALID_DEALER_CODE, all_flags_pass_settings, _ACTIVATED_AT
    )

    with pytest.raises(InvalidSubscriberStateException):
        activate_subscriber(
            sqlite_connection,
            subscriber_id,
            _VALID_DEALER_CODE,
            all_flags_pass_settings,
            _ACTIVATED_AT,
            skip_rule_checks=True,
        )
