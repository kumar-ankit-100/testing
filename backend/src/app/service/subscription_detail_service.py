"""Subscriber-facing subscription detail view: the subscription record
enriched with its current plan's name/price/terms, for the subscriber
dashboard. Read-only — no state mutation, no role restriction here
(the API layer's require_own_subscriber dependency is what keeps a
subscriber from reading someone else's subscription).

Service layer — imports Types, Config, Repository only.
"""

import sqlite3
from dataclasses import dataclass

from app.repository.plan_repository import get_plan_version_by_id
from app.repository.subscriber_repository import get_subscription_by_subscriber_id
from app.types.plan import PlanVersion
from app.types.subscription import Subscription


@dataclass(frozen=True)
class SubscriptionDetail:
    subscription: Subscription
    current_plan: PlanVersion | None


def get_subscription_detail(
    connection: sqlite3.Connection, subscriber_id: str
) -> SubscriptionDetail:
    """Raises ValueError if subscriber_id has no subscription row."""
    subscription = get_subscription_by_subscriber_id(connection, subscriber_id)
    if subscription is None:
        raise ValueError(f"Subscription for subscriber {subscriber_id!r} not found")

    current_plan = (
        get_plan_version_by_id(connection, subscription.current_plan_version_id)
        if subscription.current_plan_version_id is not None
        else None
    )
    return SubscriptionDetail(subscription=subscription, current_plan=current_plan)
