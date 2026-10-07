"""Integration tests for the registration and activation API (E2-S4)."""

from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "subscriber_api_test.db"))
    with TestClient(create_app()) as test_client:
        yield test_client


def _login(client: TestClient, mobile_number: str) -> str:
    response = client.post("/api/auth/login", json={"mobile_number": mobile_number})
    assert response.status_code == 200
    token: str = response.json()["access_token"]
    return token


def _register(
    client: TestClient, mobile_number: str, identity_proof_ref: str = "AADHAAR-XXXX-XXXX-1001"
) -> dict[str, object]:
    pre_registration_token = _login(client, mobile_number)
    response = client.post(
        "/api/subscribers/register",
        json={
            "mobile_number": mobile_number,
            "identity_proof_ref": identity_proof_ref,
            "plan_type": "POSTPAID",
        },
        headers={"Authorization": f"Bearer {pre_registration_token}"},
    )
    assert response.status_code == 201
    body: dict[str, object] = response.json()
    return body


def _activate(
    client: TestClient, registered: dict[str, object], dealer_code: str = "DLR-BLR-001"
) -> httpx.Response:
    return client.post(
        f"/api/subscribers/{registered['subscriber_id']}/activate",
        json={"dealer_code": dealer_code},
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )


def test_register_with_valid_input_returns_201_pending_kyc(client: TestClient) -> None:
    """AC-1."""
    body = _register(client, "9876541001")

    assert body["state"] == "PENDING_KYC"
    assert isinstance(body["subscriber_id"], str)
    assert isinstance(body["subscription_id"], str)


def test_register_with_malformed_mobile_number_returns_422(client: TestClient) -> None:
    mobile_number = "12345"
    token = _login(client, mobile_number)

    response = client.post(
        "/api/subscribers/register",
        json={
            "mobile_number": mobile_number,
            "identity_proof_ref": "AADHAAR-XXXX-XXXX-1002",
            "plan_type": "PREPAID",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["reason_code"] == "VALIDATION_ERROR"


def test_register_without_a_token_returns_401(client: TestClient) -> None:
    """A subscriber-role token is required to register at all (AC-1, auth gate)."""
    response = client.post(
        "/api/subscribers/register",
        json={
            "mobile_number": "9876541099",
            "identity_proof_ref": "AADHAAR-XXXX-XXXX-1099",
            "plan_type": "PREPAID",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["reason_code"] == "UNAUTHENTICATED"


def test_register_duplicate_active_mobile_returns_409(client: TestClient) -> None:
    mobile_number = "9876541003"
    first = _register(client, mobile_number)
    _activate(client, first)

    token = _login(client, mobile_number)
    response = client.post(
        "/api/subscribers/register",
        json={
            "mobile_number": mobile_number,
            "identity_proof_ref": "AADHAAR-XXXX-XXXX-1003",
            "plan_type": "PREPAID",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["reason_code"] == "DUPLICATE_ACTIVE_MOBILE"


def test_activate_with_all_flags_passing_returns_200_active(client: TestClient) -> None:
    """AC-2."""
    registered = _register(client, "9876541004")

    response = _activate(client, registered)

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ACTIVE"
    assert body["subscriber_id"] == registered["subscriber_id"]
    assert "activated_at" in body


def test_activate_with_dealer_fail_sentinel_returns_422_with_reason_code(
    client: TestClient,
) -> None:
    """AC-3."""
    registered = _register(client, "9876541005")

    response = _activate(client, registered, dealer_code="DEALER-FAIL")

    assert response.status_code == 422
    assert response.json()["error"]["reason_code"] == "DEALER_INVALID"


def test_activate_with_another_subscribers_token_returns_403(client: TestClient) -> None:
    """NFR-04: a subscriber's token only authorizes activating their own
    subscriber_id, not someone else's (require_own_subscriber, E1-S4)."""
    registered_a = _register(client, "9876541098")
    registered_b = _register(client, "9876541097")

    response = client.post(
        f"/api/subscribers/{registered_b['subscriber_id']}/activate",
        json={"dealer_code": "DLR-BLR-001"},
        headers={"Authorization": f"Bearer {registered_a['access_token']}"},
    )

    assert response.status_code == 403


def test_activate_an_already_active_subscriber_returns_409(client: TestClient) -> None:
    """AC-4."""
    registered = _register(client, "9876541006")
    _activate(client, registered)

    response = _activate(client, registered)

    assert response.status_code == 409
    assert response.json()["error"]["reason_code"] == "ALREADY_ACTIVE"


def test_register_request_body_rejects_an_unknown_plan_type(client: TestClient) -> None:
    """AC-5: requests are validated against typed models, not untyped dicts —
    an invalid enum value is rejected by Pydantic before reaching the service.
    """
    token = _login(client, "9876541007")

    response = client.post(
        "/api/subscribers/register",
        json={
            "mobile_number": "9876541007",
            "identity_proof_ref": "AADHAAR-XXXX-XXXX-1007",
            "plan_type": "NOT-A-REAL-PLAN-TYPE",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
