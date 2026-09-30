"""PlanVersion domain type.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.types.enums import PlanType


@dataclass(frozen=True)
class PlanVersion:
    """An immutable, versioned catalog entry once published."""

    plan_version_id: str
    plan_id: str
    plan_name: str
    plan_type: PlanType
    version_number: int
    price: Decimal
    terms: dict[str, object]
    published: bool
    created_at: datetime
    published_at: datetime | None

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal):
            raise TypeError(
                f"PlanVersion.price must be Decimal, got {type(self.price).__name__}"
            )
