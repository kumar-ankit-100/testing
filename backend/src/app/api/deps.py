"""Auth dependency injection: current_principal, require_role,
require_own_subscriber (E1-S4); DB connection dependency (E3-S3).

API layer — imports Types, Config, Repository, Service only.
"""

import sqlite3
from collections.abc import Callable, Iterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.db import create_connection
from app.config.settings import Settings, get_settings
from app.service.auth_service import decode_access_token
from app.types.auth import Principal
from app.types.enums import Role
from app.types.exceptions import AuthenticationError, AuthorizationError

_bearer_scheme = HTTPBearer(auto_error=False)


def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> Principal:
    """Resolve the authenticated Principal from the request's bearer token.

    `settings` is itself a FastAPI dependency (not read at module scope) so
    tests can override it via `app.dependency_overrides[get_settings]`
    instead of depending on real process environment variables.

    Raises AuthenticationError (mapped to HTTP 401) when the header is
    missing or the token fails verification.
    """
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    return decode_access_token(credentials.credentials, settings)


def require_role(*allowed_roles: Role) -> Callable[[Principal], Principal]:
    """Build a dependency that only allows principals whose role is in allowed_roles.

    Raises AuthorizationError (mapped to HTTP 403) otherwise.
    """

    def _check_role(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in allowed_roles:
            raise AuthorizationError(
                f"Role {principal.role.value} is not permitted to access this resource"
            )
        return principal

    return _check_role


def require_own_subscriber(
    subscriber_id: str, principal: Principal = Depends(current_principal)
) -> Principal:
    """Allow subscriber principals only onto their own subscriber_id path param.

    Staff roles (csr/admin/dealer) pass through without an ownership check —
    their own role scoping happens separately via require_role at the
    router that needs it (system-design.md 5.4).
    """
    if principal.role == Role.SUBSCRIBER and principal.subscriber_id != subscriber_id:
        raise AuthorizationError("Subscribers may only access their own subscription data")
    return principal


def get_db_connection(
    settings: Settings = Depends(get_settings),
) -> Iterator[sqlite3.Connection]:
    """Yield a request-scoped SQLite connection, closed after the request.

    The schema is applied once at app startup (see api.main's lifespan),
    not per request — this dependency only opens/closes a connection.
    `settings` is itself a dependency (see current_principal's docstring
    for why) so tests can point DB_PATH at an isolated temp file.
    """
    connection = create_connection(settings.db_path)
    try:
        yield connection
    finally:
        connection.close()
