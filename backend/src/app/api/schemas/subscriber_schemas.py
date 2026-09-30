"""Pydantic request/response models for the registration and activation
API (E2-S4).

API layer. Note: api-contracts.md documents these routes as requiring a
bearer token (a "pre-registration token" for register, "subscriber
(self)" ownership for activate, both obtained from POST /api/auth/login)
— but no story in specs/stories/dependency-graph.md builds that login
endpoint, and E2-S4's own acceptance criteria don't test auth for either
route. Both routes are therefore implemented without an auth gate for
now; a future auth-API story would need to add one once a way to mint a
token for a specific subscriber actually exists.
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


class ActivateSubscriberRequest(BaseModel):
    """POST /api/subscribers/{subscriber_id}/activate request body."""

    dealer_code: str


class ActivateSubscriberResponse(BaseModel):
    """POST /api/subscribers/{subscriber_id}/activate 200 response."""

    subscriber_id: str
    state: SubscriberState
    activated_at: datetime
