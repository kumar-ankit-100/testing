"""Unit tests for dynamic staff self-registration (CSR/admin/dealer),
closing the "only seeded demo users exist" gap — before this, there was
no way to create a new staff account without hand-editing schema.sql.
"""

import sqlite3

import pytest

from app.repository.user_repository import get_user_by_username
from app.service.auth_service import verify_password
from app.service.staff_registration_service import register_staff_user
from app.types.enums import Role
from app.types.exceptions import DuplicateUsernameError


def test_register_staff_user_creates_a_csr_account(
    sqlite_connection: sqlite3.Connection,
) -> None:
    user = register_staff_user(sqlite_connection, "new_csr_01", "Str0ngPass!2026", Role.CSR)

    assert user.username == "new_csr_01"
    assert user.role is Role.CSR
    assert user.password_hash is not None


def test_register_staff_user_hashes_the_password_not_plaintext(
    sqlite_connection: sqlite3.Connection,
) -> None:
    user = register_staff_user(sqlite_connection, "new_admin_01", "Str0ngPass!2026", Role.ADMIN)

    assert user.password_hash != "Str0ngPass!2026"
    assert verify_password("Str0ngPass!2026", user.password_hash or "") is True


def test_registered_staff_user_is_persisted_and_findable(
    sqlite_connection: sqlite3.Connection,
) -> None:
    register_staff_user(sqlite_connection, "new_dealer_01", "Str0ngPass!2026", Role.DEALER)

    found = get_user_by_username(sqlite_connection, "new_dealer_01")

    assert found is not None
    assert found.role is Role.DEALER


def test_register_staff_user_rejects_a_duplicate_username(
    sqlite_connection: sqlite3.Connection,
) -> None:
    register_staff_user(sqlite_connection, "dup_user", "Str0ngPass!2026", Role.CSR)

    with pytest.raises(DuplicateUsernameError):
        register_staff_user(sqlite_connection, "dup_user", "AnotherPass!2026", Role.ADMIN)


def test_register_staff_user_rejects_the_seeded_demo_username(
    sqlite_connection: sqlite3.Connection,
) -> None:
    """csr_jane is seeded by schema.sql at startup — registering it
    again must be rejected the same way any other duplicate is."""
    with pytest.raises(DuplicateUsernameError):
        register_staff_user(sqlite_connection, "csr_jane", "Str0ngPass!2026", Role.CSR)


@pytest.mark.parametrize("role", [Role.SUBSCRIBER])
def test_register_staff_user_rejects_the_subscriber_role(
    sqlite_connection: sqlite3.Connection, role: Role
) -> None:
    """Subscribers register through the existing mobile-number flow
    (registration_service.py), not this staff-only endpoint."""
    with pytest.raises(ValueError, match="not a staff role"):
        register_staff_user(sqlite_connection, "some_subscriber", "Str0ngPass!2026", role)
