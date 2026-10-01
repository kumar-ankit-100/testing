# Knowledge Deposits

Recurring mistakes and the process changes adopted to stop repeating them. Append-only; each entry stays even after the fix, so the reasoning survives.

---

## 1. Contract endpoints must map to a story, or they silently never get built

**What happened:** `specs/design/api-contracts.md` documented `POST /api/auth/login` from the Phase 3 design pass onward. `E1-S4` (Group B) built the auth *dependencies* (`require_role`, `current_principal`, JWT decode) that assume a token exists, and `E3-S3` (Group D) gated a real router behind `require_role`. Neither story — nor any story in `/spec`'s original 32-story decomposition — ever built the endpoint that actually issues a token. The gap went undetected through Groups B, C, D, and E because every integration test minted its own token directly via `auth_service.create_access_token()` in test setup, which is valid test isolation but meant the suite never once proved a real client could reach an authenticated route. It surfaced only when the Group E evaluator (asked to look for exactly this class of thing) read the contract and dependency graph side by side.

**Root cause:** `/spec`'s story decomposition was derived from the BRD's acceptance criteria and NFRs, not from a systematic pass over every endpoint `api-contracts.md` defines. A contract endpoint with no NFR/AC directly naming it (login is infrastructure, not a business rule) had no natural story to attach to, so it was never allocated to an epic.

**Fix applied:** Added `E1-S6` (`specs/stories/E1-S6.md`) after the gap was found, plus two new ACs on `E2-S5` for the frontend side (login page + route guard). Migrated the two already-evaluator-approved test files that had been working around the gap (`test_auth.py`, `test_plan_api.py`) to use the real endpoint, so the suite now actually proves the contract holds rather than assuming it.

**Process change — add a planner check:** Before a spec is marked approved, diff every path in `api-contracts.md`'s `paths` object against every story's description/ACs across `specs/stories/*.md`. An endpoint with zero stories mentioning its path (or router file) is a planner-level FAIL, not a warning — the same rigor already applied to "every AC must map to ≥1 feature" in the spec skill's quality gates should apply symmetrically to "every contract endpoint must map to ≥1 story." This is a `planner`-agent-time check (during `/spec`), not an `evaluator`-time one, since by evaluator-time the group doing the orphaned work is already mid-flight.

**How to apply:** Any future endpoint added to `api-contracts.md` — including ones that feel like "infrastructure, not a feature" (auth, health, CORS preflight, etc.) — gets the same contract-to-story diff before the spec is approved. Don't special-case infrastructure endpoints as exempt; this gap was exactly that special-casing.
