"""Pydantic request/response models for the CSR override API (E6-S3).

API layer. reason_code/original_rejection_reason use Field(min_length=1)
so a missing reason is rejected by Pydantic with a clean 422 before the
request ever reaches csr_override_service — the service's own
MissingOverrideReasonError check (mapped to the same 422/
MISSING_OVERRIDE_REASON) is defense-in-depth for callers that bypass
the API layer (e.g. a future direct-service test), not the primary gate.
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class OverrideActivationRequest(BaseModel):
    """POST /api/csr/overrides/activation/{subscriber_id} request body."""

    dealer_code: str
    reason_code: str = Field(min_length=1)
    original_rejection_reason: str = Field(min_length=1)


class OverridePlanChangeRequest(BaseModel):
    """POST /api/csr/overrides/plan-change/{subscription_id} request body."""

    target_plan_version_id: str
    reason_code: str = Field(min_length=1)
    original_rejection_reason: str = Field(min_length=1)


class OverrideActivationResponse(BaseModel):
    """POST /api/csr/overrides/activation/{subscriber_id} 200 response."""

    subscriber_id: str
    state: str


class OverridePlanChangeResponse(BaseModel):
    """POST /api/csr/overrides/plan-change/{subscription_id} 200 response."""

    billing_record_id: str
    subscription_id: str
    pro_rata_amount: Decimal
