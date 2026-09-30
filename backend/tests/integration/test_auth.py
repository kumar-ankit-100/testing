"""Integration tests for role-based auth and controller-level authorization
(E1-S4).

No business router exists yet in this group, so this test builds a small
standalone FastAPI app wired with the same deps.py dependencies and
error_handlers.py mapping that every future business router will use, and
exercises it with a real TestClient — matching AC-5's "running test
client" requirement.
"""

from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import current_principal, require_own_subscriber, require_role
from app.api.error_handlers import register_exception_handlers
from app.config.settings import Settings, get_settings
from app.service.auth_service import create_access_token
from app.types.auth import Principal
from app.types.enums import Role

SUBSCRIBER_A_ID = "7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f"
SUBSCRIBER_B_ID = "8a2d3e4b-0c2b-5d4f-9f3a-2b3c4d5e6f70"


def _build_test_app() -> FastAPI:
    """A minimal app exercising deps.py exactly as a real router would."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

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
def settings() -> Settings:
    return Settings(_env_file=None, jwt_secret_key="integration-test-secret-at-least-32-bytes")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    test_app = _build_test_app()
    test_app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(test_app) as test_client:
        yield test_client


def _bearer_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_request_receives_401(client: TestClient) -> None:
    """AC-1: every non-health route requires an authenticated principal."""
    response = client.get("/dummy/whoami")

    assert response.status_code == 401
    assert response.json()["error"]["reason_code"] == "UNAUTHENTICATED"


def test_subscriber_calling_csr_only_endpoint_receives_403(
    client: TestClient, settings: Settings
) -> None:
    """AC-2: a subscriber-role request to a CSR-only endpoint receives 403."""
    subscriber_principal = Principal(
        user_id="user-subscriber-1", role=Role.SUBSCRIBER, subscriber_id=SUBSCRIBER_A_ID
    )
    token = create_access_token(subscriber_principal, settings)

    response = client.get("/dummy/csr-or-admin-only", headers=_bearer_header(token))

    assert response.status_code == 403
    assert response.json()["error"]["reason_code"] == "FORBIDDEN"


def test_subscriber_requesting_another_subscribers_data_receives_403(
    client: TestClient, settings: Settings
) -> None:
    """AC-3: a subscriber requesting another subscriber's data (ID mismatch) receives 403."""
    subscriber_principal = Principal(
        user_id="user-subscriber-2", role=Role.SUBSCRIBER, subscriber_id=SUBSCRIBER_A_ID
    )
    token = create_access_token(subscriber_principal, settings)

    response = client.get(
        f"/dummy/subscribers/{SUBSCRIBER_B_ID}", headers=_bearer_header(token)
    )

    assert response.status_code == 403
    assert response.json()["error"]["reason_code"] == "FORBIDDEN"


def test_subscriber_requesting_own_data_succeeds(
    client: TestClient, settings: Settings
) -> None:
    """Positive counterpart to AC-3: matching subscriber_id is not blocked."""
    subscriber_principal = Principal(
        user_id="user-subscriber-3", role=Role.SUBSCRIBER, subscriber_id=SUBSCRIBER_A_ID
    )
    token = create_access_token(subscriber_principal, settings)

    response = client.get(
        f"/dummy/subscribers/{SUBSCRIBER_A_ID}", headers=_bearer_header(token)
    )

    assert response.status_code == 200
    assert response.json() == {
        "subscriber_id": SUBSCRIBER_A_ID,
        "accessed_by": "user-subscriber-3",
    }


@pytest.mark.parametrize("role", [Role.CSR, Role.ADMIN])
def test_csr_or_admin_can_access_their_scoped_endpoint_without_403(
    client: TestClient, settings: Settings, role: Role
) -> None:
    """AC-4: a CSR or admin principal accesses endpoints scoped to their role without a 403."""
    staff_principal = Principal(user_id=f"user-{role.value}", role=role, subscriber_id=None)
    token = create_access_token(staff_principal, settings)

    response = client.get("/dummy/csr-or-admin-only", headers=_bearer_header(token))

    assert response.status_code == 200
    assert response.json() == {"user_id": f"user-{role.value}"}


def test_csr_and_admin_are_not_subject_to_subscriber_ownership_checks(
    client: TestClient, settings: Settings
) -> None:
    """Staff roles bypass require_own_subscriber's ID-match check entirely."""
    admin_principal = Principal(user_id="user-admin-1", role=Role.ADMIN, subscriber_id=None)
    token = create_access_token(admin_principal, settings)

    response = client.get(
        f"/dummy/subscribers/{SUBSCRIBER_B_ID}", headers=_bearer_header(token)
    )

    assert response.status_code == 200


def test_malformed_bearer_token_receives_401(client: TestClient) -> None:
    response = client.get("/dummy/whoami", headers=_bearer_header("not-a-real-jwt"))

    assert response.status_code == 401
    assert response.json()["error"]["reason_code"] == "UNAUTHENTICATED"
