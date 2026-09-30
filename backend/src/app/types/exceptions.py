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


class AuthenticationError(Exception):
    """Raised when no valid authenticated principal could be established (E1-S4)."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)


class AuthorizationError(Exception):
    """Raised when an authenticated principal lacks permission for the action (E1-S4)."""

    def __init__(self, message: str = "Not authorized to perform this action") -> None:
        super().__init__(message)
