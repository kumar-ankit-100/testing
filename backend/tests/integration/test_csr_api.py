"""Integration tests for the CSR override API endpoints (E6-S3)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config.db import create_connection
from app.config.settings import Settings
from app.repository.plan_repository import create_plan_version, publish_plan_version
from app.repository.schema import apply_schema
from app.repository.subscriber_repository import (
    create_subscriber,
    create_subscription,
    update_subscription_plan,
    update_subscription_state,
)
from app.types.enums import PlanType, SubscriberState
from app.types.plan import PlanVersion
from app.types.subscriber import Subscriber
from app.types.subscription import Subscription

_REGISTERED_AT = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db_path = str(tmp_path / "csr_api_test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    return Settings(_env_file=None, db_path=db_path)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _seed_pending_subscriber(settings: Settings, subscriber_id: str, mobile_number: str) -> None:
    connection = create_connection(settings.db_path)
    apply_schema(connection)
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-6601",
            created_at=_REGISTERED_AT,
        ),
    )
    create_subscription(
        connection,
        Subscription(
            subscription_id=f"subn-{subscriber_id}",
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            plan_type=PlanType.POSTPAID,
            state=SubscriberState.PENDING_KYC,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=None,
            updated_at=_REGISTERED_AT,
        ),
    )
    connection.close()


def _seed_active_with_plan(
    settings: Settings, subscriber_id: str, mobile_number: str, plan_version_id: str
) -> str:
    connection = create_connection(settings.db_path)
    apply_schema(connection)
    create_subscriber(
        connection,
        Subscriber(
            subscriber_id=subscriber_id,
            mobile_number=mobile_number,
            identity_proof_ref="AADHAAR-XXXX-XXXX-6602",
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
            state=SubscriberState.PENDING_KYC,
            current_plan_version_id=None,
            dealer_code=None,
            created_at=_REGISTERED_AT,
            activated_at=None,
            updated_at=_REGISTERED_AT,
        ),
    )
    update_subscription_state(connection, subscription_id, SubscriberState.ACTIVE, _REGISTERED_AT)
    update_subscription_plan(connection, subscription_id, plan_version_id, _REGISTERED_AT)
    connection.close()
    return subscription_id


def _publish_plan(settings: Settings, plan_version_id: str, plan_id: str, price: str) -> None:
    connection = create_connection(settings.db_path)
    apply_schema(connection)
    create_plan_version(
        connection,
        PlanVersion(
            plan_version_id=plan_version_id,
            plan_id=plan_id,
            plan_name=plan_id,
            plan_type=PlanType.POSTPAID,
            version_number=1,
            price=__import__("decimal").Decimal(price),
            terms={},
            published=False,
            created_at=_REGISTERED_AT,
            published_at=None,
        ),
    )
    publish_plan_version(connection, plan_version_id, _REGISTERED_AT)
    connection.close()


def _staff_token(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token: str = response.json()["access_token"]
    return token


def test_csr_override_activation_with_dealer_fail_returns_200_active(
    client: TestClient, settings: Settings
) -> None:
    """AC-1: the override bypasses the dealer-code rule that would
    otherwise reject this exact call (DEALER-FAIL)."""
    _seed_pending_subscriber(settings, "csr-ovr-0001", "9876546601")
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.post(
        "/api/csr/overrides/activation/csr-ovr-0001",
        json={
            "dealer_code": "DEALER-FAIL",
            "reason_code": "MANUAL_KYC_VERIFIED",
            "original_rejection_reason": "DEALER_INVALID",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "ACTIVE"


def test_csr_override_activation_without_reason_code_returns_422(
    client: TestClient, settings: Settings
) -> None:
    """AC-3: rejected before any state change."""
    _seed_pending_subscriber(settings, "csr-ovr-0002", "9876546602")
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.post(
        "/api/csr/overrides/activation/csr-ovr-0002",
        json={"dealer_code": "DLR-BLR-001", "reason_code": "", "original_rejection_reason": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_non_csr_cannot_override_activation(client: TestClient, settings: Settings) -> None:
    """AC-4: an admin token is not a CSR token."""
    _seed_pending_subscriber(settings, "csr-ovr-0003", "9876546603")
    token = _staff_token(client, "admin_raj", "AdminDemo!2026Synthetic")

    response = client.post(
        "/api/csr/overrides/activation/csr-ovr-0003",
        json={
            "dealer_code": "DLR-BLR-001",
            "reason_code": "MANUAL_KYC_VERIFIED",
            "original_rejection_reason": "DEALER_INVALID",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_csr_override_plan_change_commits_despite_min_tenure(
    client: TestClient, settings: Settings
) -> None:
    """AC-2: the override bypasses the minimum-tenure rule that would
    otherwise reject this exact call."""
    _publish_plan(settings, "ovr-from-pv", "OVR-FROM-PLAN", "199.00")
    _publish_plan(settings, "ovr-to-pv", "OVR-TO-PLAN", "299.00")
    subscription_id = _seed_active_with_plan(
        settings, "csr-ovr-0004", "9876546604", "ovr-from-pv"
    )
    token = _staff_token(client, "csr_jane", "CsrDemo!2026Synthetic")

    response = client.post(
        f"/api/csr/overrides/plan-change/{subscription_id}",
        json={
            "target_plan_version_id": "ovr-to-pv",
            "reason_code": "GOODWILL_EXCEPTION",
            "original_rejection_reason": "MIN_TENURE_NOT_MET",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["subscription_id"] == subscription_id
