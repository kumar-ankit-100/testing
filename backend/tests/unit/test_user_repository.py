"""Unit tests for user_repository (E1-S4)."""

import sqlite3
from datetime import UTC, datetime

from app.repository.user_repository import (
    create_user,
    get_user_by_id,
    get_user_by_mobile,
    get_user_by_username,
)
from app.types.auth import User
from app.types.enums import Role


def _build_csr_user(user_id: str, username: str) -> User:
    return User(
        user_id=user_id,
        role=Role.CSR,
        username=username,
        password_hash="$2b$12$abcdefghijklmnopqrstuv",
        mobile_number=None,
        subscriber_id=None,
        created_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
    )


def test_create_and_get_user_by_id_round_trips(sqlite_connection: sqlite3.Connection) -> None:
    user = _build_csr_user("1a2b3c4d-0001-4e11-9f22-333344445555", "csr.priya")

    create_user(sqlite_connection, user)
    fetched = get_user_by_id(sqlite_connection, user.user_id)

    assert fetched == user


def test_get_user_by_id_returns_none_when_not_found(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_user_by_id(sqlite_connection, "does-not-exist") is None


def test_get_user_by_username_finds_the_matching_row(
    sqlite_connection: sqlite3.Connection,
) -> None:
    user = _build_csr_user("1a2b3c4d-0002-4e11-9f22-333344445555", "admin.rahul")
    create_user(sqlite_connection, user)

    fetched = get_user_by_username(sqlite_connection, "admin.rahul")

    assert fetched == user


def test_get_user_by_username_returns_none_when_not_found(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_user_by_username(sqlite_connection, "nobody.here") is None


def test_get_user_by_mobile_finds_a_subscriber_user(
    sqlite_connection: sqlite3.Connection,
) -> None:
    subscriber_user = User(
        user_id="1a2b3c4d-0003-4e11-9f22-333344445555",
        role=Role.SUBSCRIBER,
        username=None,
        password_hash=None,
        mobile_number="9876547890",
        subscriber_id="7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f",
        created_at=datetime(2026, 1, 6, 11, 30, tzinfo=UTC),
    )
    create_user(sqlite_connection, subscriber_user)

    fetched = get_user_by_mobile(sqlite_connection, "9876547890")

    assert fetched == subscriber_user


def test_get_user_by_mobile_returns_none_when_not_found(
    sqlite_connection: sqlite3.Connection,
) -> None:
    assert get_user_by_mobile(sqlite_connection, "9000000000") is None


def test_create_user_persists_null_optional_fields_as_none(
    sqlite_connection: sqlite3.Connection,
) -> None:
    admin_user = User(
        user_id="1a2b3c4d-0004-4e11-9f22-333344445555",
        role=Role.ADMIN,
        username="admin.only",
        password_hash="$2b$12$zzzzzzzzzzzzzzzzzzzzzz",
        mobile_number=None,
        subscriber_id=None,
        created_at=datetime(2026, 1, 7, 12, 0, tzinfo=UTC),
    )

    create_user(sqlite_connection, admin_user)
    fetched = get_user_by_id(sqlite_connection, admin_user.user_id)

    assert fetched is not None
    assert fetched.mobile_number is None
    assert fetched.subscriber_id is None


def test_schema_seeds_exactly_one_demo_user_per_staff_role(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """E1-S6 AC-4: exactly one seeded demo user for each of CSR, ADMIN,
    and DEALER, with password_hash populated via a real KDF (never
    plaintext).
    """
    for role in (Role.CSR, Role.ADMIN, Role.DEALER):
        row = sqlite_connection.execute(
            "SELECT COUNT(*) FROM users WHERE role = ?", (role.value,)
        ).fetchone()
        assert row[0] == 1, f"expected exactly one seeded {role.value} user"

    rows = sqlite_connection.execute(
        "SELECT username, password_hash FROM users WHERE role IN ('csr', 'admin', 'dealer')"
    ).fetchall()
    for username, password_hash in rows:
        assert username is not None
        assert password_hash is not None
        assert password_hash.startswith("pbkdf2_sha256$")


def test_seeded_csr_user_is_findable_by_username(
    sqlite_connection: sqlite3.Connection,
) -> None:
    user = get_user_by_username(sqlite_connection, "csr_jane")

    assert user is not None
    assert user.role == Role.CSR
    assert user.password_hash is not None
    assert "CsrDemo" not in user.password_hash
