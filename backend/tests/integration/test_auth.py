"""Integration tests for role-based auth and controller-level authorization
(E1-S4).

Tokens are obtained through the real POST /api/auth/login endpoint
(E1-S6) rather than minted directly via create_access_token() — this
suite proves the login endpoint and require_role/require_own_subscriber
actually work together end to end, not just that create_access_token
produces a decodable token in isolation (that unit-level guarantee is
covered separately by test_auth_service.py).

No full business router is needed to exercise require_role/
require_own_subscriber themselves, so this test still builds a small
dummy-route app (as it did before E1-S6), but now mounts the real
auth_router onto it so /api/auth/login is available against a real,
schema-applied, per-test temp database.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import current_principal, require_own_subscriber, require_role
from app.api.error_handlers import register_exception_handlers
from app.api.routers.auth_router import router as auth_router
from app.config.db import create_connection
from app.config.settings import Settings
from app.repository.schema import apply_schema
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.auth import Principal
from app.types.enums import PlanType, Role, SubscriberState
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

SUBSCRIBER_A_ID = "7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f"
SUBSCRIBER_A_MOBILE = "9876541101"
SUBSCRIBER_B_ID = "8a2d3e4b-0c2b-5d4f-9f3a-2b3c4d5e6f70"

CSR_USERNAME = "csr_jane"
CSR_PASSWORD = "CsrDemo!2026Synthetic"
ADMIN_USERNAME = "admin_raj"
ADMIN_PASSWORD = "AdminDemo!2026Synthetic"


def _build_test_app() -> FastAPI:
    """Mounts the real auth router plus dummy protected routes exercising
    deps.py exactly as a real business router would.
    """
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(auth_router)

    @test_app.get("/dummy/subscriber-only")
    def subscriber_only(
        principal: Principal = Depends(require_role(Role.SUBSCRIBER)),
    ) -> dict[str, str]:
        return {"user_id": principal.user_id}

    @test_app.get("/dummy/csr-or-admin-only")
    def csr_or_admin_only(
        principal: Principal = Depends(require_role(Role.CSR, Role.ADMIN)),
    ) -> dict[str, str]:
        return {"user_id": principal.user_id}

    @test_app.get("/dummy/whoami")
    def whoami(principal: Principal = Depends(current_principal)) -> dict[str, str]:
        return {"user_id": principal.user_id}

    @test_app.get("/dummy/subscribers/{subscriber_id}")
    def own_subscriber_data(
        subscriber_id: str, principal: Principal = Depends(require_own_subscriber)
    ) -> dict[str, str]:
        return {"subscriber_id": subscriber_id, "accessed_by": principal.user_id}

    return test_app


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db_path = str(tmp_path / "test_auth.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("JWT_SECRET_KEY", "integration-test-secret-at-least-32-bytes")
    return Settings(_env_file=None, db_path=db_path)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """Seeds subscriber A (so logging in by mobile_number returns a real
    subscriber_id) before handing back a TestClient wrapping the dummy app.
    """
    connection = create_connection(settings.db_path)
    apply_schema(connection)
    now = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=SUBSCRIBER_A_ID,
            mobile_number=SUBSCRIBER_A_MOBILE,
            identity_proof_ref="AADHAAR-XXXX-XXXX-1101",
            created_at=now,
        ),
    )
    create_subscription(
        connection,
        Subscription(
            subscription_id="subn-subscriber-a",
            subscriber_id=SUBSCRIBER_A_ID,
            mobile_number=SUBSCRIBER_A_MOBILE,
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

    with TestClient(_build_test_app()) as test_client:
        yield test_client


def _bearer_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_subscriber_a(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"mobile_number": SUBSCRIBER_A_MOBILE})
    token: str = response.json()["access_token"]
    return token


def _login_staff(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    token: str = response.json()["access_token"]
    return token


def test_unauthenticated_request_receives_401(client: TestClient) -> None:
    """AC-1: every non-health route requires an authenticated principal."""
    response = client.get("/dummy/whoami")

    assert response.status_code == 401
    assert response.json()["error"]["reason_code"] == "UNAUTHENTICATED"


def test_subscriber_calling_csr_only_endpoint_receives_403(client: TestClient) -> None:
    """AC-2: a subscriber-role request to a CSR-only endpoint receives 403."""
    token = _login_subscriber_a(client)

    response = client.get("/dummy/csr-or-admin-only", headers=_bearer_header(token))

    assert response.status_code == 403
    assert response.json()["error"]["reason_code"] == "FORBIDDEN"


def test_subscriber_requesting_another_subscribers_data_receives_403(
    client: TestClient,
) -> None:
    """AC-3 / E1-S6 AC-6: a subscriber requesting another subscriber's
    data (ID mismatch) receives 403 — using a token the real
    /api/auth/login endpoint issued for subscriber A, exercised against
    require_own_subscriber end to end, not a test-minted token.
    """
    token = _login_subscriber_a(client)

    response = client.get(
        f"/dummy/subscribers/{SUBSCRIBER_B_ID}", headers=_bearer_header(token)
    )

    assert response.status_code == 403
    assert response.json()["error"]["reason_code"] == "FORBIDDEN"


def test_subscriber_requesting_own_data_succeeds(client: TestClient) -> None:
    """Positive counterpart to AC-3: matching subscriber_id is not blocked."""
    token = _login_subscriber_a(client)

    response = client.get(
        f"/dummy/subscribers/{SUBSCRIBER_A_ID}", headers=_bearer_header(token)
    )

    assert response.status_code == 200
    assert response.json() == {
        "subscriber_id": SUBSCRIBER_A_ID,
        "accessed_by": SUBSCRIBER_A_MOBILE,
    }


@pytest.mark.parametrize(
    ("username", "password"), [(CSR_USERNAME, CSR_PASSWORD), (ADMIN_USERNAME, ADMIN_PASSWORD)]
)
def test_csr_or_admin_can_access_their_scoped_endpoint_without_403(
    client: TestClient, username: str, password: str
) -> None:
    """AC-4: a CSR or admin principal accesses endpoints scoped to their role without a 403."""
    token = _login_staff(client, username, password)

    response = client.get("/dummy/csr-or-admin-only", headers=_bearer_header(token))

    assert response.status_code == 200
    assert response.json()["user_id"]  # a real seeded user_id was returned


def test_csr_and_admin_are_not_subject_to_subscriber_ownership_checks(
    client: TestClient,
) -> None:
    """Staff roles bypass require_own_subscriber's ID-match check entirely."""
    token = _login_staff(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = client.get(
        f"/dummy/subscribers/{SUBSCRIBER_B_ID}", headers=_bearer_header(token)
    )

    assert response.status_code == 200


def test_malformed_bearer_token_receives_401(client: TestClient) -> None:
    response = client.get("/dummy/whoami", headers=_bearer_header("not-a-real-jwt"))

    assert response.status_code == 401
    assert response.json()["error"]["reason_code"] == "UNAUTHENTICATED"
