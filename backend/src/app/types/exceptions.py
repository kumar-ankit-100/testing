"""Typed domain exceptions for TelcoLane.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from app.types.enums import ReasonCode, SubscriberState


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


class InvalidMobileNumberError(Exception):
    """Raised when a mobile number does not match the 10-digit pattern (E2-S2)."""

    def __init__(self, mobile_number: str) -> None:
        self.mobile_number = mobile_number
        super().__init__(f"Mobile number {mobile_number!r} is not a valid 10-digit number")


class DuplicateActiveSubscriptionError(Exception):
    """Raised when a mobile number already has an ACTIVE subscription (E2-S2)."""

    def __init__(self, mobile_number: str) -> None:
        self.mobile_number = mobile_number
        super().__init__(
            f"Mobile number {mobile_number!r} already has an ACTIVE subscription"
        )


class PlanVersionImmutableError(Exception):
    """Raised when a caller attempts to edit an already-published plan
    version's price or terms (E3-S2 AC-3), ahead of the DB trigger that
    backstops the same rule if this check is somehow bypassed.
    """

    def __init__(self, plan_version_id: str) -> None:
        self.plan_version_id = plan_version_id
        super().__init__(
            f"Plan version {plan_version_id!r} is published and cannot be modified; "
            "create a new version instead"
        )


class ActivationRejectedError(Exception):
    """Raised when an activation attempt fails a rule check (E2-S3).

    Carries the specific machine-readable reason_code (KYC_UNVERIFIED,
    DEALER_INVALID, or MNP_FAILED) so a single exception type can map to
    HTTP 422 at the API layer without three separate exception classes.
    """

    def __init__(self, reason_code: ReasonCode) -> None:
        self.reason_code = reason_code
        super().__init__(f"Activation rejected: {reason_code.value}")
