"""Unit tests for the declarative subscriber-state FSM (E1-S1 AC-2)."""

import pytest

from app.types.enums import SubscriberState
from app.types.exceptions import InvalidSubscriberStateException
from app.types.fsm import TRANSITION_TABLE, transition

VALID_TRANSITIONS: list[tuple[SubscriberState, SubscriberState]] = [
    (SubscriberState.PENDING_KYC, SubscriberState.ACTIVE),
    (SubscriberState.ACTIVE, SubscriberState.SUSPENDED),
    (SubscriberState.SUSPENDED, SubscriberState.ACTIVE),
    (SubscriberState.ACTIVE, SubscriberState.PORT_OUT_REQUESTED),
    (SubscriberState.PORT_OUT_REQUESTED, SubscriberState.ACTIVE),
    (SubscriberState.PORT_OUT_REQUESTED, SubscriberState.PORTED_OUT),
    (SubscriberState.ACTIVE, SubscriberState.TERMINATED),
    (SubscriberState.SUSPENDED, SubscriberState.TERMINATED),
]


def test_transition_table_contains_exactly_the_eight_valid_edges() -> None:
    assert TRANSITION_TABLE == frozenset(VALID_TRANSITIONS)
    assert len(TRANSITION_TABLE) == 8


@pytest.mark.parametrize(("from_state", "to_state"), VALID_TRANSITIONS)
def test_transition_returns_target_state_for_each_valid_edge(
    from_state: SubscriberState, to_state: SubscriberState
) -> None:
    assert transition(from_state, to_state) == to_state


def test_transition_raises_for_pair_not_in_table() -> None:
    with pytest.raises(InvalidSubscriberStateException):
        transition(SubscriberState.PENDING_KYC, SubscriberState.SUSPENDED)


def test_transition_raises_for_terminal_state_reentry() -> None:
    with pytest.raises(InvalidSubscriberStateException):
        transition(SubscriberState.TERMINATED, SubscriberState.ACTIVE)


def test_transition_raises_for_ported_out_reentry() -> None:
    with pytest.raises(InvalidSubscriberStateException):
        transition(SubscriberState.PORTED_OUT, SubscriberState.ACTIVE)


def test_invalid_transition_exception_carries_from_and_to_state() -> None:
    try:
        transition(SubscriberState.PENDING_KYC, SubscriberState.TERMINATED)
    except InvalidSubscriberStateException as exc:
        assert exc.from_state == SubscriberState.PENDING_KYC
        assert exc.to_state == SubscriberState.TERMINATED
        assert "PENDING_KYC" in str(exc)
        assert "TERMINATED" in str(exc)
    else:
        pytest.fail("expected InvalidSubscriberStateException to be raised")
