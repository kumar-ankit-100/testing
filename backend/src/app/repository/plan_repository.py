"""Persistence for versioned, immutable-once-published PlanVersion records
(E3-S1).

Repository layer — imports Types and Config only.

No update_plan_version or delete_plan_version function exists: the only
mutator is publish_plan_version, a one-time draft -> published flip. A
database trigger (schema.sql) additionally rejects any UPDATE/DELETE
against an already-published row as defense-in-depth.
"""

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal

from app.types.enums import PlanType
from app.types.plan import PlanVersion

_COLUMNS = (
    "plan_version_id, plan_id, plan_name, plan_type, version_number, "
    "price, terms, published, created_at, published_at"
)


def create_plan_version(connection: sqlite3.Connection, plan_version: PlanVersion) -> None:
    """Insert a new plan version row (typically an unpublished draft)."""
    connection.execute(
        f"INSERT INTO plan_versions ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            plan_version.plan_version_id,
            plan_version.plan_id,
            plan_version.plan_name,
            plan_version.plan_type.value,
            plan_version.version_number,
            str(plan_version.price),
            json.dumps(plan_version.terms),
            int(plan_version.published),
            plan_version.created_at.isoformat(),
            plan_version.published_at.isoformat() if plan_version.published_at else None,
        ),
    )
    connection.commit()


def publish_plan_version(
    connection: sqlite3.Connection, plan_version_id: str, published_at: datetime
) -> None:
    """Flip a draft to published, stamping published_at.

    Raises sqlite3.IntegrityError if plan_version_id is already published
    (trg_plan_versions_immutable_once_published fires on the UPDATE).
    """
    connection.execute(
        "UPDATE plan_versions SET published = 1, published_at = ? WHERE plan_version_id = ?",
        (published_at.isoformat(), plan_version_id),
    )
    connection.commit()


def update_draft_plan_version(
    connection: sqlite3.Connection,
    plan_version_id: str,
    price: Decimal,
    terms: dict[str, object],
) -> None:
    """Update a draft (unpublished) version's price/terms.

    Raises sqlite3.IntegrityError if plan_version_id is already published
    (trg_plan_versions_immutable_once_published fires on the UPDATE) — the
    service layer checks first and raises PlanVersionImmutableError for a
    friendlier error; this trigger is the ultimate backstop (E3-S2 AC-3).
    """
    connection.execute(
        "UPDATE plan_versions SET price = ?, terms = ? WHERE plan_version_id = ?",
        (str(price), json.dumps(terms), plan_version_id),
    )
    connection.commit()


def get_published_version(connection: sqlite3.Connection, plan_id: str) -> PlanVersion | None:
    """Return the currently published version for plan_id.

    "Currently published" = the highest version_number among rows with
    published=1 (older published versions remain in the table forever —
    append-only — but are superseded by version ordering, never by
    mutating their own published flag, which the trigger forbids).
    """
    row = connection.execute(
        f"""
        SELECT {_COLUMNS} FROM plan_versions
        WHERE plan_id = ? AND published = 1
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (plan_id,),
    ).fetchone()
    return _row_to_plan_version(row)


def list_versions(connection: sqlite3.Connection, plan_id: str) -> list[PlanVersion]:
    """Return every version of plan_id, ascending by version_number (AC-3)."""
    rows = connection.execute(
        f"""
        SELECT {_COLUMNS} FROM plan_versions
        WHERE plan_id = ?
        ORDER BY version_number ASC
        """,
        (plan_id,),
    ).fetchall()
    return [version for row in rows if (version := _row_to_plan_version(row)) is not None]


def get_plan_version_by_id(
    connection: sqlite3.Connection, plan_version_id: str
) -> PlanVersion | None:
    """Return the version with plan_version_id, or None — a global lookup
    across all plans, not scoped to a single plan_id (E3-S3: the admin
    API's publish/edit routes receive only plan_version_id in the URL).
    """
    row = connection.execute(
        f"SELECT {_COLUMNS} FROM plan_versions WHERE plan_version_id = ?",
        (plan_version_id,),
    ).fetchone()
    return _row_to_plan_version(row)


def list_all_plan_versions(connection: sqlite3.Connection) -> list[PlanVersion]:
    """Return every version across every plan_id, ordered by plan_id then
    version_number — the full catalog history (E3-S3 AC-4).
    """
    rows = connection.execute(
        f"""
        SELECT {_COLUMNS} FROM plan_versions
        ORDER BY plan_id ASC, version_number ASC
        """
    ).fetchall()
    return [version for row in rows if (version := _row_to_plan_version(row)) is not None]


def _row_to_plan_version(row: tuple[object, ...] | None) -> PlanVersion | None:
    if row is None:
        return None
    (
        plan_version_id,
        plan_id,
        plan_name,
        plan_type,
        version_number,
        price,
        terms,
        published,
        created_at,
        published_at,
    ) = row
    return PlanVersion(
        plan_version_id=str(plan_version_id),
        plan_id=str(plan_id),
        plan_name=str(plan_name),
        plan_type=PlanType(str(plan_type)),
        version_number=int(str(version_number)),
        price=Decimal(str(price)),
        terms=json.loads(str(terms)),
        published=bool(published),
        created_at=datetime.fromisoformat(str(created_at)).replace(tzinfo=UTC),
        published_at=_as_optional_datetime(published_at),
    )


def _as_optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(str(value)).replace(tzinfo=UTC)
