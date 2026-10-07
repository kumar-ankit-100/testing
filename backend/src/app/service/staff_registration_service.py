"""Dynamic staff self-registration for CSR/admin/dealer accounts.

Service layer — imports Types, Config, Repository only.

Before this, the only staff accounts were the 3 users seeded by
schema.sql; this lets a new CSR/admin/dealer create their own account
instead of requiring a hand-edit to the seed data.
"""

import sqlite3
import uuid
from datetime import UTC, datetime

from app.repository.user_repository import create_user, get_user_by_username
from app.service.auth_service import hash_password
from app.types.auth import User
from app.types.enums import Role
from app.types.exceptions import DuplicateUsernameError

_STAFF_ROLES = frozenset({Role.CSR, Role.ADMIN, Role.DEALER})


def register_staff_user(
    connection: sqlite3.Connection, username: str, password: str, role: Role
) -> User:
    """Create a new staff account, hashing password before persisting.

    Raises ValueError if role is not a staff role (subscribers register
    via the mobile-number flow in registration_service.py instead).
    Raises DuplicateUsernameError if username is already taken, whether
    by a previously self-registered user or a seeded demo account.
    """
    if role not in _STAFF_ROLES:
        raise ValueError(f"{role.value!r} is not a staff role")

    if get_user_by_username(connection, username) is not None:
        raise DuplicateUsernameError(username)

    user = User(
        user_id=str(uuid.uuid4()),
        role=role,
        username=username,
        password_hash=hash_password(password),
        mobile_number=None,
        subscriber_id=None,
        created_at=datetime.now(UTC),
    )
    create_user(connection, user)
    return user
