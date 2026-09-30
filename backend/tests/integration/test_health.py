"""Integration tests for GET /health (E1-S5)."""

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A fresh app per test, pointed at an isolated temp DB.

    create_app() now attaches a lifespan that applies the schema at
    startup (E3-S3) — every TestClient(create_app()) triggers it, so
    DB_PATH must be isolated per test rather than touching the real
    default path on disk.
    """
    monkeypatch.setenv("DB_PATH", str(tmp_path / "health_test.db"))
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_returns_200_with_ok_status_body(client: TestClient) -> None:
    """AC-1: HTTP 200 with a JSON body containing status: 'ok'."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_responds_within_one_second(client: TestClient) -> None:
    """AC-2: response latency is under 1000ms."""
    start = time.perf_counter()
    response = client.get("/health")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 1000


def test_health_succeeds_with_no_authorization_header_present(client: TestClient) -> None:
    """AC-3: /health requires no authentication — no Authorization header is sent."""
    response = client.get("/health")

    assert response.status_code == 200
    assert "authorization" not in {h.lower() for h in response.request.headers}


def test_health_succeeds_on_first_call_immediately_after_startup_completes(
    client: TestClient,
) -> None:
    """AC-4: calling /health right after startup succeeds without any retry."""
    response = client.get("/health")

    assert response.status_code == 200
