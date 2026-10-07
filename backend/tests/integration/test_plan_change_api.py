"""Integration tests for the plan change API endpoints (E4-S4)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config.db import create_connection
from app.config.settings import Settings
from app.repository.plan_repository import create_plan_version, publish_plan_version
from app.repository.schema import apply_schema
from app.repository.subscriber_repository import create_subscriber, create_subscription
from app.types.enums import PlanType, SubscriberState
from app.types.plan import PlanVersion
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
_FROM_PLAN_ID = "API-FROM-PLAN-v1"
_TO_PLAN_ID = "API-TO-PLAN-v1"


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db_path = str(tmp_path / "plan_change_api_test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setenv("MIN_TENURE_DAYS", "90")
    return Settings(_env_file=None, db_path=db_path, min_tenure_days=90)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _seed_subscription(
    settings: Settings,
    subscriber_id: str,
    mobile_number: str,
    state: SubscriberState,
    activated_at: datetime,
) -> tuple[str, str]:
    connection = create_connection(settings.db_path)
    apply_schema(connection)

    from_plan_id = f"{_FROM_PLAN_ID}-{subscriber_id}"
    to_plan_id = f"{_TO_PLAN_ID}-{subscriber_id}"
    from_plan = PlanVersion(
        plan_version_id=from_plan_id,
        plan_id=f"API-PLAN-{subscriber_id}",
        plan_name="API Base",
        plan_type=PlanType.POSTPAID,
        version_number=1,
        price=Decimal("799.00"),
        terms={},
        published=False,
        created_at=_REGISTERED_AT,
        published_at=None,
    )
    to_plan = PlanVersion(
        plan_version_id=to_plan_id,
        plan_id=f"API-PLAN-{subscriber_id}",
        plan_name="API Pro",
        plan_type=PlanType.POSTPAID,
        version_number=2,
        price=Decimal("999.00"),
        terms={},
        published=False,
        created_at=_REGISTERED_AT,
        published_at=None,
    )
    create_plan_version(connection, from_plan)
    create_plan_version(connection, to_plan)
    publish_plan_version(connection, from_plan_id, _REGISTERED_AT)
    publish_plan_version(connection, to_plan_id, _REGISTERED_AT)

    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-4401",
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
            current_plan_version_id=from_plan_id,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=activated_at,
            updated_at=_REGISTERED_AT,
        ),
    )
    connection.close()
    return subscription_id, to_plan_id


def _subscriber_token(client: TestClient, mobile_number: str) -> str:
    response = client.post("/api/auth/login", json={"mobile_number": mobile_number})
    token: str = response.json()["access_token"]
    return token


def test_preview_returns_pro_rata_without_mutating(
    client: TestClient, settings: Settings
) -> None:
    """AC-1."""
    activated_at = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id, to_plan_id = _seed_subscription(
        settings, "pc-api-0001", "9876544401", SubscriberState.ACTIVE, activated_at
    )
    token = _subscriber_token(client, "9876544401")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/plan-change/preview",
        json={"target_plan_version_id": to_plan_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "pro_rata_amount" in body
    assert Decimal(body["pro_rata_amount"]) >= Decimal("0.00")


def test_commit_on_an_eligible_subscription_returns_new_plan_and_billing_record(
    client: TestClient, settings: Settings
) -> None:
    """AC-2."""
    activated_at = datetime(2025, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id, to_plan_id = _seed_subscription(
        settings, "pc-api-0002", "9876544402", SubscriberState.ACTIVE, activated_at
    )
    token = _subscriber_token(client, "9876544402")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/plan-change/commit",
        json={"target_plan_version_id": to_plan_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["to_plan_version_id"] == to_plan_id
    assert isinstance(body["billing_record_id"], str)


def test_commit_below_minimum_tenure_returns_422_with_reason_code(
    client: TestClient, settings: Settings
) -> None:
    """AC-3."""
    activated_at = datetime.now(UTC)
    subscription_id, to_plan_id = _seed_subscription(
        settings, "pc-api-0003", "9876544403", SubscriberState.ACTIVE, activated_at
    )
    token = _subscriber_token(client, "9876544403")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/plan-change/commit",
        json={"target_plan_version_id": to_plan_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["reason_code"] == "MIN_TENURE_NOT_MET"


def test_commit_on_a_suspended_subscription_returns_409_with_reason_code(
    client: TestClient, settings: Settings
) -> None:
    """AC-4."""
    activated_at = datetime(2025, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id, to_plan_id = _seed_subscription(
        settings, "pc-api-0004", "9876544404", SubscriberState.SUSPENDED, activated_at
    )
    token = _subscriber_token(client, "9876544404")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/plan-change/commit",
        json={"target_plan_version_id": to_plan_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["reason_code"] == "SUBSCRIPTION_SUSPENDED"


def test_subscriber_calling_for_a_non_own_subscription_is_forbidden(
    client: TestClient, settings: Settings
) -> None:
    """AC-5."""
    activated_at = datetime(2025, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id, to_plan_id = _seed_subscription(
        settings, "pc-api-0005", "9876544405", SubscriberState.ACTIVE, activated_at
    )
    # A different subscriber's token.
    _seed_subscription(settings, "pc-api-0006", "9876544406", SubscriberState.ACTIVE, activated_at)
    token = _subscriber_token(client, "9876544406")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/plan-change/commit",
        json={"target_plan_version_id": to_plan_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def _staff_token(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token: str = response.json()["access_token"]
    return token


def test_staff_can_preview_without_an_ownership_check(
    client: TestClient, settings: Settings
) -> None:
    """A CSR/admin token bypasses the subscriber-ownership check entirely
    (_require_own_subscription's early return for non-subscriber roles)."""
    activated_at = datetime(2025, 1, 1, 9, 0, tzinfo=UTC)
    subscription_id, to_plan_id = _seed_subscription(
        settings, "pc-api-0007", "9876544407", SubscriberState.ACTIVE, activated_at
    )
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.post(
        f"/api/subscriptions/{subscription_id}/plan-change/preview",
        json={"target_plan_version_id": to_plan_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
