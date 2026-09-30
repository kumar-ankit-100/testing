"""SQLite connection factory for TelcoLane.

Config layer — imports Types only (here: no imports needed beyond stdlib).
"""

import sqlite3


def create_connection(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection to db_path with WAL journal mode applied.

    WAL mode is applied immediately after connecting, before the connection
    is handed to any caller, so every consumer of this factory gets a
    connection that is already configured per E1-S2 AC-2.
    """
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL")
    return connection
