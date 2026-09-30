# Business Requirements Document — TelcoLane

**Capstone reference:** BC-AINE-020 (AI-Native Engineer Capstone, individual, 20-hour engagement)
**Status:** Approved — 2026-09-30
**Date:** 2026-09-30

---

## 1. Executive Summary

TelcoLane is a telecom Subscriber & Plan Lifecycle Management Platform built as an AI-native engineering capstone (BC-AINE-020). It is graded by automated review of the Git repository against a 21-parameter, 100-mark rubric, with a target grade of Merit (75–89) or Distinction (90+). The platform models a realistic (not production) telecom operator workflow: subscriber self-registration and rule-based activation, a versioned plan catalog, plan upgrade/downgrade with pro-rata billing, suspend/resume, a 7-day port-out cooling-period workflow, CSR overrides with audit trail, and admin reporting. Network provisioning, MNP backend, payment gateway, and real KYC are all stubbed. Only synthetic data is used. The core constraint driving every decision in this BRD is that no code is hand-written — all implementation is produced by AI agents under this project's harness, with humans providing direction, review, and approval gates.

## 2. Problem Statement

An operator wants a single platform to manage the subscriber lifecycle: activation, plan upgrades/downgrades, suspensions, pro-rata billing, and port-out — while the engineering team demonstrates it can deliver this *without hand-writing code*, using AI agents under human-controlled quality, security, and architecture gates. The risk being modeled is not a real business loss (this is an evaluation project with no real users or money) but the risk of failing to demonstrate AI-native delivery competence: accurate pro-rata billing, audited state transitions, port-out compliance, and process discipline (tests, PR-driven merges, CI), as graded by the rubric. The domain pain points being simulated are: error-prone manual pro-rata billing, unaudited CSR overrides, and non-compliant port-out cooling-period handling.

## 3. Target Users

| Role | Context | Interface |
|---|---|---|
| Subscriber | Self-service, low technical assumption | React web UI, responsive |
| CSR (Customer Service Rep) | Internal back-office user, works an exception queue | Desktop-first internal UI |
| Admin | Internal back-office user, manages catalog and reporting | Desktop-first internal UI |
| Dealer | Not a UI user in this build — identified at activation time only | No portal; dealer code validated against a seeded dealer master |

All roles are authenticated and authorized at the controller level (NFR). Subscribers see only their own subscription data (NFR-04); CSR/Admin/Dealer operate within their own auth boundaries.

## 4. Success Metrics

Since this is a graded evaluation project rather than a live product, success is defined entirely by rubric conformance:
- All 10 acceptance criteria (AC-01–AC-10) implemented, each with at least one test referencing its AC-NN ID.
- All 8 NFRs met (Decimal-only money, append-only records, PII masking, controller-level auth, structured logs, health endpoint <1s, immutable published plans, no double-ACTIVE subscriptions, pro-rata invariant).
- Deliverables per §7/§8.1 of the brief: one-command local run with seed data; 3,000+ lines of generated code; 20+ unit tests with a coverage artefact; Playwright UI tests covering at least one responsive layout; 3+ PR-driven merges with zero direct commits to `main`; CI configured with Claude Code Action.
- Target grade: Merit (75–89), reaching for Distinction (90+).
- No hand-written code — all implementation traceable to AI-agent generation under human review/approval gates.

## 5. Scope

### In Scope
- Subscriber self-registration with mobile number, identity-proof reference, and plan type; rule-based activation gated on stubbed KYC verification, dealer code validation, and stubbed MNP check.
- Versioned prepaid/postpaid plan catalog; published plan versions are immutable.
- Plan upgrade/downgrade with pro-rata billing preview and commit (AC-05 formula).
- Suspend/resume of a subscription.
- Port-out request with a 7-day cooling period; cancel-within-window returns to ACTIVE; finalize/cancel-after-window handled per rule.
- CSR exception queue with override of rejected activation/plan-change actions, requiring a reason code, fully audited (actor + timestamp).
- Admin plan catalog management (versioned, create-new-version rather than mutate-published).
- Admin reporting: activation funnel, monthly churn, plan mix, stubbed ARPU trend.
- Subscriber views: plan/usage (stubbed counters), bills, stubbed recharge.
- Dealer code validated at activation against a seeded dealer master (no dealer UI/workflow beyond this).
- Structured JSON logging with PII masking (mobile number, Aadhaar reference, PAN reference).
- Health endpoint responding within 1 second.

### Out of Scope
- Real network provisioning, real MNP backend integration, real payment gateway, real KYC verification — all stubbed with deterministic, flag-driven logic.
- Any dealer-facing portal or workflow beyond dealer-code validation.
- Email/SMS notifications of any kind.
- Real compliance handling (GDPR/DPDP) — only synthetic data is used; masking is the only privacy control implemented.
- Multi-session/concurrent load testing beyond the single explicit double-activation race check.
- Visual design polish — not a graded rubric category.

## 6. MVP Definition

Because grading is against a fixed rubric rather than incremental product value, there is no smaller "phase 1" — the MVP **is** the full scope above: all 10 ACs and all 8 NFRs implemented and tested, delivered through the harness's PR-driven pipeline with CI. There is no deferred second release within this engagement.

## 7. Alternatives Considered

**Decision needed:** how to implement the subscriber state machine and the append-only requirement.

| Option | Description | Chosen? |
|---|---|---|
| A. Explicit state-machine library with declarative transition table | `PENDING_KYC → ACTIVE → SUSPENDED / TERMINATED / PORT_OUT_REQUESTED → PORTED_OUT`; invalid transitions raise `InvalidSubscriberStateException` | **Yes** |
| B. Hand-rolled transition-dict check in the service layer | No new dependency, but higher risk of code/diagram drift, more agent-written logic to get right | No |
| C. Full event-sourcing across all entities | Maximum auditability uniformly | No — overkill for 20-hour scope |

**Rationale:** Option A most directly demonstrates AC-02's transition-correctness requirement in an auditable, testable way with minimal custom code. Combined with this, append-only storage is applied **narrowly** — exactly to what NFR-02/NFR-05 list: plan versions, subscriber state transitions, billing records, port-out events, CSR overrides, and DB/plan-catalog migrations — rather than event-sourcing every entity, keeping scope proportionate to the engagement.

## 8. Technical Architecture

- **Stack (fixed):** Backend — Python 3.12, FastAPI, `uv` package manager, `ruff` lint, `mypy` typecheck, `pytest`. Frontend — TypeScript, React, Vite, `npm`, `eslint`, `tsc`, `vitest`. Database — SQLite. Deployment — local dev servers only, single-command bootstrap (`init.sh`).
- **Layered architecture:** strict one-way dependency flow Types → Config → Repository → Service → API → UI (per `.claude/architecture.md`).
- **State machine:** explicit declarative library-based FSM per Alternative A above, raising `InvalidSubscriberStateException` on invalid transitions (AC-02).
- **Concurrency:** SQLite in WAL mode; the only enforced concurrency invariant is "no two ACTIVE subscriptions per mobile number," enforced via a service-layer check **plus** a partial unique index, with an explicit test for the double-activation race (NFR-08).
- **Stubbed integrations:** implemented as trivial synchronous functions returning deterministic canned results by input pattern — no fake HTTP clients or simulated latency. Examples: KYC flag `VERIFIED`/not-verified; dealer code `DEALER-FAIL` to force rejection; an MNP-fail flag. Each drives a distinct, testable AC-08 failure path.
- **Performance:** demo scale only; the sole formal requirement is the health endpoint returning HTTP 200 within 1 second of successful startup (NFR-07). No load testing.
- **Money handling:** all monetary values computed with `Decimal`, never `float`.

## 9. Data Model Overview

Primary entities (exact schema to be finalized in `/design`): Subscriber, Subscription (with current state per FSM), PlanCatalog / PlanVersion (versioned, immutable once published), BillingRecord (append-only, pro-rata calculations), StateTransition (append-only log), PortOutEvent (append-only, tracks 7-day window), CSROverride (append-only, actor + timestamp + reason code), DealerMaster (seeded, read-mostly), AuditLog entries derived from the append-only tables above. Migrations to plan catalog / DB schema are themselves treated as append-only history.

## 10. External Integrations

None real. All external dependencies are stubbed in-process:
- **KYC:** flag-based stub only (verified / not verified).
- **MNP (Mobile Number Portability):** workflow-states-only stub (success / fail flag).
- **Payment gateway:** stubbed responses for recharge/billing display.
- **Dealer validation:** seeded local dealer master table, no external dealer system.

## 11. Edge Cases & Constraints

- **Notifications:** none (no email/SMS). Rejections and overrides surface as: a UI message with reason code, a structured JSON log entry (masked PII), and an audit record (actor + timestamp) for CSR overrides.
- **Example failure path:** a plan change attempted on a SUSPENDED subscriber is rejected with a visible reason code (brief §8.2 item 12).
- **Compliance:** synthetic data only — no real GDPR/DPDP handling. NFR-03 masking still applies: mobile number, Aadhaar reference, and PAN reference are masked in logs and not stored in plaintext where avoidable.
- **Required negative-path tests** (beyond AC-02/NFR-08 baseline):
  - Pro-rata calculation across boundary dates including a leap-year boundary; `charges_total ≥ 0` invariant.
  - Invalid state transitions rejected with `InvalidSubscriberStateException`.
  - Attempt to mutate a published plan version (must fail; new version required instead).
  - Port-out cooling period: cancel within 7 days returns subscription to ACTIVE; cancel or finalize after the window behaves per rule.
  - Role-boundary violations: a subscriber reading another subscriber's data, or calling a CSR/admin endpoint, is rejected.
  - Activation failure paths: unverified KYC, invalid dealer code, MNP failure — each independently testable via its deterministic stub trigger.
  - Plan change violating the minimum-tenure rule (AC-04).
  - Double-activation attempt for the same mobile number (enforced by service check + partial unique index).
- **Uptime/budget/rate limits:** not applicable — local dev-only, single-user demo context.

## 12. UI Context

- **Design references:** none. Visual polish is explicitly not a graded rubric category (brief §2). A clean, functional operator-console aesthetic is left to the UI Designer agent's judgment during `/design`.
- **Devices:** Subscriber self-service UI is responsive (desktop + mobile), satisfying the rubric's requirement of at least one responsive layout (§7.2). CSR and Admin screens are desktop-first internal tools.
- **Accessibility:** reasonable defaults only — semantic HTML, form labels, readable contrast, keyboard-usable controls. Not a confirmed scored rubric category (the graded categories are specs & substrate, business understanding, architectural discipline, technical implementation, and CI/CD), so this is implemented to a sensible baseline without gold-plating.

## 13. Open Questions

- Exact list of all 21 rubric parameters is not fully visible to us — accessibility scoring cannot be definitively ruled in or out, though current signal suggests it is not scored. Treated as a minor risk; no action needed beyond the reasonable-defaults baseline above.
- Precise wording/thresholds for the leap-year boundary pro-rata test case will be finalized during `/test` (test case design), not this BRD.
- Any additional dealer-master seed data conventions (e.g., how many seeded dealers, code format) will be finalized during `/design` data modeling, not blocking BRD approval.

---

*This BRD synthesizes the five-dimension Socratic interview (Why, What, Alternatives, How, Edge Cases, UI Context) conducted for the TelcoLane / BC-AINE-020 capstone. Approved by human on 2026-09-30. Proceeding to `/spec`.*
