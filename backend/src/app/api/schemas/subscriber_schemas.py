"""Pydantic request/response models for the registration and activation
API (E2-S4), auth-gated per api-contracts.md since E1-S6 built the login
endpoint these routes were originally waiting on: register requires a
subscriber-role bearer token (the "pre-registration token" from
POST /api/auth/login with just a mobile_number); activate requires that
token's subscriber_id to match the path parameter (require_own_subscriber,
E1-S4). register's response includes a fresh access_token with
subscriber_id populated, exactly as api-contracts.md documents, so the
caller can use it for the subsequent activate call instead of the stale
pre-registration token.
"""

from datetime import datetime

from pydantic import BaseModel

from app.types.enums import PlanType, SubscriberState


class RegisterSubscriberRequest(BaseModel):
    """POST /api/subscribers/register request body."""

    mobile_number: str
    identity_proof_ref: str
    plan_type: PlanType


class RegisterSubscriberResponse(BaseModel):
    """POST /api/subscribers/register 201 response."""

    subscriber_id: str
    subscription_id: str
    state: SubscriberState
    access_token: str


class ActivateSubscriberRequest(BaseModel):
    """POST /api/subscribers/{subscriber_id}/activate request body."""

    dealer_code: str


class ActivateSubscriberResponse(BaseModel):
    """POST /api/subscribers/{subscriber_id}/activate 200 response."""

    subscriber_id: str
    state: SubscriberState
    activated_at: datetime
