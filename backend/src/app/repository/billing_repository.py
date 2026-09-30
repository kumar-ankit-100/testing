"""Append-only persistence for BillingRecord entries (E4-S1).

Repository layer — imports Types and Config only.

Only create_billing_record and list_billing_records_for_subscription are
exposed; no update/delete function exists. A database trigger
(schema.sql) additionally rejects any raw-SQL UPDATE/DELETE attempt.
"""

import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal

from app.types.billing import BillingRecord

_COLUMNS = (
    "billing_record_id, subscription_id, from_plan_version_id, to_plan_version_id, "
    "pro_rata_amount, charges_total, billing_period_start, billing_period_end, created_at"
)


def create_billing_record(connection: sqlite3.Connection, record: BillingRecord) -> None:
    """Insert a new, immutable billing record row."""
    connection.execute(
        f"INSERT INTO billing_records ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            record.billing_record_id,
            record.subscription_id,
            record.from_plan_version_id,
            record.to_plan_version_id,
            str(record.pro_rata_amount),
            str(record.charges_total),
            record.billing_period_start.isoformat(),
            record.billing_period_end.isoformat(),
            record.created_at.isoformat(),
        ),
    )
    connection.commit()


def list_billing_records_for_subscription(
    connection: sqlite3.Connection, subscription_id: str
) -> list[BillingRecord]:
    """Return every billing record for subscription_id, oldest first."""
    rows = connection.execute(
        f"""
        SELECT {_COLUMNS} FROM billing_records
        WHERE subscription_id = ?
        ORDER BY created_at ASC
        """,
        (subscription_id,),
    ).fetchall()
    return [_row_to_billing_record(row) for row in rows]


def _row_to_billing_record(row: tuple[object, ...]) -> BillingRecord:
    (
        billing_record_id,
        subscription_id,
        from_plan_version_id,
        to_plan_version_id,
        pro_rata_amount,
        charges_total,
        billing_period_start,
        billing_period_end,
        created_at,
    ) = row
    return BillingRecord(
        billing_record_id=str(billing_record_id),
        subscription_id=str(subscription_id),
        from_plan_version_id=_as_optional_str(from_plan_version_id),
        to_plan_version_id=str(to_plan_version_id),
        pro_rata_amount=Decimal(str(pro_rata_amount)),
        charges_total=Decimal(str(charges_total)),
        billing_period_start=date.fromisoformat(str(billing_period_start)),
        billing_period_end=date.fromisoformat(str(billing_period_end)),
        created_at=datetime.fromisoformat(str(created_at)).replace(tzinfo=UTC),
    )


def _as_optional_str(value: object) -> str | None:
    return None if value is None else str(value)
