"""CSR/Admin subscription termination service (E6-S5): a CSR or admin
terminates an ACTIVE or SUSPENDED subscription via the shared FSM, with
a mandatory reason_code.

Service layer — imports Types, Config, Repository.
"""

import dataclasses
import sqlite3
import uuid
from datetime import datetime

from app.repository.state_transition_repository import append_state_transition
from app.repository.subscriber_repository import get_subscription_by_id, update_subscription_state
from app.service.logging_service import get_logger
from app.types.auth import Principal
from app.types.enums import Role, SubscriberState
from app.types.exceptions import AuthorizationError
from app.types.fsm import transition
from app.types.state_transition import StateTransition
from app.types.subscription import Subscription

_logger = get_logger(__name__)


def terminate_subscription(
    connection: sqlite3.Connection,
    principal: Principal,
    subscription_id: str,
    reason_code: str,
    terminated_at: datetime,
) -> Subscription:
    """Transition subscription_id from ACTIVE or SUSPENDED to TERMINATED
    (AC-1).

    Raises InvalidSubscriberStateException if the subscription is in any
    other state (AC-2), before any write. Raises ValueError if
    reason_code is falsy (AC-3), before any write. Raises
    AuthorizationError if principal is neither CSR nor ADMIN (AC-4),
    before any write. Every call that reaches persistence — success or
    failure — writes a StateTransition with a non-null actor/reason_code/
    timestamp and logs a structured entry with a masked actor (AC-5).
    """
    _require_csr_or_admin(principal)
    if not reason_code:
        raise ValueError("A reason_code is required to terminate a subscription")

    subscription = get_subscription_by_id(connection, subscription_id)
    if subscription is None:
        raise ValueError(f"No subscription found for subscription_id {subscription_id!r}")

    transition(subscription.state, SubscriberState.TERMINATED)
    from_state = subscription.state

    update_subscription_state(
        connection, subscription_id, SubscriberState.TERMINATED, terminated_at
    )

    actor = f"{principal.role.value}:{principal.user_id}"
    append_state_transition(
        connection,
        StateTransition(
            transition_id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            from_state=from_state,
            to_state=SubscriberState.TERMINATED,
            reason_code=reason_code,
            actor=actor,
            created_at=terminated_at,
        ),
    )
    _logger.info(
        "Subscription terminated",
        extra={
            "context": {
                "subscription_id": subscription_id,
                "actor": actor,
                "reason_code": reason_code,
            }
        },
    )

    return dataclasses.replace(
        subscription, state=SubscriberState.TERMINATED, updated_at=terminated_at
    )


def _require_csr_or_admin(principal: Principal) -> None:
    if principal.role not in (Role.CSR, Role.ADMIN):
        raise AuthorizationError(
            f"Role {principal.role.value} may not terminate a subscription"
        )
