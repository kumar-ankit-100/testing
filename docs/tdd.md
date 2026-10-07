# TDD Discipline — TelcoLane

Every story in this repository was built test-first: write the failing test (red), implement just enough to pass it (green), then clean up without changing behavior (refactor) — before moving to the next acceptance criterion. `CLAUDE.md` states this as a hard rule (`TDD mandatory: test first, then implement`), and the harness's generator agent followed it story-by-story, confirmed in its own reports (e.g. Group E's: *"write a failing test, confirm it fails for the right reason, implement, confirm green, lint, typecheck, coverage, commit"*).

This repository has well over 10 test files committed across its history — `backend/tests/unit/` and `backend/tests/integration/` alone contain 30+ files, plus `frontend/tests/`.

## Worked Example: AC-05, the pro-rata leap-year boundary test

**Red.** Before `billing_calculation_service.py` existed, `backend/tests/unit/test_billing_calculation_service.py` was written with a table of 6 boundary-date scenarios, including:

```python
# 3. Mid-cycle upgrade in February of a leap year (2028, 29 days) (AC-2).
(
    Decimal("199.00"),
    Decimal("299.00"),
    date(2028, 2, 15),
    date(2028, 2, 1),
    date(2028, 2, 29),
    Decimal("48.28"),
),
```

Running this against a not-yet-written `calculate_pro_rata_charge` fails with `ImportError` — red, for the obviously-correct reason (the function doesn't exist yet), not a typo or a flaky assertion.

**Green.** The function was implemented to use `calendar.monthrange(change_date.year, change_date.month)` for the actual number of days in the cycle's month — not a hardcoded 30 or 28 — so a leap-year February is correct *by construction*, not by a special-cased `if year % 4 == 0` branch:

```python
days_in_cycle = calendar.monthrange(change_date.year, change_date.month)[1]
days_remaining = (billing_cycle_end - change_date).days
per_day_old = from_plan_price / Decimal(days_in_cycle)
per_day_new = to_plan_price / Decimal(days_in_cycle)
raw_charge = (per_day_new - per_day_old) * Decimal(days_remaining)
return max(Decimal("0.00"), raw_charge).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

All 6 scenarios passed, including the exact-boundary case (`change_date == cycle_end` → `days_remaining == 0` → `0.00` regardless of price difference) and a downgrade whose raw differential would naively be negative (clamped to `0.00` by the `max()`, satisfying the `charges_total >= 0` invariant, NFR-08).

**Refactor.** The validation logic (rejecting a `change_date` outside `[cycle_start, cycle_end]`) was extracted into `_validate_change_date` once a second test needed the same check, keeping the main function's happy path readable without changing any already-passing test's behavior.

## A Second Example: the suspend/resume FSM-ambiguity bug, caught by its own test

While building `suspend_resume_service.py`, a parametrized test asserting `resume_subscription` on a non-`SUSPENDED` subscription should raise `InvalidSubscriberStateException` failed unexpectedly for the `PENDING_KYC` case: the shared FSM table has `PENDING_KYC → ACTIVE` as a *valid* edge (that's how activation works), so relying on the generic FSM check alone let `resume_subscription` wrongly succeed on a `PENDING_KYC` subscription. The fix was an explicit `expected_from_state` check ahead of the generic FSM call — `suspend_subscription` didn't need this (`SUSPENDED` has exactly one valid incoming edge), which is exactly why the bug was resume-specific and easy to miss by symmetry. The red test is still in `backend/tests/unit/test_suspend_resume_service.py`, now green, and the reasoning is preserved in the service module's own docstring so a future reader doesn't reintroduce the same assumption.

## Coverage Discipline

100% statement coverage is treated as a floor to investigate, not a vanity number to chase blindly: every coverage gap found during this project's later groups (e.g. `reporting_service.py`'s percentage-remainder-correction branch, `lifecycle_router.py`'s staff-ownership-bypass branch) was closed with a test that exercises the *real* behavior the gap represented, not a throwaway call that merely executes the line. See `backend/tests/unit/test_reporting_service.py::test_as_percentages_corrects_a_rounding_remainder_onto_the_largest_bucket` for an example of a gap that turned out to be a genuinely untested rounding-correction rule, not dead code.
