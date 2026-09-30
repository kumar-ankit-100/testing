# TelcoLane — System Design

## 1. Overview

TelcoLane is a telecom Subscriber & Plan Lifecycle Management Platform delivered as a single FastAPI backend (Python 3.12, SQLite/WAL) and a single React SPA frontend (TypeScript, Vite). It covers subscriber self-registration and rule-based activation (KYC/dealer/MNP stubbed), a versioned immutable plan catalog, pro-rata plan upgrade/downgrade, suspend/resume, a 7-day port-out cooling period, CSR overrides with audit trail, and admin reporting.

Both backend and frontend follow the same one-way layered architecture defined in `.claude/architecture.md`:

```
Types -> Config -> Repository -> Service -> API -> UI
```

No layer imports from a layer above it. This is enforced by the `check-architecture` hook and mirrored literally in `folder-structure.md`.

## 2. Components

| Component | Technology | Responsibility |
|---|---|---|
| Backend API | FastAPI + Uvicorn | All business logic, persistence, auth, reporting |
| Database | SQLite (WAL mode) | Single-file relational store; append-only tables for ledgers |
| Frontend SPA | React + Vite + TypeScript | Subscriber self-service UI, admin/CSR internal tools |
| Stub integrations | In-process config flags | Deterministic KYC / dealer-code / MNP outcomes — no external network calls |

There is no message queue, cache, or external service in this system. All "integrations" (KYC provider, MNP provider) are stubbed via config flags per E1-S2, so the topology is deliberately a single deployable backend process plus a static frontend bundle — see `deployment.md`.

## 3. Data Flow (representative)

### 3.1 Registration → Activation
```
Subscriber UI --POST /api/subscribers/register--> API --> registration_service
   --> subscriber_repository.create_subscriber (state=PENDING_KYC)
Subscriber UI --POST /api/subscribers/{id}/activate--> API --> activation_service
   --> reads Config stub flags (KYC/MNP) + dealer_repository (dealer_code lookup)
   --> FSM.transition(PENDING_KYC -> ACTIVE) on success
   --> state_transition_repository.append_state_transition (always, pass or fail path logs the attempt outcome as a transition only on success; failures return a reason code without a transition row)
```

### 3.2 Plan change (pro-rata)
```
UI --POST .../plan-change/preview--> plan_change_service
   --> billing_calculation_service (pure Decimal math, no writes)
   <-- previewed amount (no persistence)
UI --POST .../plan-change/commit--> plan_change_service
   --> checks minimum-tenure + ACTIVE state
   --> billing_calculation_service (recompute, same formula)
   --> billing_repository.create_billing_record (append-only)
   --> subscription updated to new plan_version_id
```

### 3.3 Port-out cooling period
```
POST .../port-out --> port_out_service --> FSM(ACTIVE -> PORT_OUT_REQUESTED)
   --> port_out_repository.create_port_out_event(requested_at, cooling_period_end_at = requested_at + 7d)
POST .../port-out/cancel  (before cooling_period_end_at) --> FSM(PORT_OUT_REQUESTED -> ACTIVE), event closed CANCELLED_WITHIN_WINDOW
POST .../port-out/finalize (after cooling_period_end_at)  --> FSM(PORT_OUT_REQUESTED -> PORTED_OUT), event closed FINALIZED
```

### 3.4 CSR override
```
CSR UI --GET /api/csr/exceptions--> csr_router --> lists subscriptions whose latest
   activation/plan-change attempt was rejected and never subsequently succeeded
CSR UI --POST /api/csr/exceptions/{id}/override {reason_code}--> csr_override_service
   --> re-runs the originally-rejected action bypassing only the specific failed rule
   --> on success: mutates state via the same FSM/service path used by the normal flow
   --> always: csr_override_repository.create_csr_override (append-only audit row)
```

## 4. Infrastructure Topology

Local-dev-only per `project-manifest.json` (`deployment.method: local-dev-servers`):

```
┌────────────────────┐        ┌─────────────────────────┐
│  Frontend (Vite)    │ HTTP   │  Backend (Uvicorn)       │
│  localhost:5173      ├───────▶  localhost:8000          │
│  React SPA           │        │  FastAPI app             │
└────────────────────┘        │  SQLite file (WAL mode)  │
                                └─────────────────────────┘
```

`init.sh` bootstraps both processes and polls `/health`. See `deployment.md` for the full pipeline and promotion path to staging/prod.

## 5. Key Design Decisions & Rationale

### 5.1 Table-driven FSM in the Types layer
The subscriber lifecycle (`PENDING_KYC, ACTIVE, SUSPENDED, TERMINATED, PORT_OUT_REQUESTED, PORTED_OUT`) is modeled as a declarative `frozenset[tuple[SubscriberState, SubscriberState]]` transition table plus a single `transition()` function, per E1-S1. Rationale: every service that mutates subscription state (activation, suspend/resume, port-out, CSR override) shares one authority for "is this move legal," so a new rule is a one-line table edit instead of duplicated `if` chains scattered across five services. Illegal calls raise `InvalidSubscriberStateException` uniformly, which the API layer maps to HTTP 409.

`ACTIVE -> TERMINATED` and `SUSPENDED -> TERMINATED` are CSR/admin-only transitions (closing an account outside the port-out flow), specified by E6-S5 (service) and E6-S6 (API). These close the gap between the `TERMINATED` enum value (E1-S1 AC-1) and churn reporting's need for it (E7-S1 AC-3: "derived from PORTED_OUT/TERMINATED transitions"). No story defines a "terminate" UI (it is a CSR/admin back-office action, not a self-service one), so no terminate endpoint is UI-mapped in `component-map.md`, but the service, API endpoint, and FSM edge are fully specified and tested so reporting is exercisable and coherent.

### 5.2 Append-only ledgers, enforced at two levels
`StateTransition`, `PlanVersion` (once published), `BillingRecord`, `PortOutEvent`, `CSROverride` are all append-only per CLAUDE.md. Enforcement is layered defensively:
1. **Repository level**: no `update_*`/`delete_*` function is ever exposed for these tables (E4-S1 AC-1, E5-S1 AC-1, E6-S1 AC-1) — the only way to "change" a published plan is `create_plan_version` (new row, next version number).
2. **Database level**: a `BEFORE UPDATE`/`BEFORE DELETE` SQLite trigger on each append-only table raises `RAISE(ABORT, ...)`, so even a bypassing raw SQL statement fails (E4-S1 AC-3, E3-S1 AC-2). This is defense-in-depth against a future repository bug, not the primary mechanism — the primary mechanism is "the function doesn't exist."

### 5.3 Centralized PII masking
Per NFR-03/05 and E1-S3, `service/logging_service.py` wraps a lower-level `lib/logger.py` JSON emitter. Every log call goes through a masking pass (mobile number, Aadhaar ref, PAN ref → last-4-digits reveal) before serialization, so masking cannot be forgotten per call-site — it is structural, not a convention every developer must remember. All layers that log (service, API) call this one module rather than `logging.getLogger` directly; nothing outside `service/logging_service.py` and `lib/logger.py` performs raw JSON serialization of a log payload.

Per E1-S3 AC-5 the logger module itself imports only Types and Config (it does not reach into Repository), which is a stricter subset than the generic "Service may import Repository" rule — this is intentional: the logger is a pure formatting/masking utility with no persistence concern.

### 5.4 Role-based auth, gated at the controller
Role checks (`subscriber`, `csr`, `admin`, `dealer`) live in FastAPI dependency-injected guards (`api/deps.py`), not sprinkled through service functions as ad hoc `if role != ...` — except for E7-S2 AC-4, which explicitly requires the reporting *service* to re-check admin authorization independently of the API layer, so that calling the service directly (bypassing the router) still fails closed. This is the one deliberate exception to "auth lives only at the API boundary," because unauthorized report access is treated as high-severity (subscriber financial/behavioral aggregates).

Ownership enforcement ("a subscriber may only see their own subscription," NFR-04) is done by comparing the `subscriber_id` claim embedded in the bearer token against the path parameter's owning subscriber, at the same dependency layer — never by trusting a client-supplied subscriber ID without that check.

`dealer` is a valid role in the auth/type system (used in E1-S4's authorization test matrix) but has no dedicated dealer-facing endpoints or UI: dealer codes are validated server-side against `DealerMaster` during activation (E2-S1, E2-S3). Per E2-S1's own description ("no dealer-facing UI"), the dealer role's only purpose in this design is to (a) exist as a distinct role for authorization tests to exercise 403s against, and (b) be the seed data (`DealerMaster`) consulted by the activation engine.

### 5.5 Decimal everywhere for money
All monetary fields (`PlanVersion.price`, `BillingRecord.*_amount`, reporting ARPU) are typed `Decimal` in the Types layer and never widen to `float` in Config, Repository, or Service. SQLite has no native `DECIMAL` type, so the repository layer stores money as `TEXT` (canonical `str(Decimal)` representation) and reconstructs `Decimal` on read — this is the standard way to get exact round-tripping in SQLite without float drift, and is directly tested by E4-S1 AC-2 ("round-trip... exact Decimal equality").

### 5.6 Pro-rata billing as a pure function
`billing_calculation_service` (E4-S2) is a pure function of `(from_plan_price, to_plan_price, change_date, billing_cycle_start, billing_cycle_end)` → `Decimal`. It performs no I/O and is called identically by both `preview` (no persistence) and `commit` (persists the same computed value), guaranteeing preview and commit can never disagree. Days-in-month is computed from the actual calendar (via `calendar.monthrange`), not a fixed 30-day assumption, so leap-year Februaries (E4-S2 AC-2) are correct by construction rather than by special-casing.

### 5.7 Minimum-tenure and cooling-period as config-driven constants
`MIN_TENURE_DAYS` (plan change eligibility) and the 7-day port-out cooling period are both `Config` layer constants, not magic numbers buried in `Service`. The cooling-period *end timestamp* is computed once and stored on `PortOutEvent.cooling_period_end_at` at request time (E5-S1 AC-4) rather than recomputed from `requested_at + 7 days` on every read — this avoids any inconsistency if the configured window value is later changed while a port-out is in flight.

### 5.8 CSR override as a re-run, not a bypass
The override service does not directly flip subscription state; it re-invokes the same activation/plan-change service function used by the normal flow, but with the specific failed rule (e.g. `DEALER_INVALID`, `MIN_TENURE_NOT_MET`) suppressed for that one call, so the FSM and append-only writes still go through their single authoritative code path (E6-S2). Every override attempt that reaches persistence is written to `CSROverride` — including the actor, reason code, and masked context — regardless of whether the underlying action ultimately succeeds, satisfying AC-09's audit requirement.

## 6. Non-Functional Requirements Traceability

| NFR | Mechanism |
|---|---|
| NFR-03/05 (PII masking) | §5.3 |
| NFR-04 (subscriber data isolation) | §5.4 |
| NFR-06 (health check < 1s) | `GET /health`, no DB round-trip, no auth |
| NFR-07 (no double activation) | Partial unique index on `subscriptions(mobile_number) WHERE state='ACTIVE'` (E2-S1 AC-2) is the actual race guard; the FSM check is a second, in-process guard |
| NFR-08 (pro-rata charge >= 0) | `billing_calculation_service` clamps the final total with `max(Decimal("0.00"), computed)` and this is asserted by dedicated tests, never left to caller discipline |

### 5.9 CSR/admin subscription termination (E6-S5, E6-S6)

Termination is not an override of a rejected action (unlike E6-S2) — it is a standalone CSR/admin capability to close an `ACTIVE` or `SUSPENDED` subscription outright, via the same shared FSM used everywhere else. It reuses the existing append-only `StateTransition` log (E5-S1) as its audit record rather than writing to `CSROverride`, since a termination is a legitimate transition, not a bypass of a prior rejection: the `StateTransition` row's `actor` + `reason_code` (made mandatory for this call path, unlike routine transitions where it may be null) + `created_at` together satisfy the same audit intent as AC-09. A missing reason code is rejected before any write, mirroring E6-S2 AC-3.
