"""Persistence for User accounts backing login (E1-S4).

Repository layer — imports Types and Config only.
"""

import sqlite3
from datetime import UTC, datetime

from app.types.auth import User
from app.types.enums import Role

_INSERT_USER_SQL = """
    INSERT INTO users (
        user_id, role, username, password_hash, mobile_number, subscriber_id, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
"""
_SELECT_COLUMNS = "user_id, role, username, password_hash, mobile_number, subscriber_id, created_at"


def create_user(connection: sqlite3.Connection, user: User) -> None:
    """Insert a new user row."""
    connection.execute(
        _INSERT_USER_SQL,
        (
            user.user_id,
            user.role.value,
            user.username,
            user.password_hash,
            user.mobile_number,
            user.subscriber_id,
            user.created_at.isoformat(),
        ),
    )
    connection.commit()


def get_user_by_id(connection: sqlite3.Connection, user_id: str) -> User | None:
    """Return the user with user_id, or None if no such user exists."""
    row = connection.execute(
        f"SELECT {_SELECT_COLUMNS} FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    return _row_to_user(row)


def get_user_by_username(connection: sqlite3.Connection, username: str) -> User | None:
    """Return the user with username, or None if no such user exists."""
    row = connection.execute(
        f"SELECT {_SELECT_COLUMNS} FROM users WHERE username = ?", (username,)
    ).fetchone()
    return _row_to_user(row)


def get_user_by_mobile(connection: sqlite3.Connection, mobile_number: str) -> User | None:
    """Return the user with mobile_number, or None if no such user exists."""
    row = connection.execute(
        f"SELECT {_SELECT_COLUMNS} FROM users WHERE mobile_number = ?", (mobile_number,)
    ).fetchone()
    return _row_to_user(row)


def _row_to_user(row: tuple[object, ...] | None) -> User | None:
    if row is None:
        return None
    user_id, role, username, password_hash, mobile_number, subscriber_id, created_at = row
    return User(
        user_id=str(user_id),
        role=Role(str(role)),
        username=_as_optional_str(username),
        password_hash=_as_optional_str(password_hash),
        mobile_number=_as_optional_str(mobile_number),
        subscriber_id=_as_optional_str(subscriber_id),
        created_at=datetime.fromisoformat(str(created_at)).replace(tzinfo=UTC),
    )


def _as_optional_str(value: object) -> str | None:
    return None if value is None else str(value)
