# Evaluator Report — Group B

Date: 2026-09-30T05:16:09Z (initial pass); corrected verdict re-verified 2026-09-30T05:22:48Z
VERDICT: PASS

## Scope Note

Per `sprint-contracts/group-b.json`'s `note_for_evaluator`: Group B introduces the first API routes (E1-S4 auth deps, E1-S5 `/health`) but there is still no long-running server process. E1-S4/E1-S5's integration tests use FastAPI's in-process `TestClient` (`tests/integration/test_auth.py`, `tests/integration/test_health.py`), which is treated as equivalent evidence to a live HTTP call. `api_checks`/`playwright_checks` are intentionally empty for the same reason as Group A. The Docker/health-check-reachability step was skipped entirely, as instructed. Only `contract.architecture_checks` was evaluated, including all 40 `test_checks` entries.

No API Checks, Playwright Checks, or Design Checks were run (contract arrays intentionally empty; none apply to this group).

## Contract Correction Between Evaluation Passes

The initial pass (2026-09-30T05:16:09Z) found `grp-b-09` and `grp-b-10` FAILing on an exact-count mismatch: both commands ran clean with zero test failures, but returned more passed items ("4 passed", "8 passed") than the contract's then-current `expected` strings said ("3 passed", "7 passed"). Root cause, confirmed via `pytest -v --collect-only`: `test_csr_or_admin_can_access_their_scoped_endpoint_without_403` (`backend/tests/integration/test_auth.py:135-136`) is `@pytest.mark.parametrize("role", [Role.CSR, Role.ADMIN])`, so pytest collects it as 2 test items, not 1 — a legitimately more thorough test (it explicitly exercises both CSR and admin), not a bug.

The coordinator independently confirmed this diagnosis and corrected `sprint-contracts/group-b.json` in place between the two evaluation passes: `grp-b-09`'s `expected` was changed to `"4 passed"` and `grp-b-10`'s `expected` was changed to `"8 passed"` (both entries' `description` fields were also updated to note the parametrization). No other part of the contract was changed by the coordinator, and this evaluator did not modify the contract at any point (read-only input throughout, per instructions).

Both commands were re-run verbatim against the corrected contract at 2026-09-30T05:22:48Z and now match exactly (see the updated `grp-b-09`/`grp-b-10` entries below). All 40/40 `test_checks` entries and all 5 required `architecture_checks` now pass. **Overall verdict updated from FAIL to PASS.**

## Architecture Checks — `test_checks` (40/40 PASS)

- [PASS] grp-b-01 (F011, E1-S3 AC-1): Logger emits single JSON object with timestamp/level/message.
  - Command: `cd backend && uv run pytest -q tests/unit/test_logging_service.py::test_log_entry_is_single_json_object_with_required_keys`
  - Actual: `1 passed` in 0.01s, exit 0. Matches expected.

- [PASS] grp-b-02 (F012, E1-S3 AC-2): Mobile number masked to last 4 digits.
  - Command: `cd backend && uv run pytest -q tests/unit/test_logging_service.py::test_mobile_number_in_context_is_masked_to_last_four_digits`
  - Actual: `1 passed` in 0.01s, exit 0. Matches expected.

- [PASS] grp-b-03 (F013, E1-S3 AC-3): Aadhaar/PAN masked with same partial-reveal rule.
  - Command: `cd backend && uv run pytest -q tests/unit/test_logging_service.py::test_aadhaar_and_pan_refs_are_masked_with_same_partial_reveal_rule`
  - Actual: `1 passed` in 0.01s, exit 0. Matches expected.

- [PASS] grp-b-04 (F014, E1-S3 AC-4): All three PII fields together never appear unmasked.
  - Command: `cd backend && uv run pytest -q tests/unit/test_logging_service.py::test_all_three_pii_fields_together_never_appear_unmasked_in_emitted_json`
  - Actual: `1 passed` in 0.01s, exit 0. Matches expected.

- [PASS] grp-b-05 (F015, E1-S3 AC-5): `logging_service.py`/`pii_mask.py` import only Types+Config.
  - Command: `cd backend && grep -rnE '^(from|import)[[:space:]]+app\.(repository|api)' src/app/service/logging_service.py src/app/lib/pii_mask.py || echo NONE_FOUND`
  - Actual: `NONE_FOUND`. Matches expected.

- [PASS] grp-b-06 (F016, E1-S4 AC-1): Unauthenticated / malformed bearer token -> 401.
  - Command: `cd backend && uv run pytest -q tests/integration/test_auth.py::test_unauthenticated_request_receives_401 tests/integration/test_auth.py::test_malformed_bearer_token_receives_401`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-07 (F017, E1-S4 AC-2): Subscriber calling CSR-only endpoint -> 403.
  - Command: `cd backend && uv run pytest -q tests/integration/test_auth.py::test_subscriber_calling_csr_only_endpoint_receives_403`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-08 (F018, E1-S4 AC-3): Subscriber requesting another subscriber's data -> 403.
  - Command: `cd backend && uv run pytest -q tests/integration/test_auth.py::test_subscriber_requesting_another_subscribers_data_receives_403`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-09 (F019, E1-S4 AC-4): CSR/admin scoped-access-without-403 + own-data-succeeds + staff-not-subject-to-ownership-checks.
  - Command: `cd backend && uv run pytest -q tests/integration/test_auth.py::test_csr_or_admin_can_access_their_scoped_endpoint_without_403 tests/integration/test_auth.py::test_subscriber_requesting_own_data_succeeds tests/integration/test_auth.py::test_csr_and_admin_are_not_subject_to_subscriber_ownership_checks`
  - Expected (corrected by coordinator): `4 passed`
  - Actual: `4 passed`, exit 0. Matches expected exactly. (Initial pass, against the pre-correction contract expecting `3 passed`, recorded this as FAIL — see "Contract Correction Between Evaluation Passes" above. `test_csr_or_admin_can_access_their_scoped_endpoint_without_403` is `@pytest.mark.parametrize("role", [Role.CSR, Role.ADMIN])`, correctly collecting as 2 items, for 4 total across the 3 named tests.)

- [PASS] grp-b-10 (F020, E1-S4 AC-5): Full `test_auth.py` integration file exercises all four auth cases.
  - Command: `cd backend && uv run pytest -q tests/integration/test_auth.py`
  - Expected (corrected by coordinator): `8 passed`
  - Actual: `8 passed`, exit 0. Matches expected exactly. (Initial pass, against the pre-correction contract expecting `7 passed`, recorded this as FAIL — same root cause as grp-b-09. Independently corroborated by `grp-b-39-full-suite`'s own aggregate of exactly `129 passed`, which was already only reachable with 8, not 7, collected items in this file.)

- [PASS] grp-b-11 (F021, E1-S5 AC-1): `GET /health` -> 200 `{"status": "ok"}`.
  - Command: `cd backend && uv run pytest -q tests/integration/test_health.py::test_health_returns_200_with_ok_status_body`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-12 (F022, E1-S5 AC-2): `/health` latency < 1000ms.
  - Command: `cd backend && uv run pytest -q tests/integration/test_health.py::test_health_responds_within_one_second`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-13 (F023, E1-S5 AC-3): `/health` requires no authentication.
  - Command: `cd backend && uv run pytest -q tests/integration/test_health.py::test_health_succeeds_with_no_authorization_header_present`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-14 (F024, E1-S5 AC-4): `/health` succeeds on first call after startup.
  - Command: `cd backend && uv run pytest -q tests/integration/test_health.py::test_health_succeeds_on_first_call_immediately_after_startup_completes`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-15 (F025, E2-S1 AC-1): Repository create/get-by-id/get-by-mobile round-trip + not-found paths.
  - Command: `cd backend && uv run pytest -q tests/unit/test_subscriber_repository.py::test_create_and_get_subscriber_by_id_round_trips tests/unit/test_subscriber_repository.py::test_get_subscriber_by_id_returns_none_when_not_found tests/unit/test_subscriber_repository.py::test_get_subscriber_by_mobile_finds_the_matching_row tests/unit/test_subscriber_repository.py::test_get_subscriber_by_mobile_returns_none_when_not_found`
  - Actual: `4 passed`, exit 0. Matches expected.

- [PASS] grp-b-16 (F026, E2-S1 AC-2): Partial unique index on `(mobile_number) WHERE state='ACTIVE'`.
  - Command: `cd backend && grep -n 'idx_subscriptions_active_mobile' src/app/repository/schema.sql && uv run pytest -q tests/unit/test_subscriber_repository.py::test_second_active_subscription_for_same_mobile_raises_integrity_error`
  - Actual: grep found `55:CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_active_mobile`; `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-17 (F027, E2-S1 AC-3): `dealer_master` seeded with >= 5 valid codes + `DEALER-FAIL` sentinel.
  - Command: `cd backend && uv run pytest -q tests/unit/test_dealer_repository.py::test_at_least_five_valid_dealer_codes_are_seeded tests/unit/test_dealer_repository.py::test_dealer_fail_sentinel_is_seeded_on_schema_apply tests/unit/test_dealer_repository.py::test_seeded_valid_dealers_are_active`
  - Actual: `3 passed`, exit 0. Matches expected.

- [PASS] grp-b-18 (F028, E2-S1 AC-4): Second ACTIVE subscription for same mobile raises IntegrityError; non-ACTIVE duplicates don't conflict.
  - Command: `cd backend && uv run pytest -q tests/unit/test_subscriber_repository.py::test_second_active_subscription_for_same_mobile_raises_integrity_error tests/unit/test_subscriber_repository.py::test_non_active_subscriptions_for_same_mobile_do_not_conflict`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-19 (F029, E2-S1 AC-5): `subscriber_repository.py`/`dealer_repository.py` import only Types+Config.
  - Command: `cd backend && grep -rnE '^(from|import)[[:space:]]+app\.(service|api)' src/app/repository/subscriber_repository.py src/app/repository/dealer_repository.py || echo NONE_FOUND`
  - Actual: `NONE_FOUND`. Matches expected.

- [PASS] grp-b-20 (F049, E3-S1 AC-1): Repository exposes create/publish/get_published/list_versions.
  - Command: `cd backend && uv run pytest -q tests/unit/test_plan_repository.py`
  - Actual: `9 passed`, exit 0. Matches expected.

- [PASS] grp-b-21 (F050, E3-S1 AC-2): Update/delete of published version rejected; re-publish rejected.
  - Command: `cd backend && uv run pytest -q tests/unit/test_plan_repository.py::test_direct_update_of_a_published_versions_price_is_rejected tests/unit/test_plan_repository.py::test_direct_delete_of_a_plan_version_is_rejected tests/unit/test_plan_repository.py::test_republishing_an_already_published_version_is_rejected`
  - Actual: `3 passed`, exit 0. Matches expected.

- [PASS] grp-b-22 (F051, E3-S1 AC-3): `list_versions` returns all versions ascending, none deleted.
  - Command: `cd backend && uv run pytest -q tests/unit/test_plan_repository.py::test_list_versions_returns_all_versions_in_ascending_order`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-23 (F052, E3-S1 AC-4): Direct mutation of published version's price fails.
  - Command: `cd backend && uv run pytest -q tests/unit/test_plan_repository.py::test_direct_update_of_a_published_versions_price_is_rejected`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-24 (F067, E4-S1 AC-1): No `update_billing_record`/`delete_billing_record` function defined.
  - Command: `cd backend && grep -n 'def update_billing_record\|def delete_billing_record' src/app/repository/billing_repository.py || echo NONE_FOUND`
  - Actual: `NONE_FOUND`. Matches expected.

- [PASS] grp-b-25 (F068, E4-S1 AC-2): Monetary columns round-trip as exact Decimal.
  - Command: `cd backend && uv run pytest -q tests/unit/test_billing_repository.py::test_monetary_columns_round_trip_as_exact_decimal`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-26 (F069, E4-S1 AC-3): Raw UPDATE/DELETE against `billing_records` rejected via trigger.
  - Command: `cd backend && uv run pytest -q tests/unit/test_billing_repository.py::test_direct_update_of_a_billing_record_is_rejected tests/unit/test_billing_repository.py::test_direct_delete_of_a_billing_record_is_rejected`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-27 (F070, E4-S1 AC-4): Two billing records for same subscription both retrievable.
  - Command: `cd backend && uv run pytest -q tests/unit/test_billing_repository.py::test_two_billing_records_for_the_same_subscription_both_remain_retrievable`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-28 (F090, E5-S1 AC-1): No update/delete function for state transitions; raw UPDATE/DELETE rejected.
  - Command: `cd backend && uv run pytest -q tests/unit/test_state_transition_repository.py::test_direct_update_of_a_state_transition_is_rejected tests/unit/test_state_transition_repository.py::test_direct_delete_of_a_state_transition_is_rejected`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-29 (F091, E5-S1 AC-2): `close_port_out_event` sets status/closed_at without deleting; `get_active_port_out_event` returns None after close.
  - Command: `cd backend && uv run pytest -q tests/unit/test_port_out_repository.py::test_close_port_out_event_sets_status_and_closed_at_without_deleting_the_row tests/unit/test_port_out_repository.py::test_get_active_port_out_event_returns_none_after_the_event_is_closed`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-30 (F092, E5-S1 AC-3): Three appended state transitions all retrievable in chronological order.
  - Command: `cd backend && uv run pytest -q tests/unit/test_state_transition_repository.py::test_three_appended_transitions_remain_retrievable_in_chronological_order`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-31 (F093, E5-S1 AC-4): `create_port_out_event` stores `requested_at` + exact 7-day cooling end.
  - Command: `cd backend && uv run pytest -q tests/unit/test_port_out_repository.py::test_create_port_out_event_stores_requested_at_and_seven_day_cooling_end`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-32 (F112, E6-S1 AC-1): No update/delete function for CSR overrides; raw UPDATE/DELETE rejected.
  - Command: `cd backend && uv run pytest -q tests/unit/test_csr_override_repository.py::test_direct_update_of_a_csr_override_is_rejected tests/unit/test_csr_override_repository.py::test_direct_delete_of_a_csr_override_is_rejected`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-33 (F113, E6-S1 AC-2): Every CSROverride stores non-null actor/reason_code/timestamp.
  - Command: `cd backend && uv run pytest -q tests/unit/test_csr_override_repository.py::test_every_override_has_non_null_actor_reason_code_and_timestamp`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-34 (F114, E6-S1 AC-3): Two overrides for same subscription both independently retrievable.
  - Command: `cd backend && uv run pytest -q tests/unit/test_csr_override_repository.py::test_two_overrides_for_the_same_subscription_both_remain_retrievable`
  - Actual: `1 passed`, exit 0. Matches expected.

- [PASS] grp-b-35 (F127, E7-S1 AC-1): Repository exposes activation_funnel_counts/monthly_churn_rate/plan_mix_distribution/arpu_trend.
  - Command: `cd backend && uv run pytest -q tests/unit/test_reporting_repository.py`
  - Actual: `11 passed`, exit 0. Matches expected.

- [PASS] grp-b-36 (F128, E7-S1 AC-2): Activation funnel stages monotonically non-increasing.
  - Command: `cd backend && uv run pytest -q tests/unit/test_reporting_repository.py::test_activation_funnel_counts_are_monotonically_non_increasing tests/unit/test_reporting_repository.py::test_activation_funnel_middle_stages_equal_activated_given_no_partial_signal`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-37 (F129, E7-S1 AC-3): Monthly churn rate divides churned count by active base at month start.
  - Command: `cd backend && uv run pytest -q tests/unit/test_reporting_repository.py::test_monthly_churn_rate_divides_churned_count_by_active_base_at_month_start tests/unit/test_reporting_repository.py::test_monthly_churn_rate_is_zero_when_active_base_at_month_start_is_zero`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-38 (F130, E7-S1 AC-4): All returned monetary aggregates are Decimal, never float.
  - Command: `cd backend && uv run pytest -q tests/unit/test_reporting_repository.py::test_monthly_churn_rate_values_are_decimal tests/unit/test_reporting_repository.py::test_arpu_trend_averages_charges_total_per_month_as_decimal`
  - Actual: `2 passed`, exit 0. Matches expected.

- [PASS] grp-b-39-full-suite (cross-cutting, feature: null): Full backend suite + ruff + mypy clean together.
  - Command: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
  - Actual: `129 passed` in 0.50s; `All checks passed!` (ruff); `Success: no issues found in 41 source files` (mypy), exit 0. Matches expected exactly.

- [PASS] grp-b-40-coverage (cross-cutting, feature: null): 100% statement coverage.
  - Command: `cd backend && uv run pytest -q --cov=app --cov-report=term-missing`
  - Actual: `TOTAL 546 0 100%` (546 statements, 0 missing), `129 passed`, exit 0. Matches expected (`TOTAL 100% (546 or more statements, 0 missing)`).

## Architecture Checks — Named Checks

- [PASS] **layering** — Grep-verified for every Group B file:
  - Types (`src/app/types/*.py`, incl. new `auth.py`): `grep -nE '^(from|import)[[:space:]]+app\.(config|repository|service|api)' src/app/types/*.py` -> `NONE_FOUND`.
  - Config (`src/app/config/*.py`, incl. new `jwt_*` fields in `settings.py`): `grep -nE '^(from|import)[[:space:]]+app\.(repository|service|api)' src/app/config/*.py` -> `NONE_FOUND`.
  - Repository (all 9 Group B repository modules, incl. new `user_repository.py`): `grep -rnE '^(from|import)[[:space:]]+app\.(service|api)' src/app/repository/*.py` -> `NONE_FOUND`.
  - Service (`logging_service.py`, `auth_service.py`): `grep -rnE '^(from|import)[[:space:]]+app\.api' src/app/service/*.py` -> `NONE_FOUND` (no API imports).
  - `lib/pii_mask.py`: `grep -nE '^(from|import)[[:space:]]+app\.(repository|service|api)' src/app/lib/pii_mask.py` -> `NONE_FOUND`.
  - `api/deps.py` (new): imports confirmed to be `app.config.settings`, `app.service.auth_service`, `app.types.auth`, `app.types.enums`, `app.types.exceptions` only — consistent with API importing Config+Service+Types (one-way, no upward violation).
  - No violations found anywhere.

- [PASS] **typing** — `cd backend && uv run mypy --strict src/` -> `Success: no issues found in 41 source files` (exit 0), matching the file count seen in grp-b-39/grp-b-40. `grep -rn "\bAny\b" src/` -> `NONE_FOUND` (no `Any` usage anywhere in `backend/src`).

- [PASS] **folder_structure** — Every file listed in `specs/design/component-map.md` for E1-S3, E1-S4, E1-S5, E2-S1, E3-S1, E4-S1, E5-S1, E6-S1, E7-S1 exists on disk (28 paths checked individually with `[ -f ... ]`, all `OK`, zero `MISSING`):
  - E1-S3: `src/app/lib/pii_mask.py`, `src/app/service/logging_service.py`, `tests/unit/test_logging_service.py`
  - E1-S4: `src/app/types/auth.py`, `src/app/repository/user_repository.py`, `src/app/service/auth_service.py`, `src/app/api/deps.py`, `tests/integration/test_auth.py`
  - E1-S5: `src/app/api/routers/health_router.py`, `src/app/api/main.py`, `tests/integration/test_health.py`
  - E2-S1: `src/app/repository/subscriber_repository.py`, `src/app/repository/dealer_repository.py`, `src/app/repository/schema.sql`, `tests/unit/test_subscriber_repository.py`, `tests/unit/test_dealer_repository.py`
  - E3-S1: `src/app/repository/plan_repository.py`, `tests/unit/test_plan_repository.py`
  - E4-S1: `src/app/repository/billing_repository.py`, `tests/unit/test_billing_repository.py`
  - E5-S1: `src/app/repository/state_transition_repository.py`, `src/app/repository/port_out_repository.py`, `tests/unit/test_state_transition_repository.py`, `tests/unit/test_port_out_repository.py`
  - E6-S1: `src/app/repository/csr_override_repository.py`, `tests/unit/test_csr_override_repository.py`
  - E7-S1: `src/app/repository/reporting_repository.py`, `tests/unit/test_reporting_repository.py`
  - **Doc-drift note (not a failure, per contract's explicit instruction)**: `src/app/repository/schema.py` exists on disk (introduced in E1-S4, houses `apply_schema()`) but is not listed anywhere in `component-map.md`, which currently only mentions `schema.sql`. The contract's `folder_structure` description pre-flags exactly this drift and directs it be noted rather than failed, since the story ACs (not the doc) are authoritative. Flagged here for `component-map.md` to be updated in a future doc pass.

- [PASS] **env_vars** — `settings.py` gained `jwt_secret_key` (default `"dev-only-insecure-secret-change-in-production"`, explicitly commented as dev-only), `jwt_algorithm` (default `"HS256"`), `jwt_expiry_minutes` (default `60`). Live-verified (not just read from source):
  - With `JWT_SECRET_KEY`/`JWT_ALGORITHM`/`JWT_EXPIRY_MINUTES` set in the environment, `get_settings()` returns the overridden values exactly (`test-override-value`, `HS512`, `15`).
  - With none set, `get_settings()` returns the three documented defaults exactly.
  - Same `pydantic_settings.BaseSettings` env-var-per-field pattern as E1-S2's existing `db_path`/`kyc_stub_verified`/`mnp_stub_success`/`dealer_fail_code` fields (already verified passing in Group A's grp-a-06/grp-a-09). Consistent.

- [PASS] **migrations** (`required: true` for this group) — `schema.sql` introduced in E1-S4 and incrementally grown by E2-S1/E3-S1/E4-S1/E5-S1/E6-S1 (confirmed via grep: `CREATE TABLE IF NOT EXISTS` x7, `CREATE UNIQUE INDEX IF NOT EXISTS` x1, `CREATE TRIGGER IF NOT EXISTS` x8, `INSERT OR IGNORE` x1 for the dealer seed). Live-verified idempotency (not just read from source): calling `apply_schema()` three times in a row against the same in-memory SQLite connection raised no error, and `dealer_master` row count stayed at exactly 6 (5 valid + `DEALER-FAIL` sentinel) across all three calls — no duplicate-insert drift.

## Playwright Checks

- [SKIP] Not applicable — `playwright_checks` is intentionally empty for Group B per the contract's `note_for_evaluator` (TestClient-based integration tests are treated as equivalent evidence; no long-running server/browser target exists yet).

## API Checks

- [SKIP] Not applicable — `api_checks` is intentionally empty for Group B per the contract's `note_for_evaluator`, for the same reason as Group A.

## Design Checks

- [SKIP] Not applicable — no UI exists yet for Group B.

## Features Updated

38 features (F011–F029, F049–F052, F067–F070, F090–F093, F112–F114, F127–F130) added to `/home/ankit/AI-native-capstone/features.json` (previously containing only F001–F010 from Group A), each copying `id`/`category`/`story`/`group`/`description`/`steps` verbatim from `specs/features.json` and setting `passes`/`last_evaluated`/`failure_reason`/`failure_layer` per this evaluation. 36 of the 38 have `last_evaluated: 2026-09-30T05:16:09Z` (unchanged since the initial pass, which they passed on the first try). F019 and F020 have `last_evaluated: 2026-09-30T05:22:48Z` (the re-verification timestamp, reflecting the corrected-contract re-run documented above); both now show `passes: true`, `failure_reason: null`, `failure_layer: null`.

- F011: PASS
- F012: PASS
- F013: PASS
- F014: PASS
- F015: PASS
- F016: PASS
- F017: PASS
- F018: PASS
- F019: PASS (re-verified 2026-09-30T05:22:48Z against corrected contract expected "4 passed"; see "Contract Correction Between Evaluation Passes" above)
- F020: PASS (re-verified 2026-09-30T05:22:48Z against corrected contract expected "8 passed"; see "Contract Correction Between Evaluation Passes" above)
- F021: PASS
- F022: PASS
- F023: PASS
- F024: PASS
- F025: PASS
- F026: PASS
- F027: PASS
- F028: PASS
- F029: PASS
- F049: PASS
- F050: PASS
- F051: PASS
- F052: PASS
- F067: PASS
- F068: PASS
- F069: PASS
- F070: PASS
- F090: PASS
- F091: PASS
- F092: PASS
- F093: PASS
- F112: PASS
- F113: PASS
- F114: PASS
- F127: PASS
- F128: PASS
- F129: PASS
- F130: PASS

## Note on the Sprint Contract

**Resolved.** The initial pass identified that two of the 40 `test_checks` entries (`grp-b-09`, `grp-b-10`) had expected pytest-summary strings ("3 passed", "7 passed") that did not match what the actual, correctly-behaving test suite produced ("4 passed", "8 passed") — root-caused to `test_csr_or_admin_can_access_their_scoped_endpoint_without_403` (`backend/tests/integration/test_auth.py:135-136`) being `@pytest.mark.parametrize("role", [Role.CSR, Role.ADMIN])`, which pytest collects as 2 items rather than the 1 the contract's expected-count arithmetic assumed. This was also flagged as internally inconsistent with the same contract's `grp-b-39-full-suite` aggregate (`129 passed`), which was only reachable if `test_auth.py` already contributed 8, not 7. No test ever failed and no code defect was found — this was purely a sprint-contract authoring slip.

The coordinator independently reached the same root-cause diagnosis and corrected `sprint-contracts/group-b.json` in place (`grp-b-09.expected` -> `"4 passed"`, `grp-b-10.expected` -> `"8 passed"`, descriptions updated to note the parametrization; nothing else in the contract changed). This evaluator re-ran both commands verbatim against the corrected contract and confirmed exact matches (see above). The contract was not modified by this evaluator at any point; the correction was made by the coordinator between the two evaluation passes, as instructed.
