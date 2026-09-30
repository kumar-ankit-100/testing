"""Integration tests for error_handlers.py's domain-exception mapping
(E1-S4 initial 401/403; extended here for E3-S3's 409 mapping).
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.error_handlers import register_exception_handlers
from app.types.exceptions import PlanVersionImmutableError


def _build_test_app() -> FastAPI:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/dummy/immutable-plan")
    def raise_immutable() -> None:
        raise PlanVersionImmutableError("pv_78")

    return test_app


def test_plan_version_immutable_error_maps_to_409_with_reason_code() -> None:
    with TestClient(_build_test_app()) as client:
        response = client.get("/dummy/immutable-plan")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["reason_code"] == "PLAN_VERSION_IMMUTABLE"
    assert "pv_78" in body["error"]["message"]
