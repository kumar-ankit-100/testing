"""Maps domain exceptions to structured HTTP error responses (E1-S4).

API layer. Initial 401/403 mapping; extended by later API stories as new
domain exceptions are introduced (component-map.md cross-cutting notes).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.types.enums import ReasonCode, SubscriberState
from app.types.exceptions import (
    ActivationRejectedError,
    AuthenticationError,
    AuthorizationError,
    CoolingPeriodNotElapsedError,
    DuplicateActiveSubscriptionError,
    InvalidMobileNumberError,
    InvalidSubscriberStateException,
    MinTenureNotMetError,
    MissingOverrideReasonError,
    PlanVersionImmutableError,
    SubscriptionNotActiveError,
    SubscriptionSuspendedError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach domain-exception -> HTTP-response handlers to app."""

    @app.exception_handler(AuthenticationError)
    async def _handle_authentication_error(
        _request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return _error_response(401, ReasonCode.UNAUTHENTICATED, str(exc))

    @app.exception_handler(AuthorizationError)
    async def _handle_authorization_error(
        _request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        return _error_response(403, ReasonCode.FORBIDDEN, str(exc))

    @app.exception_handler(PlanVersionImmutableError)
    async def _handle_plan_version_immutable_error(
        _request: Request, exc: PlanVersionImmutableError
    ) -> JSONResponse:
        return _error_response(409, ReasonCode.PLAN_VERSION_IMMUTABLE, str(exc))

    @app.exception_handler(InvalidMobileNumberError)
    async def _handle_invalid_mobile_number_error(
        _request: Request, exc: InvalidMobileNumberError
    ) -> JSONResponse:
        return _error_response(422, ReasonCode.VALIDATION_ERROR, str(exc))

    @app.exception_handler(DuplicateActiveSubscriptionError)
    async def _handle_duplicate_active_subscription_error(
        _request: Request, exc: DuplicateActiveSubscriptionError
    ) -> JSONResponse:
        return _error_response(409, ReasonCode.DUPLICATE_ACTIVE_MOBILE, str(exc))

    @app.exception_handler(ActivationRejectedError)
    async def _handle_activation_rejected_error(
        _request: Request, exc: ActivationRejectedError
    ) -> JSONResponse:
        return _error_response(422, exc.reason_code, str(exc))

    @app.exception_handler(InvalidSubscriberStateException)
    async def _handle_invalid_subscriber_state_exception(
        _request: Request, exc: InvalidSubscriberStateException
    ) -> JSONResponse:
        reason_code = (
            ReasonCode.ALREADY_ACTIVE
            if exc.from_state == SubscriberState.ACTIVE
            else ReasonCode.INVALID_STATE_TRANSITION
        )
        return _error_response(409, reason_code, str(exc))

    @app.exception_handler(MinTenureNotMetError)
    async def _handle_min_tenure_not_met_error(
        _request: Request, exc: MinTenureNotMetError
    ) -> JSONResponse:
        return _error_response(422, ReasonCode.MIN_TENURE_NOT_MET, str(exc))

    @app.exception_handler(SubscriptionSuspendedError)
    async def _handle_subscription_suspended_error(
        _request: Request, exc: SubscriptionSuspendedError
    ) -> JSONResponse:
        return _error_response(409, ReasonCode.SUBSCRIPTION_SUSPENDED, str(exc))

    @app.exception_handler(SubscriptionNotActiveError)
    async def _handle_subscription_not_active_error(
        _request: Request, exc: SubscriptionNotActiveError
    ) -> JSONResponse:
        return _error_response(409, ReasonCode.INVALID_STATE_TRANSITION, str(exc))

    @app.exception_handler(CoolingPeriodNotElapsedError)
    async def _handle_cooling_period_not_elapsed_error(
        _request: Request, exc: CoolingPeriodNotElapsedError
    ) -> JSONResponse:
        return _error_response(422, ReasonCode.COOLING_PERIOD_NOT_ELAPSED, str(exc))

    @app.exception_handler(MissingOverrideReasonError)
    async def _handle_missing_override_reason_error(
        _request: Request, exc: MissingOverrideReasonError
    ) -> JSONResponse:
        return _error_response(422, ReasonCode.MISSING_OVERRIDE_REASON, str(exc))


def _error_response(status_code: int, reason_code: ReasonCode, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "reason_code": reason_code.value,
                "message": message,
                "details": {},
            }
        },
    )
