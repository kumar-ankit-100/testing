"""Append-only, audited persistence for CSROverride rows (E6-S1).

Repository layer — imports Types and Config only.

Only create_csr_override and list_csr_overrides_for_subscription are
exposed; no update/delete function exists. A database trigger
(schema.sql) additionally rejects any raw-SQL UPDATE/DELETE attempt.
"""

import sqlite3
from datetime import UTC, datetime

from app.types.csr_override import CSROverride
from app.types.enums import OverriddenAction

_COLUMNS = (
    "override_id, subscription_id, actor, reason_code, overridden_action, "
    "original_rejection_reason, created_at"
)


def create_csr_override(connection: sqlite3.Connection, override: CSROverride) -> None:
    """Insert a new, immutable CSR override audit row."""
    connection.execute(
        f"INSERT INTO csr_overrides ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            override.override_id,
            override.subscription_id,
            override.actor,
            override.reason_code,
            override.overridden_action.value,
            override.original_rejection_reason,
            override.created_at.isoformat(),
        ),
    )
    connection.commit()


def list_csr_overrides_for_subscription(
    connection: sqlite3.Connection, subscription_id: str
) -> list[CSROverride]:
    """Return every override for subscription_id, oldest first."""
    rows = connection.execute(
        f"""
        SELECT {_COLUMNS} FROM csr_overrides
        WHERE subscription_id = ?
        ORDER BY created_at ASC
        """,
        (subscription_id,),
    ).fetchall()
    return [_row_to_csr_override(row) for row in rows]


def _row_to_csr_override(row: tuple[object, ...]) -> CSROverride:
    (
        override_id,
        subscription_id,
        actor,
        reason_code,
        overridden_action,
        original_rejection_reason,
        created_at,
    ) = row
    return CSROverride(
        override_id=str(override_id),
        subscription_id=str(subscription_id),
        actor=str(actor),
        reason_code=str(reason_code),
        overridden_action=OverriddenAction(str(overridden_action)),
        original_rejection_reason=str(original_rejection_reason),
        created_at=datetime.fromisoformat(str(created_at)).replace(tzinfo=UTC),
    )
