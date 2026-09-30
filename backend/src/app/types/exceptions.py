"""Typed domain exceptions for TelcoLane.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from app.types.enums import SubscriberState


class InvalidSubscriberStateException(Exception):
    """Raised when an FSM transition is attempted for a pair not in the table."""

    def __init__(self, from_state: SubscriberState, to_state: SubscriberState) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition from {from_state.value} to {to_state.value}"
        )
