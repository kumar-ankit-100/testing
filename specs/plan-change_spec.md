# Feature Spec — Plan Upgrade/Downgrade with Pro-Rata Billing (AC-04, AC-05)

Plan change preview-then-commit, with a minimum-tenure rule and exact pro-rata billing.

## Acceptance Criteria

**AC-04.1** — Given an ACTIVE subscription below the configured minimum tenure, when a plan change is requested, then it is rejected with HTTP 422 / `MIN_TENURE_NOT_MET`, with no `BillingRecord` written.
*Test:* `backend/tests/integration/test_plan_change_api.py::test_commit_below_minimum_tenure_returns_422_with_reason_code`

**AC-04.2** — Given a SUSPENDED subscription, when a plan change is requested, then it is rejected with HTTP 409 / `SUBSCRIPTION_SUSPENDED`.
*Test:* `test_plan_change_api.py::test_commit_on_a_suspended_subscription_returns_409_with_reason_code`

**AC-05.1** — Given an eligible subscription, when a plan-change preview is requested, then the pro-rata amount is computed and returned with no persistence — `preview` and `commit` share one internal calculation path (`billing_calculation_service.calculate_pro_rata_charge`) so they can never disagree.
*Test:* `test_plan_change_api.py::test_preview_returns_pro_rata_without_mutating`

**AC-05.2** — Given an eligible subscription, when a plan change is committed, then the subscription's current plan updates and a new, independent, append-only `BillingRecord` is persisted — a second commit never overwrites the first.
*Tests:* `test_plan_change_api.py::test_commit_on_an_eligible_subscription_returns_new_plan_and_billing_record`; `backend/tests/unit/test_plan_change_service.py::test_two_consecutive_commits_each_produce_an_independent_billing_record`

**AC-05.3** — Given any boundary date (including the exact cycle boundary and a leap-year February), when the pro-rata charge is calculated, then `charges_total >= 0` holds and the value matches a hand-computed expectation exactly (NFR-01, NFR-08).
*Test:* `backend/tests/unit/test_billing_calculation_service.py::test_calculate_pro_rata_charge_matches_expected_decimal_exactly` — a 6-scenario table including the exact-boundary-day → 0.00 case and the 2028 leap-year February case; `test_all_boundary_date_scenarios_are_never_negative` covers a downgrade whose raw differential would naively be negative.

**AC-04.3 / NFR-04** — Given a subscriber's token, when they request a plan change for a subscription that isn't theirs, then it is rejected with HTTP 403; staff roles (CSR/admin) bypass this ownership check.
*Tests:* `test_plan_change_api.py::test_subscriber_calling_for_a_non_own_subscription_is_forbidden`; `test_staff_can_preview_without_an_ownership_check`

## Implementation

- Services: `backend/src/app/service/billing_calculation_service.py` (pure function, no I/O), `backend/src/app/service/plan_change_service.py`
- API: `backend/src/app/api/routers/plan_change_router.py` — `POST /api/subscriptions/{id}/plan-change/{preview,commit}`
- UI: `frontend/src/ui/pages/ActivationStatusPage.tsx`'s subscription-management panel (preview button → amount shown → confirm button)

## Note on the pro-rata formula

No story pins an exact numeric formula — the capstone brief gives `charges_total = (days_used/cycle_days × old_rent) + (days_remaining/cycle_days × new_rent)`, but this repository's implementation uses the mathematically-equivalent-in-spirit incremental-differential form documented in `billing_calculation_service.py`'s own module docstring: the per-day price difference × days remaining in the cycle after the change, using `calendar.monthrange` for the actual days-in-month so leap years are correct by construction rather than special-cased. Both forms satisfy the `charges_total >= 0` invariant and produce the same boundary behavior (0 at the exact cycle end).
