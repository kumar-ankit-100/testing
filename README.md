# TelcoLane

TelcoLane is a telecom **Subscriber & Plan Lifecycle Management Platform**: subscriber self-registration and rule-based activation (KYC, dealer code, MNP — all stubbed), a versioned prepaid/postpaid plan catalog with immutable published plans, plan upgrade/downgrade with pro-rata billing, suspend/resume, a 7-day port-out cooling-period workflow, CSR overrides with an audit trail, and live admin reports (activation funnel, churn, plan mix, stubbed ARPU).

Built end-to-end by Claude Code agents under human supervision as part of capstone **BC-AINE-020** — every line of production code is generated and independently re-verified (Generator → Evaluator loop), not hand-written or self-graded.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, `uv`, SQLite (WAL mode) |
| Frontend | TypeScript, React (Vite) |
| Auth | JWT bearer tokens, PBKDF2-HMAC-SHA256 password hashing |
| Testing | pytest + pytest-cov (backend), Vitest + Testing Library (frontend), Playwright (E2E) |
| Quality gates | ruff, mypy --strict, eslint, tsc |

## Architecture

Strict one-way layering: **Types → Config → Repository → Service → API → UI**. No layer imports from a layer to its right. See `.claude/architecture.md` for the enforced rules and `docs/architecture.md` for diagrams.

Key invariants:
- **Money is always `Decimal`**, never `float` — stored as canonical `TEXT` in SQLite, reconstructed on read.
- **Append-only history** (plan versions once published, state transitions, billing records, port-out events, CSR overrides) — enforced both at the repository layer (no `update_*`/`delete_*` functions) and by SQLite `BEFORE UPDATE`/`BEFORE DELETE` triggers.
- **One shared FSM** (`types/fsm.py`) drives every state-changing service — activation, suspend/resume, port-out, termination, CSR override — so "is this transition legal" has exactly one authority.
- **PII masking is structural**: all logging goes through one `logging_service` module; nothing else performs raw log serialization.
- **Roles**: `subscriber`, `csr`, `admin`, `dealer`. Dealer has no UI by design — it exists only as an authorization-test identity and as the seeded `dealer_master` reference table consulted during activation.

## Getting Started

### Prerequisites
- Python 3.12+ with [`uv`](https://docs.astral.sh/uv/)
- Node.js 18+ with npm

### One-command bootstrap

```bash
./init.sh
```

This installs backend and frontend dependencies and starts both dev servers:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### Manual setup

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm ci
npm run dev
```

The database schema (and seed data — demo staff users, dealer codes) is applied idempotently on backend startup.

## Seeded Demo Credentials

| Role | Username | Password |
|---|---|---|
| CSR | `csr_jane` | `CsrDemo!2026Synthetic` |
| Admin | `admin_raj` | `AdminDemo!2026Synthetic` |
| Dealer | `dealer_priya` | `DealerDemo!2026Synthetic` |

Subscribers don't have seeded accounts — register with any 10-digit mobile number via the UI or `POST /api/auth/login` with `{"mobile_number": "..."}`, then `POST /api/subscribers/register`. New CSR/admin accounts can also be created dynamically via `POST /api/auth/register-staff`.

Valid seeded dealer codes (for the activation step): `DLR-BLR-001`, `DLR-DEL-002`, `DLR-MUM-003`, `DLR-CHN-004`, `DLR-HYD-005`.

## Commands

**Backend** (`cd backend`):
```bash
uv run pytest -x -q                 # run tests
uv run pytest --cov=app             # with coverage
uv run ruff check --fix .           # lint
uv run mypy src/                    # type check
```

**Frontend** (`cd frontend`):
```bash
npm test          # unit tests (Vitest)
npm run lint       # eslint
npm run typecheck  # tsc --noEmit
npm run e2e        # Playwright E2E
```

## Project Structure

```
backend/
  src/app/
    types/        # domain types, enums, exceptions, FSM — zero downstream imports
    config/       # settings, DB connection
    repository/   # SQLite persistence, schema.sql
    service/      # business logic
    api/          # FastAPI routers, schemas, auth deps, error handlers
  tests/
    unit/         # repository + service tests
    integration/  # full-stack API tests via TestClient

frontend/
  src/
    types/        # DTOs, domain enums
    config/        # auth storage, env, dealer code reference
    api/           # fetch wrappers, one module per endpoint group
    service/       # React hooks composing api/ calls into UI state
    ui/            # pages and components
  tests/           # Vitest + Testing Library
  e2e/             # Playwright specs

docs/              # business case, architecture diagrams, TDD notes, fix-loop traces
specs/             # app spec, per-feature specs, design docs, sprint contracts
```

## API

Base URL (dev): `http://localhost:8000`. Every route except `GET /health` requires `Authorization: Bearer <token>`. Full contract in `specs/design/api-contracts.md`; interactive docs at `http://localhost:8000/docs` while the backend is running.

| Area | Key routes |
|---|---|
| Auth | `POST /api/auth/login`, `POST /api/auth/register-staff` |
| Subscribers | `POST /api/subscribers/register`, `POST /api/subscribers/{id}/activate`, `GET /api/subscribers/{id}/subscription` |
| Plans | `GET /api/plans` (published catalog, any role), `POST/GET /api/admin/plans` (admin, full version history) |
| Lifecycle | `POST /api/subscriptions/{id}/suspend`, `/resume`, `/port-out/request`, `/port-out/cancel`, `/port-out/finalize`, `/terminate` |
| Plan change | `POST /api/subscriptions/{id}/plan-change/preview`, `/commit` |
| CSR | `POST /api/csr/overrides/activation/{subscriber_id}`, `/plan-change/{subscription_id}` |
| Reports | `GET /api/admin/reports/dashboard` |

## Pipeline Commands (for continued AI-native development)

| Command | Purpose |
|---|---|
| `/brd` | Socratic interview → Business Requirements Document |
| `/spec` | BRD → stories + `features.json` |
| `/design` | Architecture + schemas + mockups |
| `/build` | Full 8-phase pipeline |
| `/implement` | Code gen with agent teams |
| `/evaluate` | Run app, verify sprint contract |
| `/review` | Evaluator + security review |
| `/test` | Test plan + Playwright E2E |
| `/deploy` | Local dev bootstrap via `init.sh` |

See `CLAUDE.md` for the full project contract and `claude-progress.txt` for session-recovery notes.

## License

Educational capstone project — not for production use.
