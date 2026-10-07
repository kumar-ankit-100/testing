"""Integration tests for the admin reporting API endpoint (E7-S3)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config.settings import Settings


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db_path = str(tmp_path / "admin_reports_api_test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    return Settings(_env_file=None, db_path=db_path)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _staff_token(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token: str = response.json()["access_token"]
    return token


def test_admin_dashboard_returns_200_with_all_sections(client: TestClient) -> None:
    """AC-1/AC-2/AC-3: on an empty database, every section is present
    and well-formed (empty, not an error)."""
    token = _staff_token(client, "admin_raj", "AdminDemo!2026Synthetic")

    response = client.get(
        "/api/admin/reports/dashboard", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert "activation_funnel" in body
    assert "plan_mix" in body
    assert "churn" in body
    assert "arpu_trend" in body
    assert body["metadata"]["arpu_trend_is_stubbed"] is True


def test_non_admin_cannot_view_the_dashboard(client: TestClient) -> None:
    """AC-4: a CSR token is rejected, enforced inside reporting_service."""
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.get(
        "/api/admin/reports/dashboard", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_dashboard_without_a_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/admin/reports/dashboard")

    assert response.status_code == 401
