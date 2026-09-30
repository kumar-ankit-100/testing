# Evaluator Report — Group D

Date: 2026-09-30T16:55:32Z
VERDICT: PASS

Stories: E2-S3 (Rule-based activation engine), E3-S3 (Plan catalog admin API endpoints)
Features: F034, F035, F036, F037, F038, F039, F058, F059, F060, F061, F062

## Scope Note

Per `sprint-contracts/group-d.json`'s `note_for_evaluator`, `api_checks` and `playwright_checks` are intentionally empty for this group — E3-S3's router is exercised via FastAPI's in-process `TestClient` in `tests/integration/test_plan_api.py`, treated as equivalent evidence to a live HTTP call at this per-group evaluation stage. The Docker/health-check step was skipped as instructed. Only `contract.architecture_checks` (including all 14 `test_checks` entries) was evaluated.

## Test Checks (contract.architecture_checks.test_checks)

All commands run exactly as specified in the contract via Bash from `backend/`.

- [PASS] grp-d-01 (F034, E2-S3 AC-1) — `test_activation_with_all_checks_passing_transitions_to_active_and_appends_transition` → 1 passed (expected: 1 passed)
- [PASS] grp-d-02 (F035, E2-S3 AC-2) — `test_activation_with_unverified_kyc_is_rejected_and_subscription_remains_pending` → 1 passed (expected: 1 passed)
- [PASS] grp-d-03 (F036, E2-S3 AC-3) — `test_activation_with_dealer_fail_sentinel_is_rejected_and_subscription_remains_pending` + `test_activation_with_an_unknown_dealer_code_is_also_rejected` → 2 passed (expected: 2 passed)
- [PASS] grp-d-04 (F037, E2-S3 AC-4) — `test_activation_with_mnp_fail_flag_is_rejected_and_subscription_remains_pending` → 1 passed (expected: 1 passed)
- [PASS] grp-d-05 (F038, E2-S3 AC-5) — `test_activating_an_already_active_subscription_raises_invalid_state_exception` → 1 passed (expected: 1 passed)
- [PASS] grp-d-06 (F039, E2-S3 AC-6) — `test_two_pending_registrations_for_the_same_mobile_only_one_reaches_active` → 1 passed (expected: 1 passed)
- [PASS] grp-d-07 (F058, E3-S3 AC-1) — `test_create_plan_version_returns_201_with_draft` → 1 passed (expected: 1 passed)
- [PASS] grp-d-08 (F059, E3-S3 AC-2) — `test_publish_plan_version_returns_200_with_published_true` → 1 passed (expected: 1 passed)
- [PASS] grp-d-09 (F060, E3-S3 AC-3) — `test_put_on_an_already_published_version_returns_409_with_immutability_message` → 1 passed (expected: 1 passed)
- [PASS] grp-d-10 (F061, E3-S3 AC-4) — `test_get_plan_list_returns_full_version_history_including_superseded` → 1 passed (expected: 1 passed)
- [PASS] grp-d-11 (F062, E3-S3 AC-5) — `test_non_admin_receives_403_for_create_and_list` + `test_non_admin_receives_403_for_publish` + `test_non_admin_receives_403_for_update` → 4 passed (expected: 4 passed). Independently verified via `pytest -v --collect-only tests/integration/test_plan_api.py::test_non_admin_receives_403_for_create_and_list`: confirms the parametrization collects exactly 2 items (`[post--json_body0]`, `[get--None]`), so 2 (parametrized) + 1 (publish) + 1 (update) = 4 is correct, not a contract-authoring slip.
- [PASS] grp-d-12-full-suite (cross-cutting gate) — `pytest -q && ruff check . && mypy src/` → 196 passed, 1 warning (StarletteDeprecationWarning re: httpx/testclient, non-blocking); ruff: "All checks passed!"; mypy: "Success: no issues found in 47 source files" (expected: 196 passed; ruff clean; mypy clean on 47 source files)
- [PASS] grp-d-13-coverage (cross-cutting gate) — `pytest -q --cov=app --cov-report=term-missing` → TOTAL 823 statements, 0 missing, 100% coverage (expected: TOTAL 100%, 823+ statements, 0 missing)
- [PASS] grp-d-14-no-stray-db (cross-cutting gate) — `find backend -maxdepth 2 -name '*.db' -not -path '*/.mypy_cache/*'; echo DONE` → output was exactly `DONE` with no `.db` path printed before it (expected: no stray DB file). Confirms the E3-S3 lifespan (first to touch disk on every `TestClient(create_app())` call) does not leak a real SQLite file at the default `DB_PATH` during the test run.

## Architecture Checks

- [PASS] **layering** (required) — `backend/src/app/service/activation_service.py` imports only from `app.config.settings`, `app.repository.*`, and `app.types.*` (Types/Config/Repository); no `app.api` or UI import. `backend/src/app/api/routers/plan_router.py` imports from `app.api.deps`, `app.api.schemas.plan_schemas`, `app.repository.plan_repository`, `app.service.plan_catalog_service`, `app.types.auth`, `app.types.enums` (Types/Config/Repository/Service); no UI import. `backend/src/app/api/schemas/plan_schemas.py` imports only `app.types.enums`/`app.types.plan` plus stdlib/pydantic. Zero upward violations confirmed by direct file inspection of import statements.
- [PASS] **typing** (required) — `uv run mypy src/` → "Success: no issues found in 47 source files" (run as part of grp-d-12). No `Any` usage found in the two new/modified Group D files on inspection.
- [PASS] **folder_structure** (required) — cross-referenced against `specs/design/component-map.md` (E2-S3 and E3-S3 rows) and verified on disk:
  - `backend/src/app/service/activation_service.py` exists, with matching `backend/tests/unit/test_activation_service.py`
  - `backend/src/app/api/routers/plan_router.py` and `backend/src/app/api/schemas/plan_schemas.py` exist, with matching `backend/tests/integration/test_plan_api.py`
  - `subscriber_repository.py` contains both `get_subscription_by_subscriber_id` (line 104) and `activate_subscription` (line 119)
  - `plan_repository.py` contains both `get_plan_version_by_id` (line 114) and `list_all_plan_versions` (line 128)
  - `api/deps.py` contains `get_db_connection` (line 71)
  - `api/error_handlers.py` maps `PlanVersionImmutableError` to HTTP 409 with `ReasonCode.PLAN_VERSION_IMMUTABLE` (lines 14, 33-37)
  - `api/main.py` calls `register_exception_handlers(app)` (line 41) and `app.include_router(plan_router)` (line 43)
  - `types/exceptions.py` defines `ActivationRejectedError` (line 66)
  All claims in the contract's `folder_structure` description verified true on disk; no discrepancies found.
- [N/A] **env_vars** (`required: false`) — contract states no new environment variables introduced in Group D; not evaluated as a pass/fail gate per the contract's `required: false` flag.
- [N/A] **migrations** (`required: false`) — contract states no `schema.sql` changes in Group D; not evaluated as a pass/fail gate per the contract's `required: false` flag.

## API Checks

Not applicable — `api_checks` is intentionally empty per `note_for_evaluator`; E3-S3's HTTP surface is covered by in-process `TestClient` integration tests counted above in `test_checks` (grp-d-07 through grp-d-11).

## Playwright Checks

Not applicable — `playwright_checks` is intentionally empty per `note_for_evaluator`. No frontend surface was introduced in Group D.

## Design Checks

Not applicable — no `design_checks` in this contract.

## Features Updated

Updated in `/home/ankit/AI-native-capstone/features.json` (root, live harness state — previously-existing 62 entries left untouched, these 11 appended):

- F034: PASS
- F035: PASS
- F036: PASS
- F037: PASS
- F038: PASS
- F039: PASS
- F058: PASS
- F059: PASS
- F060: PASS
- F061: PASS
- F062: PASS

All 11 set with `passes: true`, `last_evaluated: "2026-09-30T16:55:32Z"`, `failure_reason: null`, `failure_layer: null`. `id`/`category`/`story`/`group`/`description`/`steps` copied verbatim from `specs/features.json`.

## Summary

All 14 `test_checks` entries in `contract.architecture_checks` pass exactly as specified, with no divergence from expected output requiring further investigation (the one parametrized-count entry, grp-d-11, was independently re-verified via an isolated `--collect-only` run and confirmed correct). All 3 required named architecture checks (layering, typing, folder_structure) pass on direct inspection of source files against `specs/design/component-map.md`. `env_vars` and `migrations` are `required: false` and correctly marked N/A. No stray SQLite file was left at the default DB_PATH after the full suite ran (grp-d-14), confirming the prior test-isolation bug fix reported by the generator holds. Overall verdict: **PASS**.
