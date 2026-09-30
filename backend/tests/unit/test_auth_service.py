"""Unit tests for JWT access-token issuance and verification (E1-S4)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config.settings import Settings
from app.service.auth_service import create_access_token, decode_access_token
from app.types.auth import Principal
from app.types.enums import Role
from app.types.exceptions import AuthenticationError


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None, jwt_secret_key="unit-test-signing-secret-at-least-32-bytes-long"
    )


def test_create_access_token_round_trips_through_decode(settings: Settings) -> None:
    principal = Principal(
        user_id="9a1b2c3d-1111-4e22-9f33-444455556666",
        role=Role.SUBSCRIBER,
        subscriber_id="7f1c2f3a-9b1a-4c3e-8e2f-1a2b3c4d5e6f",
    )

    token = create_access_token(principal, settings)
    decoded = decode_access_token(token, settings)

    assert decoded == principal


def test_decode_access_token_round_trips_staff_principal_with_null_subscriber_id(
    settings: Settings,
) -> None:
    principal = Principal(
        user_id="9a1b2c3d-2222-4e22-9f33-444455556666", role=Role.CSR, subscriber_id=None
    )

    token = create_access_token(principal, settings)
    decoded = decode_access_token(token, settings)

    assert decoded == principal


def test_decode_access_token_rejects_a_token_signed_with_a_different_secret(
    settings: Settings,
) -> None:
    principal = Principal(
        user_id="9a1b2c3d-3333-4e22-9f33-444455556666", role=Role.ADMIN, subscriber_id=None
    )
    token = create_access_token(principal, settings)
    wrong_secret_settings = Settings(
        _env_file=None, jwt_secret_key="a-different-secret-that-is-also-at-least-32-bytes"
    )

    with pytest.raises(AuthenticationError):
        decode_access_token(token, wrong_secret_settings)


def test_decode_access_token_rejects_an_expired_token(settings: Settings) -> None:
    now = datetime.now(UTC)
    expired_payload = {
        "sub": "9a1b2c3d-4444-4e22-9f33-444455556666",
        "role": Role.SUBSCRIBER.value,
        "subscriber_id": None,
        "iat": now - timedelta(minutes=120),
        "exp": now - timedelta(minutes=60),
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(AuthenticationError):
        decode_access_token(expired_token, settings)


def test_decode_access_token_rejects_malformed_garbage_input(settings: Settings) -> None:
    with pytest.raises(AuthenticationError):
        decode_access_token("not-a-real-jwt", settings)


def test_decode_access_token_rejects_a_token_missing_the_role_claim(settings: Settings) -> None:
    payload_missing_role = {"sub": "9a1b2c3d-5555-4e22-9f33-444455556666"}
    token = jwt.encode(
        payload_missing_role, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings)


def test_decode_access_token_rejects_a_token_with_an_unrecognized_role_claim(
    settings: Settings,
) -> None:
    payload_bad_role = {
        "sub": "9a1b2c3d-6666-4e22-9f33-444455556666",
        "role": "super-root",
        "subscriber_id": None,
    }
    token = jwt.encode(payload_bad_role, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings)


def test_decode_access_token_rejects_a_token_with_a_non_string_subscriber_id(
    settings: Settings,
) -> None:
    payload_bad_subscriber_id = {
        "sub": "9a1b2c3d-7777-4e22-9f33-444455556666",
        "role": Role.SUBSCRIBER.value,
        "subscriber_id": 12345,
    }
    token = jwt.encode(
        payload_bad_subscriber_id, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings)
