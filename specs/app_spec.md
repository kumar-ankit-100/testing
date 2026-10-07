# App Spec — TelcoLane

Root specification. Maps the capstone brief's AC-01–AC-10 / NFR-01–NFF-08 numbering to this repository's actual implementation and tests. Per-feature detail lives in `specs/<feature>_spec.md`; this file is the index and the NFR/architecture-wide criteria that don't belong to one feature alone.

## Acceptance Criteria Index

| AC | Criterion | Feature spec | Primary implementation |
|---|---|---|---|
| AC-01 | Subscriber self-registration → PENDING_KYC | `specs/activation_spec.md` | `backend/src/app/service/registration_service.py`, `POST /api/subscribers/register` |
| AC-02 | Lifecycle state machine, invalid transitions raise | `specs/activation_spec.md`, `specs/suspension_spec.md`, `specs/port-out_spec.md` | `backend/src/app/types/fsm.py` (one shared transition table for all five services below) |
| AC-03 | Versioned, immutable plan catalog | `specs/plan-catalog_spec.md` | `backend/src/app/service/plan_catalog_service.py` |
| AC-04 | Plan upgrade/downgrade, minimum-tenure rule | `specs/plan-change_spec.md` | `backend/src/app/service/plan_change_service.py` |
| AC-05 | Pro-rata billing on mid-cycle change | `specs/plan-change_spec.md` | `backend/src/app/service/billing_calculation_service.py` |
| AC-06 | Suspend/resume | `specs/suspension_spec.md` | `backend/src/app/service/suspend_resume_service.py` |
| AC-07 | 7-day port-out cooling period | `specs/port-out_spec.md` | `backend/src/app/service/port_out_service.py` |
| AC-08 | Rule-based activation (KYC/dealer/MNP stubs) | `specs/activation_spec.md` | `backend/src/app/service/activation_service.py` |
| AC-09 | CSR override, audited | `specs/csr-override_spec.md` | `backend/src/app/service/csr_override_service.py` |
| AC-10 | Admin reporting | `specs/reports_spec.md` | `backend/src/app/service/reporting_service.py` |

## Non-Functional Requirements

| NFR | Requirement | How it's enforced |
|---|---|---|
| NFR-01 | Decimal, never float | Every money-typed field across `types/billing.py`, `types/plan.py` is `Decimal`; `billing_calculation_service.py` and `plan_change_service.py` never import `float` for a monetary value. Stored as canonical `TEXT` in SQLite, reconstructed on read. |
| NFR-02 | Append-only history | `plan_versions` (once published), `state_transitions`, `billing_records`, `port_out_events`, `csr_overrides` tables each have `BEFORE UPDATE`/`BEFORE DELETE` triggers in `backend/src/app/repository/schema.sql`; the repository layer exposes no update/delete function for any of them. |
| NFR-03 | PII masked in logs | `backend/src/app/service/logging_service.py`'s `PII_FIELD_NAMES` set masks `mobile_number`, `aadhaar_ref`, `pan_ref`, `identity_proof_ref` before any JSON log line is serialized. No other module performs raw log serialization. |
| NFR-04 | Controller-layer auth, role separation, subscriber data isolation | `backend/src/app/api/deps.py`: `current_principal`, `require_role`, `require_own_subscriber`. Every router depends on one of these; subscriber-role tokens are rejected (403) against any subscription_id that doesn't match their own. |
| NFR-05 | Append-only migrations | `schema.sql` uses only `CREATE TABLE IF NOT EXISTS` / `CREATE TRIGGER IF NOT EXISTS` / `INSERT OR IGNORE` — additive only, applied idempotently at app startup (`backend/src/app/repository/schema.py`). |
| NFR-06 | Structured JSON logs, masked subscriber_id | Same `logging_service.py` as NFR-03; every log call emits one JSON object with `timestamp`/`level`/`message` plus a masked `context`. |
| NFR-07 | Health endpoint < 1s | `GET /health` — no DB round-trip, no auth (`backend/src/app/api/routers/health_router.py`), verified by `tests/integration/test_health.py`. |
| NFR-08 | Architecture invariants as tests | Published-plan immutability: `tests/unit/test_plan_repository.py`'s direct-SQL-bypass tests. No double-ACTIVE-per-mobile: the partial unique index `idx_subscriptions_active_mobile`, exercised by `tests/unit/test_subscriber_repository.py` and `tests/unit/test_activation_service.py`'s race test. Pro-rata invariant: `tests/unit/test_billing_calculation_service.py`'s boundary-date table, including the leap-year case. |

## Layering

`Types → Config → Repository → Service → API → UI`, one-way imports only, enforced by `.claude/hooks/check-architecture.js` and documented in `.claude/architecture.md`. See `docs/architecture.md` for the full diagram.

## Stack

Backend: Python 3.12, FastAPI, `uv`, `ruff`, `mypy --strict`, `pytest` + `pytest-cov`. Frontend: TypeScript, React (Vite), `npm`, `eslint`, `tsc`, `vitest`, Playwright. Database: SQLite (WAL mode). See `CLAUDE.md` for exact commands.
