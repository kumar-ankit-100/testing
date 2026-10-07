# Architecture — TelcoLane

## Layers (one-way imports only)

```
Types → Config → Repository → Service → API → UI
```

No layer imports from a layer above it, enforced by `.claude/hooks/check-architecture.js` on every file save. Frontend mirrors the same chain: `types/ → config/ → api/ (the only layer that calls fetch()) → service/ (hooks) → ui/`.

## System Context

```mermaid
graph TD
    subgraph Frontend [React + Vite :5173]
        UI[ui/ pages]
        Hooks[service/ hooks]
        ApiClient[api/ client.ts]
        UI --> Hooks --> ApiClient
    end

    subgraph Backend [FastAPI + Uvicorn :8000]
        Router[API routers]
        Svc[Service layer]
        Repo[Repository layer]
        Types[Types layer]
        Router --> Svc --> Repo --> Types
    end

    DB[(SQLite, WAL mode)]

    ApiClient -->|Bearer JWT, CORS allowed from :5173| Router
    Repo --> DB
```

## Subscriber Lifecycle (the state machine every mutating service shares)

```mermaid
stateDiagram-v2
    [*] --> PENDING_KYC: register
    PENDING_KYC --> ACTIVE: activate (or CSR override)
    ACTIVE --> SUSPENDED: suspend
    SUSPENDED --> ACTIVE: resume
    ACTIVE --> PORT_OUT_REQUESTED: port-out request
    PORT_OUT_REQUESTED --> ACTIVE: port-out cancel (within 7 days)
    PORT_OUT_REQUESTED --> PORTED_OUT: port-out finalize (after 7 days)
    ACTIVE --> TERMINATED: CSR/admin terminate
    SUSPENDED --> TERMINATED: CSR/admin terminate
    PORTED_OUT --> [*]
    TERMINATED --> [*]
```

Defined once as a declarative `frozenset[tuple[SubscriberState, SubscriberState]]` in `backend/src/app/types/fsm.py`. Every service that moves a subscription — activation, suspend/resume, port-out, termination, CSR override — calls this one `transition()` function. An edge not in the table raises `InvalidSubscriberStateException`, mapped to HTTP 409 by `error_handlers.py`.

## Activation → Port-Out Sequence (representative end-to-end flow)

```mermaid
sequenceDiagram
    participant S as Subscriber (browser)
    participant A as Auth router
    participant Sub as Subscriber router
    participant Svc as activation_service
    participant Repo as subscriber_repository
    participant DB as SQLite

    S->>A: POST /api/auth/login {mobile_number}
    A-->>S: 200 {access_token, subscriber_id: null}
    S->>Sub: POST /api/subscribers/register (Bearer token)
    Sub->>Svc: register_subscriber(...)
    Svc->>Repo: create_subscriber + create_subscription (PENDING_KYC)
    Repo->>DB: INSERT
    Sub-->>S: 201 {subscriber_id, access_token (subscriber_id now populated)}
    S->>Sub: POST /api/subscribers/{id}/activate {dealer_code} (new token)
    Sub->>Svc: activate_subscriber(...)
    Svc->>Svc: check KYC stub, dealer_code, MNP stub
    alt all rules pass
        Svc->>Repo: update_subscription_state(ACTIVE) + append_state_transition
        Sub-->>S: 200 {state: ACTIVE}
    else a rule fails
        Sub-->>S: 422 {reason_code}
    end
```

## Component Map

| Component | Technology | Responsibility |
|---|---|---|
| Backend API | FastAPI + Uvicorn | All business logic, persistence, auth, reporting |
| Database | SQLite (WAL mode) | Single-file store; append-only tables for ledgers |
| Frontend SPA | React + Vite + TypeScript | Subscriber self-service, admin/CSR internal tools |
| Stub integrations | In-process config flags | Deterministic KYC/dealer/MNP outcomes, no network calls |

## Key Design Decisions

1. **Table-driven FSM in the Types layer** (see above) — one authority for transition legality, not five duplicated checks.
2. **Append-only enforced at two levels** — no update/delete repository function for ledger tables, *plus* a database trigger as defense-in-depth against a raw-SQL bypass.
3. **PII masking is structural** — `logging_service.py` is the only module that serializes a log payload; masking cannot be forgotten per call-site.
4. **Decimal everywhere for money** — stored as canonical `TEXT` in SQLite (no native decimal type), reconstructed as `Decimal` on read.
5. **Pro-rata billing as a pure function** — `billing_calculation_service.calculate_pro_rata_charge` has no I/O; preview and commit call the identical function, so they can never disagree.
6. **CSR override as a re-run, not a bypass** — re-invokes the same authoritative service function with one rule suppressed, so the FSM and append-only writes still go through their single normal code path.
7. **Role-based auth at the controller layer** — `require_role`/`require_own_subscriber` dependencies, with the admin-reporting service re-checking its own role requirement independently of the router (the one deliberate exception, since unauthorized report access is treated as high-severity).

## Known Gaps (honestly, not swept under the rug)

- No `src/domain/` directory with dedicated rule/policy/validator files — domain rules live inside the relevant service files (`activation_service.py`'s rule sequence, `plan_change_service.py`'s tenure check, `fsm.py`'s transition table) rather than a separate domain layer.
- No `import-linter`/`dependency-cruiser` config yet — layering is enforced by a custom pre-save hook (`check-architecture.js`), not a dedicated architecture-test tool.
- `main` branch lagged `develop` by several commits as of this writing (all of Group F/G's work landed on `develop` only) — see `claude-progress.txt` for the exact catch-up status.
