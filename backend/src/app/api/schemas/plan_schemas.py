"""Pydantic request/response models for the plan catalog admin API (E3-S3).

API layer. Money fields are typed `str` in RESPONSE models (not Decimal)
to guarantee the exact `"199.00"`-style wire format api-contracts.md
requires — Pydantic/FastAPI's default JSON encoding for a bare `Decimal`
field emits a JSON number, not a string, which would violate that
contract. REQUEST models use `Decimal` fields instead, since Pydantic
correctly parses an incoming JSON string into Decimal.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.types.enums import PlanType
from app.types.plan import PlanVersion


class CreatePlanVersionRequest(BaseModel):
    """POST /api/admin/plans request body."""

    plan_id: str
    plan_name: str
    plan_type: PlanType
    price: Decimal
    terms: dict[str, object]


class CreatePlanVersionResponse(BaseModel):
    """POST /api/admin/plans 201 response — confirms what was created."""

    plan_version_id: str
    plan_id: str
    version_number: int
    published: bool


class PublishPlanVersionResponse(BaseModel):
    """POST /api/admin/plans/{id}/publish 200 response."""

    plan_version_id: str
    published: bool
    published_at: datetime


class UpdatePlanVersionRequest(BaseModel):
    """PUT /api/admin/plans/{id} request body — either field may be omitted,
    in which case the version's current value is kept unchanged.
    """

    price: Decimal | None = None
    terms: dict[str, object] | None = None


class PlanVersionSchema(BaseModel):
    """A full PlanVersion, used for the PUT response and each item in the
    GET /api/admin/plans version-history list.
    """

    plan_version_id: str
    plan_id: str
    plan_name: str
    plan_type: PlanType
    version_number: int
    price: str
    terms: dict[str, object]
    published: bool
    created_at: datetime
    published_at: datetime | None

    @classmethod
    def from_domain(cls, plan_version: PlanVersion) -> "PlanVersionSchema":
        return cls(
            plan_version_id=plan_version.plan_version_id,
            plan_id=plan_version.plan_id,
            plan_name=plan_version.plan_name,
            plan_type=plan_version.plan_type,
            version_number=plan_version.version_number,
            price=str(plan_version.price),
            terms=plan_version.terms,
            published=plan_version.published,
            created_at=plan_version.created_at,
            published_at=plan_version.published_at,
        )


class PlanVersionListResponse(BaseModel):
    """GET /api/admin/plans 200 response."""

    plans: list[PlanVersionSchema]
