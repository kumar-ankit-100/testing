"""Persistence for PortOutEvent rows tracking the 7-day cooling period
(E5-S1).

Repository layer — imports Types and Config only.

Rows are never deleted (a database trigger rejects DELETE); closing an
event is the one legitimate UPDATE (status + closed_at), performed by
close_port_out_event.
"""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from app.types.enums import PortOutStatus
from app.types.port_out import PortOutEvent

_COOLING_PERIOD = timedelta(days=7)
_COLUMNS = (
    "port_out_event_id, subscription_id, requested_at, cooling_period_end_at, status, closed_at"
)


def create_port_out_event(
    connection: sqlite3.Connection, subscription_id: str, requested_at: datetime
) -> PortOutEvent:
    """Create a PENDING port-out event, computing cooling_period_end_at as
    exactly 7 days after requested_at (AC-4).
    """
    event = PortOutEvent(
        port_out_event_id=str(uuid.uuid4()),
        subscription_id=subscription_id,
        requested_at=requested_at,
        cooling_period_end_at=requested_at + _COOLING_PERIOD,
        status=PortOutStatus.PENDING,
        closed_at=None,
    )
    connection.execute(
        f"INSERT INTO port_out_events ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?)",
        (
            event.port_out_event_id,
            event.subscription_id,
            event.requested_at.isoformat(),
            event.cooling_period_end_at.isoformat(),
            event.status.value,
            event.closed_at,
        ),
    )
    connection.commit()
    return event


def get_active_port_out_event(
    connection: sqlite3.Connection, subscription_id: str
) -> PortOutEvent | None:
    """Return the PENDING port-out event for subscription_id, or None."""
    row = connection.execute(
        f"""
        SELECT {_COLUMNS} FROM port_out_events
        WHERE subscription_id = ? AND status = ?
        ORDER BY requested_at DESC
        LIMIT 1
        """,
        (subscription_id, PortOutStatus.PENDING.value),
    ).fetchone()
    return _row_to_port_out_event(row)


def close_port_out_event(
    connection: sqlite3.Connection,
    port_out_event_id: str,
    status: PortOutStatus,
    closed_at: datetime,
) -> None:
    """Set an end status and closed_at; never deletes the row (AC-2)."""
    connection.execute(
        "UPDATE port_out_events SET status = ?, closed_at = ? WHERE port_out_event_id = ?",
        (status.value, closed_at.isoformat(), port_out_event_id),
    )
    connection.commit()


def _row_to_port_out_event(row: tuple[object, ...] | None) -> PortOutEvent | None:
    if row is None:
        return None
    port_out_event_id, subscription_id, requested_at, cooling_period_end_at, status, closed_at = (
        row
    )
    return PortOutEvent(
        port_out_event_id=str(port_out_event_id),
        subscription_id=str(subscription_id),
        requested_at=datetime.fromisoformat(str(requested_at)).replace(tzinfo=UTC),
        cooling_period_end_at=datetime.fromisoformat(str(cooling_period_end_at)).replace(
            tzinfo=UTC
        ),
        status=PortOutStatus(str(status)),
        closed_at=None if closed_at is None else datetime.fromisoformat(str(closed_at)).replace(
            tzinfo=UTC
        ),
    )
