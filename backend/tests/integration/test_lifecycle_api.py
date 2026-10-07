"""Integration tests for the suspend/resume + port-out API endpoints (E5-S4)."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config.db import create_connection
from app.config.settings import Settings
from app.repository.port_out_repository import create_port_out_event
from app.repository.schema import apply_schema
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.enums import PlanType, SubscriberState
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db_path = str(tmp_path / "lifecycle_api_test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    return Settings(_env_file=None, db_path=db_path)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _seed_subscription(
    settings: Settings, subscriber_id: str, mobile_number: str, state: SubscriberState
) -> str:
    connection = create_connection(settings.db_path)
    apply_schema(connection)
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-5501",
            created_at=_REGISTERED_AT,
        ),
    )
    subscription_id = f"subn-{subscriber_id}"
    create_subscription(
        connection,
        Subscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            plan_type=PlanType.POSTPAID,
            state=state,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=_REGISTERED_AT,
            updated_at=_REGISTERED_AT,
        ),
    )
    connection.close()
    return subscription_id


def _subscriber_token(client: TestClient, mobile_number: str) -> str:
    response = client.post("/api/auth/login", json={"mobile_number": mobile_number})
    token: str = response.json()["access_token"]
    return token


def _staff_token(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token: str = response.json()["access_token"]
    return token


def test_suspend_an_active_subscription_returns_200_suspended(
    client: TestClient, settings: Settings
) -> None:
    """AC-1."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0001", "9876545501", SubscriberState.ACTIVE
    )
    token = _subscriber_token(client, "9876545501")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/suspend",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "SUSPENDED"


def test_resume_a_suspended_subscription_returns_200_active(
    client: TestClient, settings: Settings
) -> None:
    """AC-2."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0002", "9876545502", SubscriberState.SUSPENDED
    )
    token = _subscriber_token(client, "9876545502")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/resume",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "ACTIVE"


def test_port_out_request_returns_200_with_cooling_period_end_date(
    client: TestClient, settings: Settings
) -> None:
    """AC-3."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0003", "9876545503", SubscriberState.ACTIVE
    )
    token = _subscriber_token(client, "9876545503")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/port-out/request",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert "cooling_period_end_at" in body


def test_cancel_port_out_within_window_returns_200_active(
    client: TestClient, settings: Settings
) -> None:
    """AC-4."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0004", "9876545504", SubscriberState.ACTIVE
    )
    token = _subscriber_token(client, "9876545504")
    client.post(
        f"/api/subscriptions/{subscription_id}/port-out/request",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/subscriptions/{subscription_id}/port-out/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "ACTIVE"


def test_finalize_port_out_before_window_elapses_returns_422(
    client: TestClient, settings: Settings
) -> None:
    """AC-5."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0005", "9876545505", SubscriberState.ACTIVE
    )
    token = _subscriber_token(client, "9876545505")
    client.post(
        f"/api/subscriptions/{subscription_id}/port-out/request",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/subscriptions/{subscription_id}/port-out/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["reason_code"] == "COOLING_PERIOD_NOT_ELAPSED"


def test_csr_can_terminate_an_active_subscription(
    client: TestClient, settings: Settings
) -> None:
    """E6-S6 AC-1."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0006", "9876545506", SubscriberState.ACTIVE
    )
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/terminate",
        json={"reason_code": "FRAUD_SUSPECTED"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "TERMINATED"


def test_admin_can_terminate_a_suspended_subscription(
    client: TestClient, settings: Settings
) -> None:
    """E6-S6: ADMIN is permitted, same as CSR."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0007", "9876545507", SubscriberState.SUSPENDED
    )
    token = _staff_token(client, "admin_raj", "AdminDemo!2026Synthetic")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/terminate",
        json={"reason_code": "COURT_ORDER"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "TERMINATED"


def test_terminate_without_a_reason_code_returns_422(
    client: TestClient, settings: Settings
) -> None:
    """E6-S6 AC-3: rejected by Pydantic before termination_service is ever called."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0008", "9876545508", SubscriberState.ACTIVE
    )
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/terminate",
        json={"reason_code": ""},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_subscriber_cannot_terminate_their_own_subscription(
    client: TestClient, settings: Settings
) -> None:
    """E6-S6 AC-4: termination is CSR/admin-only — a subscriber's own
    token is rejected even against their own subscription_id."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0009", "9876545509", SubscriberState.ACTIVE
    )
    token = _subscriber_token(client, "9876545509")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/terminate",
        json={"reason_code": "SUBSCRIBER_REQUEST"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_staff_can_suspend_without_an_ownership_check(
    client: TestClient, settings: Settings
) -> None:
    """A CSR token bypasses the subscriber-ownership check entirely
    (_require_own_subscription's early return for non-subscriber roles)."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0010", "9876545510", SubscriberState.ACTIVE
    )
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/suspend",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "SUSPENDED"


def test_subscriber_cannot_suspend_another_subscribers_subscription(
    client: TestClient, settings: Settings
) -> None:
    """A subscriber token is rejected against a subscription_id that
    isn't theirs (_require_own_subscription's mismatch branch)."""
    subscription_id = _seed_subscription(
        settings, "lc-api-0011", "9876545511", SubscriberState.ACTIVE
    )
    _seed_subscription(settings, "lc-api-0012", "9876545512", SubscriberState.ACTIVE)
    token = _subscriber_token(client, "9876545512")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/suspend",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_finalize_port_out_after_window_elapsed_returns_200_ported_out(
    client: TestClient, settings: Settings
) -> None:
    """E5-S3 AC-5 success path: seeds a port-out event requested 8 days
    ago (the API itself always uses "now" for requested_at, so a past
    event has to be seeded directly to test the elapsed-window path)."""
    subscription_id = "subn-lc-api-0013"
    requested_at = datetime.now(UTC) - timedelta(days=8)

    connection = create_connection(settings.db_path)
    apply_schema(connection)
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id="lc-api-0013",
            mobile_number="9876545513",
            identity_proof_ref="AADHAAR-XXXX-XXXX-5513",
            created_at=_REGISTERED_AT,
        ),
    )
    create_subscription(
        connection,
        Subscription(
            subscription_id=subscription_id,
            subscriber_id="lc-api-0013",
            mobile_number="9876545513",
            plan_type=PlanType.POSTPAID,
            state=SubscriberState.PORT_OUT_REQUESTED,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=_REGISTERED_AT,
            updated_at=_REGISTERED_AT,
        ),
    )
    create_port_out_event(connection, subscription_id, requested_at)
    connection.close()

    token = _subscriber_token(client, "9876545513")
    response = client.post(
        f"/api/subscriptions/{subscription_id}/port-out/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "FINALIZED"


def test_terminate_an_unknown_subscription_returns_404(
    client: TestClient, settings: Settings
) -> None:
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.post(
        "/api/subscriptions/does-not-exist/terminate",
        json={"reason_code": "FRAUD_SUSPECTED"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
