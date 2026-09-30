"""Types layer — shared domain models and FSM contracts.

Zero imports from Config, Repository, Service, API, or UI.
"""

from app.types.billing import BillingRecord
from app.types.csr_override import CSROverride
from app.types.dealer import DealerMaster
from app.types.enums import (
    OverriddenAction,
    PlanType,
    PortOutStatus,
    ReasonCode,
    Role,
    SubscriberState,
)
from app.types.exceptions import InvalidSubscriberStateException
from app.types.fsm import TRANSITION_TABLE, transition
from app.types.plan import PlanVersion
from app.types.port_out import PortOutEvent
from app.types.state_transition import StateTransition
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

__all__ = [
    "TRANSITION_TABLE",
    "BillingRecord",
    "CSROverride",
    "DealerMaster",
    "InvalidSubscriberStateException",
    "OverriddenAction",
    "PlanType",
    "PlanVersion",
    "PortOutEvent",
    "PortOutStatus",
    "ReasonCode",
    "Role",
    "StateTransition",
    "Subscriber",
    "SubscriberState",
    "Subscription",
    "transition",
]
