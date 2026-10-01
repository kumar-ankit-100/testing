"""Integration tests for POST /api/auth/login (E1-S6)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config.settings import Settings
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.enums import PlanType, SubscriberState
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_JWT_SECRET = "integration-test-secret-at-least-32-bytes-long"


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db_path = str(tmp_path / "auth_login_test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("JWT_SECRET_KEY", _JWT_SECRET)
    return Settings(_env_file=None, db_path=db_path, jwt_secret_key=_JWT_SECRET)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _decode(token: str) -> dict[str, object]:
    return jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])


def test_staff_login_with_valid_csr_credentials_returns_token_with_role_and_subject(
    client: TestClient,
) -> None:
    """AC-1."""
    response = client.post(
        "/api/auth/login", json={"username": "csr_jane", "password": "CsrDemo!2026Synthetic"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "csr"
    assert body["subscriber_id"] is None
    assert body["expires_in"] > 0

    claims = _decode(body["access_token"])
    assert claims["role"] == "csr"
    assert isinstance(claims["sub"], str) and claims["sub"]


def test_staff_login_with_valid_admin_credentials_returns_200(client: TestClient) -> None:
    """AC-1."""
    response = client.post(
        "/api/auth/login", json={"username": "admin_raj", "password": "AdminDemo!2026Synthetic"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_subscriber_login_with_no_prior_registration_returns_pre_registration_token(
    client: TestClient,
) -> None:
    """AC-2."""
    response = client.post("/api/auth/login", json={"mobile_number": "9876540001"})

    assert response.status_code == 200
    body = response.json()
    assert body["subscriber_id"] is None
    assert body["role"] == "subscriber"
    claims = _decode(body["access_token"])
    assert claims["role"] == "subscriber"
    assert claims["subscriber_id"] is None


def test_subscriber_login_after_registration_returns_populated_subscriber_id(
    client: TestClient, settings: Settings
) -> None:
    """A registered mobile number's login reflects its real subscriber_id —
    the positive counterpart to AC-2's null case."""
    from app.config.db import create_connection

    connection = create_connection(settings.db_path)
    now = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id="real-subscriber-0001",
            mobile_number="9876540002",
            identity_proof_ref="AADHAAR-XXXX-XXXX-0002",
            created_at=now,
        ),
    )
    create_subscription(
        connection,
        Subscription(
            subscription_id="real-subscription-0001",
            subscriber_id="real-subscriber-0001",
            mobile_number="9876540002",
            plan_type=PlanType.PREPAID,
            state=SubscriberState.PENDING_KYC,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=now,
            activated_at=None,
            updated_at=now,
        ),
    )
    connection.close()

    response = client.post("/api/auth/login", json={"mobile_number": "9876540002"})

    assert response.status_code == 200
    assert response.json()["subscriber_id"] == "real-subscriber-0001"


def test_staff_login_with_wrong_password_returns_401_generic_reason_code(
    client: TestClient,
) -> None:
    """AC-3."""
    response = client.post(
        "/api/auth/login", json={"username": "csr_jane", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["reason_code"] == "UNAUTHENTICATED"


def test_staff_login_with_unknown_username_returns_the_same_401_response_shape(
    client: TestClient,
) -> None:
    """AC-3: identical error+message for unknown-user vs. wrong-password —
    no user-enumeration signal.
    """
    unknown_user_response = client.post(
        "/api/auth/login", json={"username": "no_such_user", "password": "anything"}
    )
    wrong_password_response = client.post(
        "/api/auth/login", json={"username": "csr_jane", "password": "wrong-password"}
    )

    assert unknown_user_response.status_code == wrong_password_response.status_code == 401
    assert unknown_user_response.json() == wrong_password_response.json()


def test_login_attempt_never_logs_the_raw_password(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-5."""
    client.post(
        "/api/auth/login", json={"username": "csr_jane", "password": "CsrDemo!2026Synthetic"}
    )

    captured = capsys.readouterr().out
    assert "CsrDemo!2026Synthetic" not in captured


def test_login_attempt_masks_the_mobile_number_in_logs(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-5."""
    client.post("/api/auth/login", json={"mobile_number": "9876540003"})

    captured = capsys.readouterr().out
    assert "9876540003" not in captured
    assert "******0003" in captured


