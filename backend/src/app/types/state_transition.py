"""StateTransition domain type.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass
from datetime import datetime

from app.types.enums import SubscriberState


@dataclass(frozen=True)
class StateTransition:
    """An append-only audit row for one FSM transition."""

    transition_id: str
    subscription_id: str
    from_state: SubscriberState
    to_state: SubscriberState
    reason_code: str | None
    actor: str
    created_at: datetime
