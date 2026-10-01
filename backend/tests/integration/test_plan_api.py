"""Integration tests for the plan catalog admin API (E3-S3).

Bearer tokens are obtained through the real POST /api/auth/login
endpoint (E1-S6), using the seeded demo staff credentials, rather than
minted directly via create_access_token() — this suite proves the admin
router's auth actually works against a real login flow.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config.settings import Settings

_JWT_SECRET = "integration-test-secret-at-least-32-bytes-long"
_ADMIN_USERNAME = "admin_raj"
_ADMIN_PASSWORD = "AdminDemo!2026Synthetic"
_CSR_USERNAME = "csr_jane"
_CSR_PASSWORD = "CsrDemo!2026Synthetic"


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "plan_api_test.db"))
    monkeypatch.setenv("JWT_SECRET_KEY", _JWT_SECRET)
    return Settings(_env_file=None, db_path=str(tmp_path / "plan_api_test.db"))


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    token: str = response.json()["access_token"]
    return token


def _admin_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client, _ADMIN_USERNAME, _ADMIN_PASSWORD)}"}


def _csr_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client, _CSR_USERNAME, _CSR_PASSWORD)}"}


def _create_draft(client: TestClient, plan_id: str = "PLAN-5G") -> dict[str, object]:
    response = client.post(
        "/api/admin/plans",
        json={
            "plan_id": plan_id,
            "plan_name": "Unlimited 5G Postpaid",
            "plan_type": "POSTPAID",
            "price": "799.00",
            "terms": {"data_gb": 100},
        },
        headers=_admin_header(client),
    )
    assert response.status_code == 201
    body: dict[str, object] = response.json()
    return body


def test_create_plan_version_returns_201_with_draft(client: TestClient) -> None:
    """AC-1."""
    body = _create_draft(client)

    assert body["plan_id"] == "PLAN-5G"
    assert body["version_number"] == 1
    assert body["published"] is False
    assert isinstance(body["plan_version_id"], str)


def test_publish_plan_version_returns_200_with_published_true(client: TestClient) -> None:
    """AC-2."""
    draft = _create_draft(client)

    response = client.post(
        f"/api/admin/plans/{draft['plan_version_id']}/publish", headers=_admin_header(client)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["published"] is True
    assert body["plan_version_id"] == draft["plan_version_id"]
    assert "published_at" in body


def test_put_on_an_already_published_version_returns_409_with_immutability_message(
    client: TestClient,
) -> None:
    """AC-3."""
    draft = _create_draft(client)
    client.post(
        f"/api/admin/plans/{draft['plan_version_id']}/publish", headers=_admin_header(client)
    )

    response = client.put(
        f"/api/admin/plans/{draft['plan_version_id']}",
        json={"price": "1.00"},
        headers=_admin_header(client),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["reason_code"] == "PLAN_VERSION_IMMUTABLE"
    assert "modif" in body["error"]["message"].lower() or "immutable" in str(body).lower()


def test_put_on_a_draft_version_updates_price(client: TestClient) -> None:
    draft = _create_draft(client)

    response = client.put(
        f"/api/admin/plans/{draft['plan_version_id']}",
        json={"price": "849.00"},
        headers=_admin_header(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == "849.00"
    assert body["terms"] == {"data_gb": 100}  # unset field keeps its current value


def test_get_plan_list_returns_full_version_history_including_superseded(
    client: TestClient,
) -> None:
    """AC-4."""
    v1 = _create_draft(client, plan_id="PLAN-5G")
    client.post(f"/api/admin/plans/{v1['plan_version_id']}/publish", headers=_admin_header(client))
    v2 = _create_draft(client, plan_id="PLAN-5G")  # a second version, superseding v1

    response = client.get("/api/admin/plans", headers=_admin_header(client))

    assert response.status_code == 200
    plans = response.json()["plans"]
    version_numbers = {p["plan_version_id"]: p["version_number"] for p in plans}
    assert version_numbers[v1["plan_version_id"]] == 1
    assert version_numbers[v2["plan_version_id"]] == 2
    published_flags = {p["plan_version_id"]: p["published"] for p in plans}
    assert published_flags[v1["plan_version_id"]] is True
    assert published_flags[v2["plan_version_id"]] is False


@pytest.mark.parametrize(
    ("method", "path_suffix", "json_body"),
    [
        ("post", "", {"plan_id": "X", "plan_name": "X", "plan_type": "PREPAID",
                       "price": "1.00", "terms": {}}),
        ("get", "", None),
    ],
)
def test_non_admin_receives_403_for_create_and_list(
    client: TestClient, method: str, path_suffix: str, json_body: dict[str, object] | None
) -> None:
    """AC-5 (create, list)."""
    csr_header = _csr_header(client)

    response = client.request(
        method, f"/api/admin/plans{path_suffix}", json=json_body, headers=csr_header
    )

    assert response.status_code == 403


def test_non_admin_receives_403_for_publish(client: TestClient) -> None:
    """AC-5 (publish)."""
    draft = _create_draft(client)
    csr_header = _csr_header(client)

    response = client.post(
        f"/api/admin/plans/{draft['plan_version_id']}/publish", headers=csr_header
    )

    assert response.status_code == 403


def test_non_admin_receives_403_for_update(client: TestClient) -> None:
    """AC-5 (update)."""
    draft = _create_draft(client)
    csr_header = _csr_header(client)

    response = client.put(
        f"/api/admin/plans/{draft['plan_version_id']}",
        json={"price": "1.00"},
        headers=csr_header,
    )

    assert response.status_code == 403


def test_price_fields_are_serialized_as_strings_not_json_numbers(client: TestClient) -> None:
    """Guards against Pydantic/FastAPI's default Decimal-to-JSON-number
    encoding, which would violate api-contracts.md's string-money contract.
    """
    draft = _create_draft(client)

    response = client.put(
        f"/api/admin/plans/{draft['plan_version_id']}",
        json={"price": "849.00"},
        headers=_admin_header(client),
    )

    raw_text = response.text
    assert '"price":"849.00"' in raw_text.replace(" ", "")


def test_publish_an_unknown_plan_version_id_returns_404(client: TestClient) -> None:
    response = client.post("/api/admin/plans/does-not-exist/publish", headers=_admin_header(client))

    assert response.status_code == 404
    assert response.json()["error"]["reason_code"] == "NOT_FOUND"


def test_update_an_unknown_plan_version_id_returns_404(client: TestClient) -> None:
    response = client.put(
        "/api/admin/plans/does-not-exist", json={"price": "1.00"}, headers=_admin_header(client)
    )

    assert response.status_code == 404
    assert response.json()["error"]["reason_code"] == "NOT_FOUND"
