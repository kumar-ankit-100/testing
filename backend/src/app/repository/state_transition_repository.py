"""Append-only persistence for StateTransition audit rows (E5-S1).

Repository layer — imports Types and Config only.

Only append_state_transition and list_state_transitions_for_subscription
are exposed; no update/delete function exists. A database trigger
(schema.sql) additionally rejects any raw-SQL UPDATE/DELETE attempt.
"""

import sqlite3
from datetime import UTC, datetime

from app.types.enums import SubscriberState
from app.types.state_transition import StateTransition

_COLUMNS = "transition_id, subscription_id, from_state, to_state, reason_code, actor, created_at"


def append_state_transition(connection: sqlite3.Connection, transition: StateTransition) -> None:
    """Insert a new, immutable state transition row."""
    connection.execute(
        f"INSERT INTO state_transitions ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            transition.transition_id,
            transition.subscription_id,
            transition.from_state.value,
            transition.to_state.value,
            transition.reason_code,
            transition.actor,
            transition.created_at.isoformat(),
        ),
    )
    connection.commit()


def list_state_transitions_for_subscription(
    connection: sqlite3.Connection, subscription_id: str
) -> list[StateTransition]:
    """Return every transition for subscription_id, oldest first (AC-3)."""
    rows = connection.execute(
        f"""
        SELECT {_COLUMNS} FROM state_transitions
        WHERE subscription_id = ?
        ORDER BY created_at ASC
        """,
        (subscription_id,),
    ).fetchall()
    return [_row_to_state_transition(row) for row in rows]


def _row_to_state_transition(row: tuple[object, ...]) -> StateTransition:
    transition_id, subscription_id, from_state, to_state, reason_code, actor, created_at = row
    return StateTransition(
        transition_id=str(transition_id),
        subscription_id=str(subscription_id),
        from_state=SubscriberState(str(from_state)),
        to_state=SubscriberState(str(to_state)),
        reason_code=None if reason_code is None else str(reason_code),
        actor=str(actor),
        created_at=datetime.fromisoformat(str(created_at)).replace(tzinfo=UTC),
    )
