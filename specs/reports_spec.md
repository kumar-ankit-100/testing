# Feature Spec — Admin Reporting (AC-10)

Activation funnel, churn, plan mix, and stubbed ARPU trend.

## Acceptance Criteria

**AC-10.1** — Given any amount of subscriber data (including none), when an admin requests the dashboard, then a well-formed activation funnel, plan mix, churn, and ARPU trend are returned — never an exception, even on an empty database.
*Tests:* `backend/tests/unit/test_reporting_service.py::test_dashboard_on_an_empty_database_returns_a_well_formed_empty_funnel`; `backend/tests/integration/test_admin_reports_api.py::test_admin_dashboard_returns_200_with_all_sections`

**AC-10.2** — Given subscription data across plan types, when plan-mix percentages are computed, then they sum to exactly 100.00 — independent per-bucket rounding can produce a ±0.01 remainder, which is corrected onto the largest bucket rather than left to silently drift.
*Test:* `test_reporting_service.py::test_as_percentages_corrects_a_rounding_remainder_onto_the_largest_bucket`

**AC-10.3** — Given `PORTED_OUT`/`TERMINATED` transitions across months, when the churn report is requested, then each month's rate divides the churned count by the active base reconstructed at that month's *start* (a point-in-time query over the `state_transitions` event log), not the current active count.
*Implementation:* `backend/src/app/repository/reporting_repository.py::_active_base_before`

**AC-10.4** — Given the ARPU trend is explicitly stubbed (no real usage-rated billing exists), when the dashboard is returned, then `metadata.arpu_trend_is_stubbed` is `true` with an explanatory note — never presented as real revenue data.
*Test:* `test_reporting_service.py::test_arpu_trend_metadata_is_labeled_as_stubbed`

**AC-10.5 / NFR-04** — Given a non-admin principal (e.g. CSR), when they request the dashboard, then it is rejected with HTTP 403, enforced inside the service independently of the router (so calling the service directly, bypassing the API, still fails closed).
*Test:* `test_admin_reports_api.py::test_non_admin_cannot_view_the_dashboard`

## Implementation

- Service: `backend/src/app/service/reporting_service.py`
- Repository: `backend/src/app/repository/reporting_repository.py`
- API: `backend/src/app/api/routers/admin_reports_router.py` — `GET /api/admin/reports/dashboard`
- UI: `frontend/src/ui/pages/AdminReportsDashboardPage.tsx` — a second admin tab alongside the plan catalog

## Known data-model limitation (documented, not a bug)

`kyc_passed`/`dealer_passed`/`mnp_passed` in the activation funnel report the same count as `activated`, because a *rejected* activation attempt writes no row anywhere (per the activation spec) — there is no stored signal distinguishing "never attempted" from "rejected at KYC" from "rejected at dealer" from "rejected at MNP". This satisfies the funnel's "each stage ≤ prior stage" requirement under equality rather than fabricating a distinction the data can't support.
