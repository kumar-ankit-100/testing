"""Suspend/resume service (E5-S2): uses the shared FSM to move a
subscription between ACTIVE and SUSPENDED, logging each transition.

Service layer — imports Types, Config, Repository.
"""

import dataclasses
import sqlite3
import uuid
from datetime import datetime

from app.repository.state_transition_repository import append_state_transition
from app.repository.subscriber_repository import get_subscription_by_id, update_subscription_state
from app.types.enums import SubscriberState
from app.types.exceptions import InvalidSubscriberStateException
from app.types.fsm import transition
from app.types.state_transition import StateTransition
from app.types.subscription import Subscription


def suspend_subscription(
    connection: sqlite3.Connection, subscription_id: str, actor: str, suspended_at: datetime
) -> Subscription:
    """Transition subscription_id from ACTIVE to SUSPENDED (AC-1).

    Raises InvalidSubscriberStateException if it is not currently ACTIVE
    (AC-3, e.g. already SUSPENDED or still PENDING_KYC).
    """
    return _apply_transition(
        connection,
        subscription_id,
        SubscriberState.ACTIVE,
        SubscriberState.SUSPENDED,
        actor,
        suspended_at,
    )


def resume_subscription(
    connection: sqlite3.Connection, subscription_id: str, actor: str, resumed_at: datetime
) -> Subscription:
    """Transition subscription_id from SUSPENDED back to ACTIVE (AC-2).

    Raises InvalidSubscriberStateException if it is not currently
    SUSPENDED (AC-4). This is checked explicitly against the current
    state rather than relying only on the generic FSM edge table,
    because ACTIVE has more than one valid incoming edge (from
    PENDING_KYC via activation, from PORT_OUT_REQUESTED via cancel, and
    from SUSPENDED via resume) — the FSM alone can't tell "resume" apart
    from those other flows.
    """
    return _apply_transition(
        connection,
        subscription_id,
        SubscriberState.SUSPENDED,
        SubscriberState.ACTIVE,
        actor,
        resumed_at,
    )


def _apply_transition(
    connection: sqlite3.Connection,
    subscription_id: str,
    expected_from_state: SubscriberState,
    target_state: SubscriberState,
    actor: str,
    changed_at: datetime,
) -> Subscription:
    subscription = get_subscription_by_id(connection, subscription_id)
    if subscription is None:
        raise ValueError(f"No subscription found for subscription_id {subscription_id!r}")

    if subscription.state != expected_from_state:
        raise InvalidSubscriberStateException(subscription.state, target_state)
    transition(subscription.state, target_state)

    update_subscription_state(connection, subscription_id, target_state, changed_at)
    append_state_transition(
        connection,
        StateTransition(
            transition_id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            from_state=expected_from_state,
            to_state=target_state,
            reason_code=None,
            actor=actor,
            created_at=changed_at,
        ),
    )

    return dataclasses.replace(subscription, state=target_state, updated_at=changed_at)
