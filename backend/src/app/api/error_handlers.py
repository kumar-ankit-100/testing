"""Maps domain exceptions to structured HTTP error responses (E1-S4).

API layer. Initial 401/403 mapping; extended by later API stories as new
domain exceptions are introduced (component-map.md cross-cutting notes).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.types.enums import ReasonCode
from app.types.exceptions import AuthenticationError, AuthorizationError


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
