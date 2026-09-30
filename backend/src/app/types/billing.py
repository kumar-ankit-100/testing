"""BillingRecord domain type.

Types layer — zero imports from Config, Repository, Service, API, or UI.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class BillingRecord:
    """An append-only record of a pro-rata charge produced by a plan change."""

    billing_record_id: str
    subscription_id: str
    from_plan_version_id: str | None
    to_plan_version_id: str
    pro_rata_amount: Decimal
    charges_total: Decimal
    billing_period_start: date
    billing_period_end: date
    created_at: datetime

    def __post_init__(self) -> None:
        for field_name in ("pro_rata_amount", "charges_total"):
            value = getattr(self, field_name)
            if not isinstance(value, Decimal):
                raise TypeError(
                    f"BillingRecord.{field_name} must be Decimal, "
                    f"got {type(value).__name__}"
                )
