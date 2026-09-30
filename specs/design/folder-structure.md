# TelcoLane — Folder Structure

Layer order is literal and matches `.claude/architecture.md`: **Types -> Config -> Repository -> Service -> API -> UI**, one-way imports only. Backend and frontend each implement the full chain; the frontend has no true "Repository" concept (no local persistence), so its `api/` directory plays that role — it is the only place that talks to the network, exactly as `repository/` is the only place that talks to SQLite on the backend. This substitution is called out explicitly per `architecture.md`'s customization note (layer paths may be adapted per stack).

## Backend (`backend/`)

```
backend/
├── pyproject.toml                     # uv-managed deps: fastapi, pydantic, pyjwt, pytest, ruff, mypy
├── uv.lock
├── src/
│   └── app/
│       ├── types/                     # LAYER 1 — zero imports from any other layer
│       │   ├── __init__.py
│       │   ├── enums.py               # SubscriberState, PlanType, Role, ReasonCode, PortOutStatus
│       │   ├── fsm.py                  # transition table + transition() + InvalidSubscriberStateException
│       │   ├── exceptions.py          # PlanVersionImmutableError, and other typed domain errors
│       │   ├── subscriber.py          # Subscriber dataclass
│       │   ├── subscription.py        # Subscription dataclass
│       │   ├── plan.py                # PlanVersion dataclass
│       │   ├── billing.py             # BillingRecord dataclass
│       │   ├── state_transition.py    # StateTransition dataclass
│       │   ├── port_out.py            # PortOutEvent dataclass
│       │   ├── csr_override.py        # CSROverride dataclass
│       │   ├── dealer.py              # DealerMaster dataclass
│       │   └── auth.py                # User dataclass, Principal (decoded-token) type
│       │
│       ├── config/                    # LAYER 2 — imports Types only
│       │   ├── __init__.py
│       │   ├── settings.py            # typed Settings: DB path, MIN_TENURE_DAYS, JWT secret/exp
│       │   ├── stub_flags.py          # KYC_STUB_FLAG, MNP_STUB_FLAG, DEALER_FAIL_CODE
│       │   └── db.py                  # SQLite connection factory, PRAGMA journal_mode=WAL
│       │
│       ├── repository/                # LAYER 3 — imports Types, Config only
│       │   ├── __init__.py
│       │   ├── schema.sql             # DDL: tables, partial unique index, append-only triggers, dealer seed
│       │   ├── subscriber_repository.py
│       │   ├── dealer_repository.py
│       │   ├── plan_repository.py
│       │   ├── billing_repository.py
│       │   ├── state_transition_repository.py
│       │   ├── port_out_repository.py
│       │   ├── csr_override_repository.py
│       │   ├── reporting_repository.py
│       │   └── user_repository.py
│       │
│       ├── service/                   # LAYER 4 — imports Types, Config, Repository only
│       │   ├── __init__.py
│       │   ├── logging_service.py     # PII-masking structured logger (imports Types+Config only, per E1-S3 AC-5)
│       │   ├── auth_service.py        # login, token issue/verify, role/ownership checks callable outside API layer
│       │   ├── registration_service.py
│       │   ├── activation_service.py
│       │   ├── plan_catalog_service.py
│       │   ├── billing_calculation_service.py   # pure Decimal pro-rata math, no I/O
│       │   ├── plan_change_service.py
│       │   ├── suspend_resume_service.py
│       │   ├── port_out_service.py
│       │   ├── csr_override_service.py
│       │   ├── termination_service.py           # CSR/admin-only ACTIVE/SUSPENDED -> TERMINATED (E6-S5)
│       │   └── reporting_service.py
│       │
│       ├── api/                       # LAYER 5 — imports Types, Config, Repository, Service only
│       │   ├── __init__.py
│       │   ├── main.py                # FastAPI app factory, router mounting, startup (schema.sql apply)
│       │   ├── deps.py                # auth DI: current_principal(), require_role(), require_own_subscriber()
│       │   ├── error_handlers.py      # maps domain exceptions -> HTTP status + reason_code body
│       │   ├── routers/
│       │   │   ├── health_router.py
│       │   │   ├── auth_router.py
│       │   │   ├── subscriber_router.py
│       │   │   ├── plan_router.py
│       │   │   ├── plan_change_router.py
│       │   │   ├── lifecycle_router.py       # suspend/resume/port-out(+cancel/finalize)
│       │   │   ├── csr_router.py
│       │   │   └── admin_reports_router.py
│       │   └── schemas/                       # pydantic request/response models (one file per router)
│       │       ├── auth_schemas.py
│       │       ├── subscriber_schemas.py
│       │       ├── plan_schemas.py
│       │       ├── plan_change_schemas.py
│       │       ├── lifecycle_schemas.py
│       │       ├── csr_schemas.py
│       │       └── report_schemas.py
│       │
│       └── lib/                       # cross-cutting utility, used by any layer per architecture.md
│           ├── __init__.py
│           ├── pii_mask.py            # low-level masking primitives reused by logging_service
│           └── telemetry.py           # span/trace helper stubs
│
└── tests/
    ├── unit/                          # one file per repository/service module above
    └── integration/                   # one file per router, using FastAPI TestClient
```

There is no `ui/` directory in the backend — UI is the frontend's top layer.

## Frontend (`frontend/`)

```
frontend/
├── package.json                       # react, vite, typescript, vitest, eslint, @playwright/test
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── types/                         # LAYER 1 — mirrors backend domain + API response shapes
│   │   ├── domain.ts                  # SubscriberState, PlanType, Role, ReasonCode
│   │   └── api.ts                     # request/response DTO types matching api-contracts.md
│   │
│   ├── config/                        # LAYER 2 — imports types only
│   │   └── env.ts                     # API_BASE_URL, from Vite env vars
│   │
│   ├── api/                           # LAYER 3 (Repository-equivalent) — the only layer that calls fetch()
│   │   ├── client.ts                  # shared fetch wrapper: auth header injection, error unwrapping
│   │   ├── authApi.ts
│   │   ├── subscriberApi.ts
│   │   ├── planApi.ts
│   │   ├── planChangeApi.ts
│   │   ├── lifecycleApi.ts
│   │   ├── csrApi.ts
│   │   └── reportsApi.ts
│   │
│   ├── service/                       # LAYER 4 — React hooks composing api/ calls + UI-facing business rules
│   │   ├── useAuth.ts
│   │   ├── useRegistration.ts
│   │   ├── useActivationStatus.ts
│   │   ├── usePlanCatalog.ts
│   │   ├── usePlanChange.ts
│   │   ├── useLifecycle.ts
│   │   ├── useCsrExceptions.ts
│   │   └── useReports.ts
│   │
│   └── ui/                            # LAYER 5 (topmost) — imports types, config, api, service
│       ├── App.tsx
│       ├── router.tsx
│       ├── components/                # shared building blocks
│       │   ├── ReasonMessage.tsx
│       │   ├── StateBadge.tsx
│       │   ├── CountdownTimer.tsx
│       │   ├── LoadingState.tsx
│       │   └── ErrorState.tsx
│       └── pages/
│           ├── RegisterPage.tsx               # E2-S5
│           ├── ActivationStatusPage.tsx       # E2-S5
│           ├── AdminPlanCatalogPage.tsx       # E3-S4
│           ├── PlanChangePage.tsx             # E4-S5
│           ├── LifecyclePage.tsx              # E5-S5 (suspend/resume/port-out)
│           ├── CsrExceptionQueuePage.tsx      # E6-S4
│           └── AdminReportsDashboardPage.tsx  # E7-S4
│
├── tests/                             # vitest unit tests for hooks/components
└── e2e/                                # Playwright specs, one per UI story
    ├── registration.spec.ts
    ├── admin-plan-catalog.spec.ts
    ├── plan-change.spec.ts
    ├── lifecycle.spec.ts
    ├── csr-queue.spec.ts
    └── admin-reports.spec.ts
```

## Layering note (frontend "Repository")

The generic architecture table's "Repository: Data access, persistence, external data sources" maps to `frontend/src/api/` here — it is the frontend's only external-data boundary (the backend REST API), just as `backend/src/repository/` is the backend's only boundary to SQLite. No frontend directory is named `repository/` to avoid implying local persistence that doesn't exist; this substitution is documented here per `architecture.md`'s stated allowance for adapting layer paths to a non-standard stack.
