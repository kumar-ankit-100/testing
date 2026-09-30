"""Integration tests for error_handlers.py's domain-exception mapping
(E1-S4 initial 401/403; extended by E3-S3's 409 and E2-S4's 422/409 set).
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.error_handlers import register_exception_handlers
from app.types.enums import ReasonCode, SubscriberState
from app.types.exceptions import (
    ActivationRejectedError,
    DuplicateActiveSubscriptionError,
    InvalidMobileNumberError,
    InvalidSubscriberStateException,
    PlanVersionImmutableError,
)


def _build_test_app() -> FastAPI:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/dummy/immutable-plan")
    def raise_immutable() -> None:
        raise PlanVersionImmutableError("pv_78")

    @test_app.get("/dummy/invalid-mobile")
    def raise_invalid_mobile() -> None:
        raise InvalidMobileNumberError("12345")

    @test_app.get("/dummy/duplicate-active")
    def raise_duplicate_active() -> None:
        raise DuplicateActiveSubscriptionError("9876543210")

    @test_app.get("/dummy/activation-rejected")
    def raise_activation_rejected() -> None:
        raise ActivationRejectedError(ReasonCode.KYC_UNVERIFIED)

    @test_app.get("/dummy/already-active")
    def raise_already_active() -> None:
        raise InvalidSubscriberStateException(SubscriberState.ACTIVE, SubscriberState.ACTIVE)

    @test_app.get("/dummy/invalid-transition")
    def raise_invalid_transition() -> None:
        raise InvalidSubscriberStateException(
            SubscriberState.PENDING_KYC, SubscriberState.SUSPENDED
        )

    return test_app


def test_plan_version_immutable_error_maps_to_409_with_reason_code() -> None:
    with TestClient(_build_test_app()) as client:
        response = client.get("/dummy/immutable-plan")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["reason_code"] == "PLAN_VERSION_IMMUTABLE"
    assert "pv_78" in body["error"]["message"]


def test_invalid_mobile_number_error_maps_to_422_validation_error() -> None:
    with TestClient(_build_test_app()) as client:
        response = client.get("/dummy/invalid-mobile")

    assert response.status_code == 422
    assert response.json()["error"]["reason_code"] == "VALIDATION_ERROR"


def test_duplicate_active_subscription_error_maps_to_409() -> None:
    with TestClient(_build_test_app()) as client:
        response = client.get("/dummy/duplicate-active")

    assert response.status_code == 409
    assert response.json()["error"]["reason_code"] == "DUPLICATE_ACTIVE_MOBILE"


def test_activation_rejected_error_maps_to_422_with_its_own_reason_code() -> None:
    with TestClient(_build_test_app()) as client:
        response = client.get("/dummy/activation-rejected")

    assert response.status_code == 422
    assert response.json()["error"]["reason_code"] == "KYC_UNVERIFIED"


def test_invalid_subscriber_state_from_active_maps_to_already_active() -> None:
    with TestClient(_build_test_app()) as client:
        response = client.get("/dummy/already-active")

    assert response.status_code == 409
    assert response.json()["error"]["reason_code"] == "ALREADY_ACTIVE"


def test_invalid_subscriber_state_otherwise_maps_to_invalid_state_transition() -> None:
    with TestClient(_build_test_app()) as client:
        response = client.get("/dummy/invalid-transition")

    assert response.status_code == 409
    assert response.json()["error"]["reason_code"] == "INVALID_STATE_TRANSITION"
