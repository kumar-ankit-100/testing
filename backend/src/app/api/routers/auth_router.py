"""Auth login endpoint (E1-S6) — the endpoint api-contracts.md has
always documented and that E1-S4's auth dependencies and E3-S3's admin
router have assumed exists since Group D.

API layer — imports Types, Config, Repository, Service.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_db_connection
from app.api.schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterStaffRequest,
    RegisterStaffResponse,
)
from app.config.settings import Settings, get_settings
from app.repository.subscriber_repository import get_subscriber_by_mobile
from app.repository.user_repository import get_user_by_username
from app.service.auth_service import create_access_token, verify_password
from app.service.logging_service import get_logger
from app.service.staff_registration_service import register_staff_user
from app.types.auth import Principal
from app.types.enums import Role
from app.types.exceptions import AuthenticationError

router = APIRouter(prefix="/api/auth", tags=["auth"])
_logger = get_logger(__name__)

# A precomputed hash of a random, never-used password. Checked when the
# supplied username doesn't exist, so the verify_password() call always
# runs — keeping "unknown user" and "wrong password" on the same code
# path (AC-3: no user-enumeration signal, not even a timing one).
_DUMMY_HASH = (
    "pbkdf2_sha256$390000$b0ccadb95661e756d8e9bc29ccefc63f"
    "$5ca3867be3adbd6c8a30122a841c578b1ff5abdeee36ec5bc91d91af4d316068"
)


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    """AC-1/AC-2: staff credentials or a subscriber mobile_number, 200
    with an access_token. AC-3: invalid staff credentials, 401
    UNAUTHENTICATED (identical response for unknown-user and
    wrong-password).
    """
    if request.mobile_number is not None:
        return _login_subscriber(connection, request.mobile_number, settings)
    return _login_staff(connection, request.username, request.password, settings)


@router.post(
    "/register-staff", response_model=RegisterStaffResponse, status_code=status.HTTP_201_CREATED
)
def register_staff(
    request: RegisterStaffRequest,
    connection: sqlite3.Connection = Depends(get_db_connection),
) -> RegisterStaffResponse:
    """Dynamic CSR/admin/dealer account creation. 422 for an unrecognized
    or non-staff role, 409 (via DuplicateUsernameError) for an existing
    username.
    """
    try:
        role = Role(request.role)
        user = register_staff_user(connection, request.username, request.password, role)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return RegisterStaffResponse(
        user_id=user.user_id, username=user.username or "", role=user.role.value
    )


def _login_staff(
    connection: sqlite3.Connection,
    username: str | None,
    password: str | None,
    settings: Settings,
) -> LoginResponse:
    user = get_user_by_username(connection, username) if username is not None else None
    hash_to_check = (
        user.password_hash if user is not None and user.password_hash is not None else _DUMMY_HASH
    )
    password_is_correct = verify_password(password or "", hash_to_check)

    if user is None or user.password_hash is None or not password_is_correct:
        _logger.info(
            "Staff login attempt failed", extra={"context": {"username": username}}
        )
        raise AuthenticationError("Invalid username or password")

    principal = Principal(user_id=user.user_id, role=user.role, subscriber_id=user.subscriber_id)
    token = create_access_token(principal, settings)
    _logger.info("Staff login attempt succeeded", extra={"context": {"username": username}})

    return LoginResponse(
        access_token=token,
        role=user.role.value,
        subscriber_id=user.subscriber_id,
        expires_in=settings.jwt_expiry_minutes * 60,
    )


def _login_subscriber(
    connection: sqlite3.Connection, mobile_number: str, settings: Settings
) -> LoginResponse:
    subscriber = get_subscriber_by_mobile(connection, mobile_number)
    subscriber_id = subscriber.subscriber_id if subscriber is not None else None

    principal = Principal(user_id=mobile_number, role=Role.SUBSCRIBER, subscriber_id=subscriber_id)
    token = create_access_token(principal, settings)
    _logger.info(
        "Subscriber login attempt succeeded",
        extra={"context": {"mobile_number": mobile_number}},
    )

    return LoginResponse(
        access_token=token,
        role=Role.SUBSCRIBER.value,
        subscriber_id=subscriber_id,
        expires_in=settings.jwt_expiry_minutes * 60,
    )
