"""Pydantic request/response models for the auth login endpoint (E1-S6).

API layer.
"""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """POST /api/auth/login request body.

    Staff login supplies username + password; subscriber self-service
    supplies mobile_number only. Exactly one of these two shapes is
    expected per call (per api-contracts.md); the router dispatches on
    whether mobile_number is present.
    """

    username: str | None = None
    password: str | None = None
    mobile_number: str | None = None


class LoginResponse(BaseModel):
    """POST /api/auth/login 200 response."""

    access_token: str
    role: str
    subscriber_id: str | None
    expires_in: int
