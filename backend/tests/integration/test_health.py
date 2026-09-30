"""Integration tests for GET /health (E1-S5)."""

import time

from fastapi.testclient import TestClient

from app.api.main import app


def test_health_returns_200_with_ok_status_body() -> None:
    """AC-1: HTTP 200 with a JSON body containing status: 'ok'."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_responds_within_one_second() -> None:
    """AC-2: response latency is under 1000ms."""
    with TestClient(app) as client:
        start = time.perf_counter()
        response = client.get("/health")
        elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 1000


def test_health_succeeds_with_no_authorization_header_present() -> None:
    """AC-3: /health requires no authentication — no Authorization header is sent."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert "authorization" not in {h.lower() for h in response.request.headers}


def test_health_succeeds_on_first_call_immediately_after_startup_completes() -> None:
    """AC-4: calling /health right after startup succeeds without any retry."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
