"""PortOutEvent domain type.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass
from datetime import datetime

from app.types.enums import PortOutStatus


@dataclass(frozen=True)
class PortOutEvent:
    """An append-only record tracking the 7-day port-out cooling period."""

    port_out_event_id: str
    subscription_id: str
    requested_at: datetime
    cooling_period_end_at: datetime
    status: PortOutStatus
    closed_at: datetime | None
