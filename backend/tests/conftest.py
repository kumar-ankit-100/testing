"""Shared pytest fixtures for backend tests.

`sqlite_connection` gives repository tests a temp-file SQLite connection
with the full repository/schema.sql DDL already applied, so each
repository test file doesn't duplicate that setup.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config.db import create_connection
from app.repository.schema import apply_schema


@pytest.fixture
def sqlite_connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = create_connection(str(tmp_path / "telcolane_test.db"))
    apply_schema(connection)
    try:
        yield connection
    finally:
        connection.close()
