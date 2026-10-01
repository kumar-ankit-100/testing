"""Pydantic request/response models for the plan change API (E4-S4).

API layer.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PlanChangeRequest(BaseModel):
    """POST .../plan-change/{preview,commit} request body."""

    target_plan_version_id: str


class PlanChangePreviewResponse(BaseModel):
    """POST .../plan-change/preview 200 response (AC-1: no persistence)."""

    pro_rata_amount: Decimal


class PlanChangeCommitResponse(BaseModel):
    """POST .../plan-change/commit 200 response (AC-2)."""

    billing_record_id: str
    subscription_id: str
    from_plan_version_id: str | None
    to_plan_version_id: str
    pro_rata_amount: Decimal
    billing_period_start: date
    billing_period_end: date
