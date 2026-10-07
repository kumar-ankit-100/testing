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

from app.api.schemas.plan_schemas import PlanVersionSchema
from app.service.subscription_detail_service import SubscriptionDetail
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


class SubscriptionDetailResponse(BaseModel):
    """GET /api/subscribers/{subscriber_id}/subscription 200 response —
    the subscriber dashboard's main data source.
    """

    subscription_id: str
    subscriber_id: str
    mobile_number: str
    plan_type: PlanType
    state: SubscriberState
    dealer_code: str | None
    created_at: datetime
    activated_at: datetime | None
    current_plan: PlanVersionSchema | None

    @classmethod
    def from_domain(cls, detail: SubscriptionDetail) -> "SubscriptionDetailResponse":
        subscription = detail.subscription
        return cls(
            subscription_id=subscription.subscription_id,
            subscriber_id=subscription.subscriber_id,
            mobile_number=subscription.mobile_number,
            plan_type=subscription.plan_type,
            state=subscription.state,
            dealer_code=subscription.dealer_code,
            created_at=subscription.created_at,
            activated_at=subscription.activated_at,
            current_plan=(
                PlanVersionSchema.from_domain(detail.current_plan)
                if detail.current_plan is not None
                else None
            ),
        )
