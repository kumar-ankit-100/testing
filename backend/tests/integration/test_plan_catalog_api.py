"""Integration tests for GET /api/plans — the public (any authenticated
role) plan catalog listing subscribers use to browse plans at
registration/plan-change time, distinct from admin-only /api/admin/plans.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config.settings import Settings

_ADMIN_USERNAME = "admin_raj"
_ADMIN_PASSWORD = "AdminDemo!2026Synthetic"


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "plan_catalog_api_test.db"))
    monkeypatch.setenv("JWT_SECRET_KEY", "integration-test-secret-at-least-32-bytes-long")
    return Settings(_env_file=None, db_path=str(tmp_path / "plan_catalog_api_test.db"))


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _admin_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"username": _ADMIN_USERNAME, "password": _ADMIN_PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _subscriber_header(client: TestClient, mobile_number: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"mobile_number": mobile_number})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _publish_plan(client: TestClient, plan_id: str, price: str) -> None:
    create_response = client.post(
        "/api/admin/plans",
        json={
            "plan_id": plan_id,
            "plan_name": "Unlimited 5G Postpaid",
            "plan_type": "POSTPAID",
            "price": price,
            "terms": {"data_gb": 100},
        },
        headers=_admin_header(client),
    )
    plan_version_id = create_response.json()["plan_version_id"]
    client.post(f"/api/admin/plans/{plan_version_id}/publish", headers=_admin_header(client))


def test_subscriber_can_list_published_plans(client: TestClient) -> None:
    _publish_plan(client, "PLAN-5G", "799.00")

    response = client.get("/api/plans", headers=_subscriber_header(client, "9876500001"))

    assert response.status_code == 200
    plans = response.json()["plans"]
    assert len(plans) == 1
    assert plans[0]["plan_id"] == "PLAN-5G"
    assert plans[0]["published"] is True


def test_published_plan_list_excludes_unpublished_drafts(client: TestClient) -> None:
    client.post(
        "/api/admin/plans",
        json={
            "plan_id": "PLAN-DRAFT",
            "plan_name": "Draft Only",
            "plan_type": "PREPAID",
            "price": "99.00",
            "terms": {},
        },
        headers=_admin_header(client),
    )

    response = client.get("/api/plans", headers=_subscriber_header(client, "9876500002"))

    assert response.status_code == 200
    assert response.json()["plans"] == []


def test_unauthenticated_request_returns_401(client: TestClient) -> None:
    response = client.get("/api/plans")

    assert response.status_code == 401
