"""Pydantic request/response models for the auth login endpoint (E1-S6).

API layer.
"""

from pydantic import BaseModel, Field


class RegisterStaffRequest(BaseModel):
    """POST /api/auth/register-staff request body (CSR/admin/dealer only;
    subscribers register via POST /api/subscribers/register instead)."""

    username: str = Field(min_length=1)
    password: str = Field(min_length=8)
    role: str


class RegisterStaffResponse(BaseModel):
    """POST /api/auth/register-staff 201 response."""

    user_id: str
    username: str
    role: str


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
