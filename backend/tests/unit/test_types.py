"""Unit tests for domain dataclasses (E1-S1 AC-3, AC-5).

Each type is instantiated with valid, domain-representative data and its
field types are asserted. Monetary fields must reject non-Decimal input.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.types.billing import BillingRecord
from app.types.csr_override import CSROverride
from app.types.dealer import DealerMaster
from app.types.enums import (
    OverriddenAction,
    PlanType,
    PortOutStatus,
    SubscriberState,
)
from app.types.plan import PlanVersion
from app.types.port_out import PortOutEvent
from app.types.state_transition import StateTransition
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

NOW = datetime(2026, 1, 15, 9, 30, tzinfo=UTC)


def test_subscriber_holds_typed_fields() -> None:
    subscriber = Subscriber(
        subscriber_id="7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f",
        mobile_number="9876543210",
        identity_proof_ref="AADHAAR-XXXX-XXXX-1234",
        created_at=NOW,
    )
    assert isinstance(subscriber.subscriber_id, str)
    assert isinstance(subscriber.mobile_number, str)
    assert isinstance(subscriber.identity_proof_ref, str)
    assert isinstance(subscriber.created_at, datetime)


def test_subscription_holds_typed_fields_with_optional_activation() -> None:
    subscription = Subscription(
        subscription_id="a3d4e5f6-0000-4111-8222-333344445555",
        subscriber_id="7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f",
        mobile_number="9876543210",
        plan_type=PlanType.POSTPAID,
        state=SubscriberState.PENDING_KYC,
        current_plan_version_id=None,
        dealer_code=None,
        created_at=NOW,
        activated_at=None,
        updated_at=NOW,
    )
    assert subscription.plan_type is PlanType.POSTPAID
    assert subscription.state is SubscriberState.PENDING_KYC
    assert subscription.current_plan_version_id is None
    assert subscription.activated_at is None


def test_plan_version_price_is_decimal() -> None:
    plan_version = PlanVersion(
        plan_version_id="b1c2d3e4-1111-4222-9333-444455556666",
        plan_id="PLAN-UNLIMITED-5G",
        plan_name="Unlimited 5G Postpaid",
        plan_type=PlanType.POSTPAID,
        version_number=1,
        price=Decimal("799.00"),
        terms={"data_gb": 100, "voice_minutes": "unlimited"},
        published=True,
        created_at=NOW,
        published_at=NOW,
    )
    assert isinstance(plan_version.price, Decimal)
    assert plan_version.price == Decimal("799.00")


def test_plan_version_rejects_non_decimal_price() -> None:
    with pytest.raises(TypeError):
        PlanVersion(
            plan_version_id="b1c2d3e4-1111-4222-9333-444455556666",
            plan_id="PLAN-UNLIMITED-5G",
            plan_name="Unlimited 5G Postpaid",
            plan_type=PlanType.POSTPAID,
            version_number=1,
            price=799.00,  # type: ignore[arg-type]
            terms={},
            published=True,
            created_at=NOW,
            published_at=None,
        )


def test_billing_record_amounts_are_decimal() -> None:
    billing_record = BillingRecord(
        billing_record_id="c1d2e3f4-2222-4333-9444-555566667777",
        subscription_id="a3d4e5f6-0000-4111-8222-333344445555",
        from_plan_version_id=None,
        to_plan_version_id="b1c2d3e4-1111-4222-9333-444455556666",
        pro_rata_amount=Decimal("249.50"),
        charges_total=Decimal("249.50"),
        billing_period_start=date(2026, 1, 1),
        billing_period_end=date(2026, 1, 31),
        created_at=NOW,
    )
    assert isinstance(billing_record.pro_rata_amount, Decimal)
    assert isinstance(billing_record.charges_total, Decimal)
    assert isinstance(billing_record.billing_period_start, date)


def test_billing_record_rejects_non_decimal_charges_total() -> None:
    with pytest.raises(TypeError):
        BillingRecord(
            billing_record_id="c1d2e3f4-2222-4333-9444-555566667777",
            subscription_id="a3d4e5f6-0000-4111-8222-333344445555",
            from_plan_version_id=None,
            to_plan_version_id="b1c2d3e4-1111-4222-9333-444455556666",
            pro_rata_amount=Decimal("249.50"),
            charges_total="249.50",  # type: ignore[arg-type]
            billing_period_start=date(2026, 1, 1),
            billing_period_end=date(2026, 1, 31),
            created_at=NOW,
        )


def test_state_transition_holds_typed_states_and_nullable_reason() -> None:
    state_transition = StateTransition(
        transition_id="d1e2f3a4-3333-4444-9555-666677778888",
        subscription_id="a3d4e5f6-0000-4111-8222-333344445555",
        from_state=SubscriberState.PENDING_KYC,
        to_state=SubscriberState.ACTIVE,
        reason_code=None,
        actor="system:activation_service",
        created_at=NOW,
    )
    assert state_transition.from_state is SubscriberState.PENDING_KYC
    assert state_transition.to_state is SubscriberState.ACTIVE
    assert state_transition.reason_code is None


def test_port_out_event_holds_typed_status_and_nullable_closed_at() -> None:
    port_out_event = PortOutEvent(
        port_out_event_id="e1f2a3b4-4444-4555-9666-777788889999",
        subscription_id="a3d4e5f6-0000-4111-8222-333344445555",
        requested_at=NOW,
        cooling_period_end_at=datetime(2026, 1, 22, 9, 30, tzinfo=UTC),
        status=PortOutStatus.PENDING,
        closed_at=None,
    )
    assert port_out_event.status is PortOutStatus.PENDING
    assert port_out_event.closed_at is None
    assert port_out_event.cooling_period_end_at > port_out_event.requested_at


def test_csr_override_holds_typed_overridden_action() -> None:
    csr_override = CSROverride(
        override_id="f1a2b3c4-5555-4666-9777-888899990000",
        subscription_id="a3d4e5f6-0000-4111-8222-333344445555",
        actor="csr:agent-42",
        reason_code="GOODWILL_EXCEPTION",
        overridden_action=OverriddenAction.ACTIVATION,
        original_rejection_reason="DEALER_INVALID",
        created_at=NOW,
    )
    assert csr_override.overridden_action is OverriddenAction.ACTIVATION
    assert isinstance(csr_override.reason_code, str)


def test_dealer_master_holds_typed_active_flag() -> None:
    dealer_master = DealerMaster(
        dealer_code="DLR-BLR-001", dealer_name="Bengaluru Central Retail", active=True
    )
    assert isinstance(dealer_master.active, bool)
    assert dealer_master.dealer_code == "DLR-BLR-001"
