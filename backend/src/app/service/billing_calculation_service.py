"""Pure pro-rata billing calculation for plan upgrade/downgrade (E4-S2).

Service layer — no I/O, no imports beyond Types/stdlib. Called identically
by preview (no persistence) and commit (persists the same computed value)
so the two can never disagree (system-design.md 5.6).

Formula (this module's own documented design — no story specifies exact
numeric thresholds; the BRD explicitly defers that to implementation):
the incremental per-day price differential between the old and new plan,
times the number of days strictly AFTER change_date through
billing_cycle_end (change_date itself is excluded — the changeover takes
full effect starting the day after it), clamped to >= 0.00 (NFR-08).
days-in-cycle is the actual number of days in change_date's calendar
month via calendar.monthrange, so a leap-year February is exact by
construction rather than a special case.
"""

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

_CENTS = Decimal("0.01")


def calculate_pro_rata_charge(
    from_plan_price: Decimal,
    to_plan_price: Decimal,
    change_date: date,
    billing_cycle_start: date,
    billing_cycle_end: date,
) -> Decimal:
    """Return the clamped (>= 0.00) pro-rata charge for switching plans.

    Raises ValueError if change_date falls outside
    [billing_cycle_start, billing_cycle_end].
    """
    _validate_change_date(change_date, billing_cycle_start, billing_cycle_end)

    days_in_cycle = calendar.monthrange(change_date.year, change_date.month)[1]
    days_remaining = (billing_cycle_end - change_date).days

    per_day_old = from_plan_price / Decimal(days_in_cycle)
    per_day_new = to_plan_price / Decimal(days_in_cycle)
    raw_charge = (per_day_new - per_day_old) * Decimal(days_remaining)

    return max(Decimal("0.00"), raw_charge).quantize(_CENTS, rounding=ROUND_HALF_UP)


def _validate_change_date(
    change_date: date, billing_cycle_start: date, billing_cycle_end: date
) -> None:
    if change_date < billing_cycle_start:
        raise ValueError(
            f"change_date {change_date} is before billing_cycle_start {billing_cycle_start}"
        )
    if change_date > billing_cycle_end:
        raise ValueError(
            f"change_date {change_date} is after billing_cycle_end {billing_cycle_end}"
        )
