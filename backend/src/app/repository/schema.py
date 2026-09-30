"""Applies repository/schema.sql to a SQLite connection (migration entry point).

Repository layer — imports Types, Config only (here: no imports needed
beyond stdlib). This is the "application startup/migration" mechanism
referenced by E2-S1 AC-3 and every other append-only-table story in this
group: schema.sql is executed once, idempotently (CREATE TABLE IF NOT
EXISTS / INSERT OR IGNORE), against a real or test connection.
"""

import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def apply_schema(connection: sqlite3.Connection) -> None:
    """Execute the full schema.sql DDL script against connection."""
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    connection.executescript(schema_sql)
    connection.commit()
