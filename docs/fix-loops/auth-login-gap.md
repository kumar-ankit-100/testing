# Fix Loop: auth-login endpoint gap

## Detected

During Group E's sprint-contract evaluation (2026-09-30), while independently re-verifying the generator's implementation report, the coordinator asked "is this a real gap or a code defect?" and ran:

```
grep -rl "auth/login\|auth_router\|POST /api/auth/login" specs/stories/*.md
```

Zero matches. `specs/design/api-contracts.md` has documented `POST /api/auth/login` since the Phase 3 design pass; `E1-S4` (Group B) built auth dependencies (`require_role`, `current_principal`) that assume a token exists; `E3-S3` (Group D) gated a real router behind `require_role`. No story anywhere ever built the endpoint that issues the token. The evaluator for Group E independently confirmed the same finding and flagged it in `specs/reviews/evaluator-report-group-e.md` without it causing a FAIL, since no Group E acceptance criterion required the login endpoint to exist.

## Reproduced

```
curl -s -X POST http://localhost:8000/api/auth/login -d '{"username":"admin_raj","password":"x"}'
# 404 — the route never existed
```

Confirmed via `tests/integration/test_auth.py` and `tests/integration/test_plan_api.py` (both already evaluator-approved, Groups B and D): both minted bearer tokens directly via `auth_service.create_access_token()` in test setup rather than through any HTTP call — proof the suite had never once exercised a real login, only the downstream token-verification logic.

## Fixed

User decision (2026-10-01): spec-first. Added `specs/stories/E1-S6.md` (6 ACs in Given-When-Then form: staff login, subscriber login, generic 401 on invalid credentials with no user-enumeration signal, seeded demo users with hashed passwords, PII-masked login logging, end-to-end 403 through a real-issued token) and extended `specs/stories/E2-S5.md` with two new ACs (login page, role-based route guard). Updated `specs/stories/dependency-graph.md` and `specs/features.json` (+8 features, F154–F161) to match, committed on `spec/add-auth-login-story` and merged `--no-ff` into `develop` before any implementation started.

Implementation (strict TDD, tests first):
- `backend/src/app/api/routers/auth_router.py` + `auth_schemas.py` — staff and subscriber login paths, reusing `E1-S4`'s existing `create_access_token`/`decode_access_token` rather than inventing a second token format.
- `auth_service.hash_password`/`verify_password` — PBKDF2-HMAC-SHA256, 390,000 iterations, random salt, `hmac.compare_digest` for the comparison. A precomputed dummy hash is checked when the username doesn't exist, so `verify_password()` always runs — closing the timing side-channel as well as the response-shape one, which the story's AC asked for but didn't spell out that specific mechanism.
- `schema.sql` seeds exactly one demo user per CSR/ADMIN/DEALER role with a real (non-plaintext) hash.
- `tests/integration/test_auth.py` (Group B) and `tests/integration/test_plan_api.py` (Group D) migrated to obtain tokens through the real endpoint instead of minting them — the highest-risk part of this fix, since both files were already evaluator-approved.
- Frontend: `config/authStorage.ts`, `api/authApi.ts`, `service/useAuth.ts`, `ui/components/RouteGuard.tsx`, `ui/pages/LoginPage.tsx`. A real bug was caught before any test was written for it: `RouteGuard` and `LoginPage` each independently calling `useAuth()` would hold separate, isolated `useState` copies, so a successful login would never be visible to the guard. Fixed by lifting the single `useAuth()` call to `App.tsx` and passing state down as props.

## Validated

Coordinator independently re-ran everything before accepting any verdict (not just reading the generator's report):
- Backend: `255 passed` (was 237 before this story), `ruff check .` clean, `mypy src/` clean (54 files), `100%` coverage (1111/1111 statements).
- Frontend: `26 passed` across 7 files (was 12), lint/typecheck/build all clean.
- Regression check, run in isolation: `tests/integration/test_auth.py tests/integration/test_plan_api.py` → `20 passed` (8 + 12) — zero regressions in the two migrated, already-approved files.
- Independently re-confirmed the generator's two security claims by reading the source directly rather than trusting the report: `hmac.compare_digest` is genuinely used (not `==`), and the three seeded users' `password_hash` values are genuinely salted PBKDF2 output, not plaintext.
- Dispatched the `evaluator` agent against `sprint-contracts/group-e1s6.json` (8 features, 12 checks, every expected count pre-verified via isolated `pytest --collect-only`/`vitest` runs before writing the contract). Evaluator independently re-confirmed the same two security claims on its own before returning VERDICT: PASS.

## PR

Branch `feat/e1-s6-auth-login` → `--no-ff` merge into `develop` as `125d358` (implementation); branch `eval/...` (contract + evaluator output) to follow this trace's own commit. No direct commits to `develop` or `main` at any point in this loop.

## Process change

Recorded in `docs/knowledge-deposits.md` entry 1: added a contract-to-story coverage check to the `/design` skill's pre-approval gate (`.claude/skills/design/SKILL.md`), so a future endpoint documented in `api-contracts.md` with zero owning stories blocks the design gate instead of shipping silently for four build groups.
