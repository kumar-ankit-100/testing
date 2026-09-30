"""Rule-based activation engine (E2-S3): KYC, dealer, and MNP stub checks
gate the PENDING_KYC -> ACTIVE transition.

Service layer — imports Types, Config, Repository.
"""

import dataclasses
import sqlite3
import uuid
from datetime import datetime

from app.config.settings import Settings
from app.repository.dealer_repository import get_dealer_by_code
from app.repository.state_transition_repository import append_state_transition
from app.repository.subscriber_repository import (
    activate_subscription,
    get_subscription_by_subscriber_id,
)
from app.types.enums import ReasonCode, SubscriberState
from app.types.exceptions import ActivationRejectedError, DuplicateActiveSubscriptionError
from app.types.fsm import transition
from app.types.state_transition import StateTransition
from app.types.subscription import Subscription


def activate_subscriber(
    connection: sqlite3.Connection,
    subscriber_id: str,
    dealer_code: str,
    settings: Settings,
    activated_at: datetime,
) -> Subscription:
    """Evaluate KYC/dealer/MNP rules and transition subscriber_id's
    subscription from PENDING_KYC to ACTIVE.

    Raises InvalidSubscriberStateException (AC-5) if the subscription is
    not currently PENDING_KYC — checked before any rule is evaluated.
    Raises ActivationRejectedError (AC-2/3/4) with the specific failing
    reason_code if a rule fails; the subscription remains PENDING_KYC and
    no StateTransition row is written. Raises
    DuplicateActiveSubscriptionError (AC-6) if a sibling registration for
    the same mobile number already won the race to ACTIVE.
    """
    subscription = _get_subscription_or_raise(connection, subscriber_id)

    transition(subscription.state, SubscriberState.ACTIVE)
    _evaluate_activation_rules(connection, dealer_code, settings)

    try:
        activate_subscription(connection, subscription.subscription_id, activated_at)
    except sqlite3.IntegrityError as exc:
        raise DuplicateActiveSubscriptionError(subscription.mobile_number) from exc

    append_state_transition(
        connection,
        StateTransition(
            transition_id=str(uuid.uuid4()),
            subscription_id=subscription.subscription_id,
            from_state=SubscriberState.PENDING_KYC,
            to_state=SubscriberState.ACTIVE,
            reason_code=None,
            actor=f"subscriber:{subscriber_id}",
            created_at=activated_at,
        ),
    )

    return dataclasses.replace(
        subscription,
        state=SubscriberState.ACTIVE,
        activated_at=activated_at,
        updated_at=activated_at,
    )


def _get_subscription_or_raise(
    connection: sqlite3.Connection, subscriber_id: str
) -> Subscription:
    subscription = get_subscription_by_subscriber_id(connection, subscriber_id)
    if subscription is None:
        raise ValueError(f"No subscription found for subscriber {subscriber_id!r}")
    return subscription


def _evaluate_activation_rules(
    connection: sqlite3.Connection, dealer_code: str, settings: Settings
) -> None:
    if not settings.kyc_stub_verified:
        raise ActivationRejectedError(ReasonCode.KYC_UNVERIFIED)

    dealer = get_dealer_by_code(connection, dealer_code)
    if dealer is None or not dealer.active:
        raise ActivationRejectedError(ReasonCode.DEALER_INVALID)

    if not settings.mnp_stub_success:
        raise ActivationRejectedError(ReasonCode.MNP_FAILED)
