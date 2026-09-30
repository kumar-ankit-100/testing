"""Shared domain enums for TelcoLane.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from enum import StrEnum


class SubscriberState(StrEnum):
    """Lifecycle state of a Subscription, driven by the FSM in fsm.py."""

    PENDING_KYC = "PENDING_KYC"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    PORT_OUT_REQUESTED = "PORT_OUT_REQUESTED"
    PORTED_OUT = "PORTED_OUT"


class PlanType(StrEnum):
    """Billing model of a plan catalog entry or subscription."""

    PREPAID = "PREPAID"
    POSTPAID = "POSTPAID"


class Role(StrEnum):
    """Authenticated principal role."""

    SUBSCRIBER = "subscriber"
    CSR = "csr"
    ADMIN = "admin"
    DEALER = "dealer"


class PortOutStatus(StrEnum):
    """Terminal/pending status of a PortOutEvent."""

    PENDING = "PENDING"
    CANCELLED_WITHIN_WINDOW = "CANCELLED_WITHIN_WINDOW"
    FINALIZED = "FINALIZED"


class OverriddenAction(StrEnum):
    """The type of previously-rejected action a CSROverride re-runs."""

    ACTIVATION = "ACTIVATION"
    PLAN_CHANGE = "PLAN_CHANGE"


class ReasonCode(StrEnum):
    """Machine-readable reason codes returned in API error envelopes."""

    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DUPLICATE_ACTIVE_MOBILE = "DUPLICATE_ACTIVE_MOBILE"
    KYC_UNVERIFIED = "KYC_UNVERIFIED"
    DEALER_INVALID = "DEALER_INVALID"
    MNP_FAILED = "MNP_FAILED"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    ALREADY_ACTIVE = "ALREADY_ACTIVE"
    MIN_TENURE_NOT_MET = "MIN_TENURE_NOT_MET"
    SUBSCRIPTION_SUSPENDED = "SUBSCRIPTION_SUSPENDED"
    COOLING_PERIOD_NOT_ELAPSED = "COOLING_PERIOD_NOT_ELAPSED"
    PLAN_VERSION_IMMUTABLE = "PLAN_VERSION_IMMUTABLE"
    MISSING_OVERRIDE_REASON = "MISSING_OVERRIDE_REASON"
    RATE_LIMITED = "RATE_LIMITED"
