"""Unit tests for the User and Principal domain types (E1-S4)."""

from datetime import UTC, datetime

from app.types.auth import Principal, User
from app.types.enums import Role


def test_user_holds_typed_role_and_nullable_staff_fields() -> None:
    user = User(
        user_id="6e1f2a3b-0001-4a11-9b22-c33d44e55f66",
        role=Role.CSR,
        username="csr.agent42",
        password_hash="$2b$12$abcdefghijklmnopqrstuv",
        mobile_number=None,
        subscriber_id=None,
        created_at=datetime(2026, 1, 10, 8, 0, tzinfo=UTC),
    )
    assert user.role is Role.CSR
    assert user.username == "csr.agent42"
    assert user.mobile_number is None
    assert user.subscriber_id is None


def test_user_holds_subscriber_context_for_subscriber_role() -> None:
    user = User(
        user_id="6e1f2a3b-0002-4a11-9b22-c33d44e55f66",
        role=Role.SUBSCRIBER,
        username=None,
        password_hash=None,
        mobile_number="9876547890",
        subscriber_id="7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f",
        created_at=datetime(2026, 1, 12, 9, 15, tzinfo=UTC),
    )
    assert user.role is Role.SUBSCRIBER
    assert user.subscriber_id == "7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f"


def test_principal_holds_typed_role_and_nullable_subscriber_id() -> None:
    principal = Principal(
        user_id="6e1f2a3b-0003-4a11-9b22-c33d44e55f66", role=Role.ADMIN, subscriber_id=None
    )
    assert principal.role is Role.ADMIN
    assert principal.subscriber_id is None


def test_principal_carries_subscriber_id_for_ownership_checks() -> None:
    principal = Principal(
        user_id="6e1f2a3b-0004-4a11-9b22-c33d44e55f66",
        role=Role.SUBSCRIBER,
        subscriber_id="7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f",
    )
    assert principal.subscriber_id == "7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f"
