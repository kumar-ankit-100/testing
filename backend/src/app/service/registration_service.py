"""Subscriber self-registration service (E2-S2).

Service layer — imports Types, Config, Repository, and the cross-cutting
logging_service.
"""

import re
import sqlite3
import uuid
from datetime import datetime

from app.repository.subscriber_repository import (
    create_subscriber,
    create_subscription,
    get_active_subscription_by_mobile,
)
from app.service.logging_service import get_logger
from app.types.enums import PlanType, SubscriberState
from app.types.exceptions import DuplicateActiveSubscriptionError, InvalidMobileNumberError
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_MOBILE_NUMBER_PATTERN = re.compile(r"^[0-9]{10}$")
_logger = get_logger(__name__)


def register_subscriber(
    connection: sqlite3.Connection,
    mobile_number: str,
    identity_proof_ref: str,
    plan_type: PlanType,
    registered_at: datetime,
) -> Subscription:
    """Create a new Subscriber + Subscription pair in PENDING_KYC state.

    Raises InvalidMobileNumberError before any database write if
    mobile_number is malformed (AC-3), or DuplicateActiveSubscriptionError
    if mobile_number already has an ACTIVE subscription (AC-2).
    """
    _validate_mobile_number(mobile_number)
    _reject_if_duplicate_active(connection, mobile_number)

    subscriber = Subscriber(
        subscriber_id=str(uuid.uuid4()),
        mobile_number=mobile_number,
        identity_proof_ref=identity_proof_ref,
        created_at=registered_at,
    )
    subscription = Subscription(
        subscription_id=str(uuid.uuid4()),
        subscriber_id=subscriber.subscriber_id,
        mobile_number=mobile_number,
        plan_type=plan_type,
        state=SubscriberState.PENDING_KYC,
        current_plan_version_id=None,
        dealer_code=None,
        created_at=registered_at,
        activated_at=None,
        updated_at=registered_at,
    )

    create_subscriber(connection, subscriber)
    create_subscription(connection, subscription)

    _logger.info(
        "Subscriber registered",
        extra={
            "context": {
                "subscriber_id": subscriber.subscriber_id,
                "mobile_number": mobile_number,
                "identity_proof_ref": identity_proof_ref,
            }
        },
    )

    return subscription


def _validate_mobile_number(mobile_number: str) -> None:
    if not _MOBILE_NUMBER_PATTERN.fullmatch(mobile_number):
        raise InvalidMobileNumberError(mobile_number)


def _reject_if_duplicate_active(connection: sqlite3.Connection, mobile_number: str) -> None:
    if get_active_subscription_by_mobile(connection, mobile_number) is not None:
        raise DuplicateActiveSubscriptionError(mobile_number)
