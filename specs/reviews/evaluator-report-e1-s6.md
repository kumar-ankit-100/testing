# Evaluator Report — Group E1-S6 (fix-loop: auth login endpoint)

Date: 2026-10-01T07:45:00Z
VERDICT: PASS

## Context

This is a fix-loop evaluation closing the auth-login gap identified during Group E's evaluation. It
also modified two already-evaluator-approved test files (`tests/integration/test_auth.py` from Group B
and `tests/integration/test_plan_api.py` from Group D) to obtain tokens through the real login endpoint
instead of minting them directly. Per the contract's `note_for_evaluator`, the regression-check entry
(`grp-e1s6-09-regression-check`) received extra scrutiny.

## Test Checks (12/12 PASS)

- [PASS] grp-e1s6-01 (F154, AC-1) — `test_staff_login_with_valid_csr_credentials_returns_token_with_role_and_subject`, `test_staff_login_with_valid_admin_credentials_returns_200` → 2 passed ✓
- [PASS] grp-e1s6-02 (F155, AC-2) — pre-registration + post-registration subscriber login tests → 2 passed ✓
- [PASS] grp-e1s6-03 (F156, AC-3) — wrong password / unknown username both 401 with identical shape → 2 passed ✓
- [PASS] grp-e1s6-04 (F157, AC-4) — hash/verify password unit tests + seeded-user repository tests → 6 passed ✓
- [PASS] grp-e1s6-05 (F158, AC-5) — login never logs raw password / masks mobile number → 2 passed ✓
- [PASS] grp-e1s6-06 (F159, AC-6) — `test_subscriber_requesting_another_subscribers_data_receives_403` (real-issued token) → 1 passed ✓
- [PASS] grp-e1s6-07 (F160, AC-5 of E2-S5) — `LoginPage.test.tsx` + `useAuth.test.tsx` → Test Files 2 passed (2); Tests 8 passed (8) ✓ (exact match)
- [PASS] grp-e1s6-08 (F161, AC-6 of E2-S5) — `RouteGuard.test.tsx` → Test Files 1 passed (1); Tests 4 passed (4) ✓ (exact match)
- [PASS] grp-e1s6-09-regression-check (cross-cutting) — `pytest tests/integration/test_auth.py tests/integration/test_plan_api.py` → **20 passed**, exactly matching the contract's expected count (8 from test_auth.py + 12 from test_plan_api.py). No regression in previously evaluator-approved Group B/D test files. ✓
- [PASS] grp-e1s6-10-backend-full-suite — `pytest -q && ruff check . && mypy src/` → 255 passed; ruff "All checks passed!"; mypy "Success: no issues found in 54 source files" — exact match ✓
- [PASS] grp-e1s6-11-backend-coverage — `pytest --cov=app --cov-report=term-missing` → TOTAL 1111 statements, 0 missing, 100% — exact match ✓
- [PASS] grp-e1s6-12-frontend-full-suite — `npm test -- --run && npm run lint && npm run typecheck && npm run build` → Test Files 7 passed (7); Tests 26 passed (26); lint clean; typecheck clean; build succeeded — exact match ✓

## Architecture Checks

- [PASS] **layering** — `auth_router.py` imports only from `app.api.deps`, `app.api.schemas.auth_schemas`, `app.config.settings`, `app.repository.*`, `app.service.auth_service`, `app.service.logging_service`, `app.types.*` — no UI imports. Frontend: `authStorage.ts` is in `config/` (no upward imports observed); `App.tsx` calls `useAuth()` exactly once and passes `isAuthenticated`, `role`, `login` down as props to `RouteGuard`/`LoginPage`, which are documented and verified as not calling `useAuth()` themselves. ✓
- [PASS] **typing** — `mypy src/` → "Success: no issues found in 54 source files"; `npm run typecheck` (tsc --noEmit) → clean, no errors. ✓
- [PASS] **folder_structure** — Verified on disk: `backend/src/app/api/routers/auth_router.py`, `backend/src/app/api/schemas/auth_schemas.py`, `backend/tests/integration/test_auth_login_api.py`, `auth_service.py` contains `hash_password`/`verify_password`. Frontend: `frontend/src/config/authStorage.ts`, `frontend/src/api/authApi.ts`, `frontend/src/service/useAuth.ts`, `frontend/src/ui/components/RouteGuard.tsx`, `frontend/src/ui/pages/LoginPage.tsx` all exist with corresponding test files; `App.tsx` (at `frontend/src/ui/App.tsx`) calls `useAuth()` once. ✓
- [N/A] **env_vars** — not required; no new environment variables added (reuses E1-S4's `jwt_secret_key`/`jwt_algorithm`/`jwt_expiry_minutes`). Not evaluated per contract's `required: false`.
- [PASS] **migrations** — `schema.sql` seeds exactly 3 demo users via idempotent `INSERT OR IGNORE`: `csr_jane`, `admin_raj`, `dealer_priya`, each with a `password_hash` in `pbkdf2_sha256$<iterations>$<salt_hex>$<derived_key_hex>` format — non-plaintext, salted. Verified directly in `backend/src/app/repository/schema.sql`. ✓

## Independent Security Verification — Constant-Time Comparison

Beyond the contract's checks, `backend/src/app/service/auth_service.py`'s `verify_password` function
was inspected directly:

```python
import hmac
...
derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
return hmac.compare_digest(derived, expected)
```

Confirmed: `verify_password` uses `hmac.compare_digest` for the final comparison, not `==`. This is a
genuine constant-time comparison, not merely a functional claim.

## Regression-Check Confirmation

`grp-e1s6-09-regression-check` was run in isolation exactly as specified:
`cd backend && uv run pytest -q tests/integration/test_auth.py tests/integration/test_plan_api.py`
Result: **20 passed** (exact match to contract's expected count), confirming both previously
evaluator-approved files (Group B's `test_auth.py`, Group D's `test_plan_api.py`) continue to pass in
full after being migrated to obtain tokens through the real login endpoint. No regression detected.

## Features Updated

- F154: PASS
- F155: PASS
- F156: PASS
- F157: PASS
- F158: PASS
- F159: PASS
- F160: PASS
- F161: PASS

All 12 required test_checks passed. All 4 required architecture_checks passed (env_vars N/A, not
required). Overall VERDICT: **PASS**.
