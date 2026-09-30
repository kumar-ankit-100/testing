"""Unit tests for the request-scoped DB connection dependency (E3-S3)."""

import sqlite3
from pathlib import Path

import pytest

from app.api.deps import get_db_connection
from app.config.settings import Settings


def test_get_db_connection_yields_a_working_sqlite_connection(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, db_path=str(tmp_path / "deps_test.db"))

    generator = get_db_connection(settings)
    connection = next(generator)

    try:
        assert isinstance(connection, sqlite3.Connection)
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal_mode == "wal"
    finally:
        with pytest.raises(StopIteration):
            next(generator)


def test_get_db_connection_closes_the_connection_after_the_request(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, db_path=str(tmp_path / "deps_test_close.db"))

    generator = get_db_connection(settings)
    connection = next(generator)
    with pytest.raises(StopIteration):
        next(generator)

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
