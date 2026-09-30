"""Declarative subscriber-state FSM.

Types layer — zero imports from Config, Repository, Service, API, or UI.

Every service that mutates subscription state (activation, suspend/resume,
port-out, termination, CSR override) shares this single authority for
"is this move legal" so a new rule is a one-line table edit instead of
duplicated conditionals scattered across services.
"""

from app.types.enums import SubscriberState
from app.types.exceptions import InvalidSubscriberStateException

TRANSITION_TABLE: frozenset[tuple[SubscriberState, SubscriberState]] = frozenset(
    {
        (SubscriberState.PENDING_KYC, SubscriberState.ACTIVE),
        (SubscriberState.ACTIVE, SubscriberState.SUSPENDED),
        (SubscriberState.SUSPENDED, SubscriberState.ACTIVE),
        (SubscriberState.ACTIVE, SubscriberState.PORT_OUT_REQUESTED),
        (SubscriberState.PORT_OUT_REQUESTED, SubscriberState.ACTIVE),
        (SubscriberState.PORT_OUT_REQUESTED, SubscriberState.PORTED_OUT),
        (SubscriberState.ACTIVE, SubscriberState.TERMINATED),
        (SubscriberState.SUSPENDED, SubscriberState.TERMINATED),
    }
)


def transition(
    current_state: SubscriberState, target_state: SubscriberState
) -> SubscriberState:
    """Return target_state if (current_state, target_state) is a valid edge.

    Raises InvalidSubscriberStateException if the pair is not in
    TRANSITION_TABLE.
    """
    if (current_state, target_state) not in TRANSITION_TABLE:
        raise InvalidSubscriberStateException(current_state, target_state)
    return target_state
