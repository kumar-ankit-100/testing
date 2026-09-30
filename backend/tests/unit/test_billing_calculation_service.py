"""Unit tests for the pure pro-rata billing calculation service (E4-S2).

Formula (documented in billing_calculation_service.py, since no story pins
down the exact numeric formula — the BRD explicitly defers "precise
wording/thresholds for the leap-year boundary pro-rata test case" to
implementation): the incremental per-day price differential between the
old and new plan, times the number of days strictly AFTER change_date
through billing_cycle_end (exclusive of change_date itself — the
changeover is considered to take full effect starting the day after), with
days-in-cycle taken from the actual calendar month of change_date via
calendar.monthrange (so leap-year February is exact), clamped to >= 0.00.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.service.billing_calculation_service import calculate_pro_rata_charge

# (from_price, to_price, change_date, cycle_start, cycle_end, expected)
BOUNDARY_DATE_SCENARIOS: list[tuple[Decimal, Decimal, date, date, date, Decimal]] = [
    # 1. Exactly at the billing-cycle boundary (change_date == cycle_end):
    #    0 days remain after the change within this cycle -> 0.00 regardless
    #    of the price difference (AC-1).
    (
        Decimal("199.00"),
        Decimal("299.00"),
        date(2026, 1, 31),
        date(2026, 1, 1),
        date(2026, 1, 31),
        Decimal("0.00"),
    ),
    # 2. Mid-cycle upgrade in February of a non-leap year (2026, 28 days) (AC-2).
    (
        Decimal("199.00"),
        Decimal("299.00"),
        date(2026, 2, 15),
        date(2026, 2, 1),
        date(2026, 2, 28),
        Decimal("46.43"),
    ),
    # 3. Mid-cycle upgrade in February of a leap year (2028, 29 days) (AC-2).
    (
        Decimal("199.00"),
        Decimal("299.00"),
        date(2028, 2, 15),
        date(2028, 2, 1),
        date(2028, 2, 29),
        Decimal("48.28"),
    ),
    # 4. Downgrade whose raw differential is negative, one day before cycle
    #    end -> clamped to 0.00, not a negative credit (AC-3).
    (
        Decimal("499.00"),
        Decimal("199.00"),
        date(2026, 3, 30),
        date(2026, 3, 1),
        date(2026, 3, 31),
        Decimal("0.00"),
    ),
    # 5. Mid-cycle upgrade in a 31-day month (January).
    (
        Decimal("99.00"),
        Decimal("149.00"),
        date(2026, 1, 10),
        date(2026, 1, 1),
        date(2026, 1, 31),
        Decimal("33.87"),
    ),
    # 6. Upgrade very early in a 30-day month (June) -> most of the cycle remains.
    (
        Decimal("149.00"),
        Decimal("249.00"),
        date(2026, 6, 2),
        date(2026, 6, 1),
        date(2026, 6, 30),
        Decimal("93.33"),
    ),
]


@pytest.mark.parametrize(
    ("from_price", "to_price", "change_date", "cycle_start", "cycle_end", "expected"),
    BOUNDARY_DATE_SCENARIOS,
)
def test_calculate_pro_rata_charge_matches_expected_decimal_exactly(
    from_price: Decimal,
    to_price: Decimal,
    change_date: date,
    cycle_start: date,
    cycle_end: date,
    expected: Decimal,
) -> None:
    result = calculate_pro_rata_charge(from_price, to_price, change_date, cycle_start, cycle_end)

    assert result == expected
    assert isinstance(result, Decimal)


def test_all_boundary_date_scenarios_are_never_negative() -> None:
    """AC-3 (NFR-08): charges_total >= 0 for every generated test case,
    including the downgrade scenario that could naively produce a
    negative credit-only figure.
    """
    assert all(scenario[-1] >= Decimal("0.00") for scenario in BOUNDARY_DATE_SCENARIOS)


def test_calculate_pro_rata_charge_rejects_a_change_date_before_the_cycle_start() -> None:
    with pytest.raises(ValueError, match="billing_cycle_start"):
        calculate_pro_rata_charge(
            Decimal("199.00"),
            Decimal("299.00"),
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 2, 28),
        )


def test_calculate_pro_rata_charge_rejects_a_change_date_after_the_cycle_end() -> None:
    with pytest.raises(ValueError, match="billing_cycle_end"):
        calculate_pro_rata_charge(
            Decimal("199.00"),
            Decimal("299.00"),
            date(2026, 3, 1),
            date(2026, 2, 1),
            date(2026, 2, 28),
        )


def test_calculate_pro_rata_charge_same_price_change_is_always_zero() -> None:
    """No differential between old and new price -> zero charge regardless
    of how many days remain."""
    result = calculate_pro_rata_charge(
        Decimal("199.00"), Decimal("199.00"), date(2026, 4, 10), date(2026, 4, 1), date(2026, 4, 30)
    )

    assert result == Decimal("0.00")
