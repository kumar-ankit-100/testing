"""Integration tests for dynamic staff self-registration via the API
(POST /api/auth/register-staff), closing the "only seeded demo users
exist" gap."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "auth_api_test.db"))
    with TestClient(create_app()) as test_client:
        yield test_client


def test_register_staff_then_login_succeeds(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register-staff",
        json={"username": "fresh_csr_01", "password": "Str0ngPass!2026", "role": "csr"},
    )

    assert register_response.status_code == 201
    body = register_response.json()
    assert body["username"] == "fresh_csr_01"
    assert body["role"] == "csr"

    login_response = client.post(
        "/api/auth/login",
        json={"username": "fresh_csr_01", "password": "Str0ngPass!2026"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["role"] == "csr"


def test_register_staff_with_duplicate_username_returns_409(client: TestClient) -> None:
    client.post(
        "/api/auth/register-staff",
        json={"username": "dup_api_user", "password": "Str0ngPass!2026", "role": "admin"},
    )

    response = client.post(
        "/api/auth/register-staff",
        json={"username": "dup_api_user", "password": "AnotherPass!2026", "role": "dealer"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["reason_code"] == "DUPLICATE_USERNAME"


def test_register_staff_with_seeded_demo_username_returns_409(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register-staff",
        json={"username": "csr_jane", "password": "Str0ngPass!2026", "role": "csr"},
    )

    assert response.status_code == 409


def test_register_staff_with_subscriber_role_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register-staff",
        json={"username": "should_fail", "password": "Str0ngPass!2026", "role": "subscriber"},
    )

    assert response.status_code == 422


def test_register_staff_with_unknown_role_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register-staff",
        json={"username": "should_fail_2", "password": "Str0ngPass!2026", "role": "superuser"},
    )

    assert response.status_code == 422


def test_register_staff_with_short_password_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register-staff",
        json={"username": "short_pw_user", "password": "short", "role": "csr"},
    )

    assert response.status_code == 422
