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


class CoolingPeriodNotElapsedError(Exception):
    """Raised when finalizing a port-out before its 7-day cooling period
    has elapsed (E5-S3 AC-4). reason_code: COOLING_PERIOD_NOT_ELAPSED.
    """

    def __init__(self, subscription_id: str) -> None:
        self.subscription_id = subscription_id
        super().__init__(
            f"Port-out for subscription {subscription_id!r} cannot be finalized: "
            "cooling period has not elapsed"
        )


class MinTenureNotMetError(Exception):
    """Raised when a plan change is requested before the minimum-tenure
    period has elapsed (E4-S3 AC-1). reason_code: MIN_TENURE_NOT_MET.
    """

    def __init__(self, subscription_id: str) -> None:
        self.subscription_id = subscription_id
        super().__init__(
            f"Subscription {subscription_id!r} has not met the minimum tenure period"
        )


class SubscriptionSuspendedError(Exception):
    """Raised when a plan change is requested on a SUSPENDED subscription
    (E4-S3 AC-2). reason_code: SUBSCRIPTION_SUSPENDED.
    """

    def __init__(self, subscription_id: str) -> None:
        self.subscription_id = subscription_id
        super().__init__(f"Subscription {subscription_id!r} is suspended")


class MissingOverrideReasonError(Exception):
    """Raised when a CSR override is attempted without a reason_code
    (E6-S2 AC-3). No state change or CSROverride record is written.
    """

    def __init__(self) -> None:
        super().__init__("A reason_code is required to perform a CSR override")


class SubscriptionNotActiveError(Exception):
    """Raised when a plan change is requested on a subscription that is
    neither ACTIVE nor SUSPENDED (e.g. PENDING_KYC, PORT_OUT_REQUESTED,
    PORTED_OUT, TERMINATED). reason_code: INVALID_STATE_TRANSITION.
    """

    def __init__(self, subscription_id: str, current_state: SubscriberState) -> None:
        self.subscription_id = subscription_id
        self.current_state = current_state
        super().__init__(
            f"Subscription {subscription_id!r} is {current_state.value}, "
            "not eligible for a plan change"
        )


class DuplicateUsernameError(Exception):
    """Raised when staff self-registration is attempted with a username
    that already exists. reason_code: DUPLICATE_USERNAME.
    """

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Username {username!r} is already taken")
