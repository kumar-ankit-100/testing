"""Subscription domain type.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass
from datetime import datetime

from app.types.enums import PlanType, SubscriberState


@dataclass(frozen=True)
class Subscription:
    """A subscriber's line, tracked through the SubscriberState FSM."""

    subscription_id: str
    subscriber_id: str
    mobile_number: str
    plan_type: PlanType
    state: SubscriberState
    current_plan_version_id: str | None
    dealer_code: str | None
    created_at: datetime
    activated_at: datetime | None
    updated_at: datetime
