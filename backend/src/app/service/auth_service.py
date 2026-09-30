"""Access-token issuance and verification (E1-S4).

Service layer — imports Types and Config only for this module.

The bearer token is self-contained (role + subscriber_id embedded as
claims); per system-design.md 5.4, ownership checks compare the token's
subscriber_id claim directly against the requested path parameter, with
no repository round-trip needed on the authorization hot path.
"""

from datetime import UTC, datetime, timedelta

import jwt

from app.config.settings import Settings
from app.types.auth import Principal
from app.types.enums import Role
from app.types.exceptions import AuthenticationError

_SUBJECT_CLAIM = "sub"
_ROLE_CLAIM = "role"
_SUBSCRIBER_ID_CLAIM = "subscriber_id"


def create_access_token(principal: Principal, settings: Settings) -> str:
    """Encode principal's identity as a signed, expiring JWT."""
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        _SUBJECT_CLAIM: principal.user_id,
        _ROLE_CLAIM: principal.role.value,
        _SUBSCRIBER_ID_CLAIM: principal.subscriber_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> Principal:
    """Verify token's signature and expiry, and return its Principal claims.

    Raises AuthenticationError for any invalid, expired, or malformed token.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc

    return _principal_from_claims(payload)


def _principal_from_claims(payload: dict[str, object]) -> Principal:
    user_id = payload.get(_SUBJECT_CLAIM)
    role_value = payload.get(_ROLE_CLAIM)
    if not isinstance(user_id, str) or not isinstance(role_value, str):
        raise AuthenticationError("Access token is missing required claims")

    try:
        role = Role(role_value)
    except ValueError as exc:
        raise AuthenticationError("Access token has an unrecognized role claim") from exc

    subscriber_id = payload.get(_SUBSCRIBER_ID_CLAIM)
    if subscriber_id is not None and not isinstance(subscriber_id, str):
        raise AuthenticationError("Access token has a malformed subscriber_id claim")

    return Principal(user_id=user_id, role=role, subscriber_id=subscriber_id)
