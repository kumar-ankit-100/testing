"""CSR override service (E6-S2): a CSR re-runs a previously-rejected
activation or plan-change, bypassing only the specific rule that
originally failed, while every other code path (FSM validity, state
checks) stays exactly as strict as the unprivileged call.

Service layer — imports Types, Config, Repository, and the
activation_service / plan_change_service functions it re-invokes.
Per system-design.md 5.8, an override never mutates state directly; it
re-invokes the same authoritative service function with the rule bypass
flag set, so there is only ever one code path that can produce ACTIVE
or a committed plan change.
"""

import sqlite3
import uuid
from datetime import datetime

from app.config.settings import Settings
from app.repository.csr_override_repository import create_csr_override
from app.service.activation_service import activate_subscriber
from app.service.logging_service import get_logger
from app.service.plan_change_service import commit_plan_change
from app.types.auth import Principal
from app.types.billing import BillingRecord
from app.types.csr_override import CSROverride
from app.types.enums import OverriddenAction, Role
from app.types.exceptions import AuthorizationError, MissingOverrideReasonError
from app.types.subscription import Subscription

_logger = get_logger(__name__)


def override_rejected_activation(
    connection: sqlite3.Connection,
    principal: Principal,
    subscriber_id: str,
    dealer_code: str,
    settings: Settings,
    overridden_at: datetime,
    reason_code: str,
    original_rejection_reason: str,
) -> Subscription:
    """CSR forces a previously-rejected activation through (AC-1).

    Raises MissingOverrideReasonError if reason_code is falsy, before any
    state change or record write (AC-3). Raises AuthorizationError if
    principal is not a CSR, before any state change or record write
    (AC-4). Every attempt that reaches persistence — success or failure
    of the underlying activation — logs a structured entry with a masked
    actor and the reason_code (AC-5).
    """
    _require_csr(principal)
    _require_reason_code(reason_code)

    subscription = activate_subscriber(
        connection,
        subscriber_id,
        dealer_code,
        settings,
        overridden_at,
        skip_rule_checks=True,
    )

    _record_override(
        connection,
        subscription.subscription_id,
        principal,
        reason_code,
        OverriddenAction.ACTIVATION,
        original_rejection_reason,
        overridden_at,
    )
    return subscription


def override_rejected_plan_change(
    connection: sqlite3.Connection,
    principal: Principal,
    subscription_id: str,
    target_plan_version_id: str,
    change_at: datetime,
    settings: Settings,
    reason_code: str,
    original_rejection_reason: str,
) -> BillingRecord:
    """CSR forces a previously-rejected plan change through (AC-2).

    Raises MissingOverrideReasonError if reason_code is falsy, before any
    state change or record write (AC-3). Raises AuthorizationError if
    principal is not a CSR, before any state change or record write
    (AC-4).
    """
    _require_csr(principal)
    _require_reason_code(reason_code)

    record = commit_plan_change(
        connection,
        subscription_id,
        target_plan_version_id,
        change_at,
        settings,
        skip_eligibility_checks=True,
    )

    _record_override(
        connection,
        subscription_id,
        principal,
        reason_code,
        OverriddenAction.PLAN_CHANGE,
        original_rejection_reason,
        change_at,
    )
    return record


def _require_csr(principal: Principal) -> None:
    if principal.role != Role.CSR:
        raise AuthorizationError(f"Role {principal.role.value} may not perform CSR overrides")


def _require_reason_code(reason_code: str) -> None:
    if not reason_code:
        raise MissingOverrideReasonError()


def _record_override(
    connection: sqlite3.Connection,
    subscription_id: str,
    principal: Principal,
    reason_code: str,
    overridden_action: OverriddenAction,
    original_rejection_reason: str,
    created_at: datetime,
) -> None:
    actor = f"{principal.role.value}:{principal.user_id}"
    create_csr_override(
        connection,
        CSROverride(
            override_id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            actor=actor,
            reason_code=reason_code,
            overridden_action=overridden_action,
            original_rejection_reason=original_rejection_reason,
            created_at=created_at,
        ),
    )
    _logger.info(
        "CSR override recorded",
        extra={
            "context": {
                "subscription_id": subscription_id,
                "actor": actor,
                "reason_code": reason_code,
                "overridden_action": overridden_action.value,
            }
        },
    )


__all__ = [
    "override_rejected_activation",
    "override_rejected_plan_change",
]
