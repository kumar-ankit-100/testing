# TelcoLane — Deployment

## 1. Environments

Per `project-manifest.json`, this project's `deployment.method` is `local-dev-servers` — there is currently one real environment (local dev), described below with a documented path to add staging/prod later without redesigning the app.

| Environment | Backend | Frontend | Database | Purpose |
|---|---|---|---|---|
| **dev** (current) | `uvicorn --reload` on `:8000` | `vite dev` on `:5173` | `backend/telcolane.db` (SQLite/WAL, gitignored) | Local development, `/evaluate` and Playwright runs |
| **staging** (future) | Same FastAPI app, container image, no `--reload` | Static build (`npm run build`) served by Nginx or the same container | SQLite file on a persistent volume, or migrate to Postgres if concurrent write load grows | Pre-prod verification |
| **prod** (future) | Same image, behind a reverse proxy (TLS) | Static build behind CDN/reverse proxy | Same as staging | Live traffic |

SQLite/WAL is adequate for staging/prod at this project's expected scale (a single-writer append-heavy workload with modest concurrency); if write concurrency becomes a bottleneck, the Repository layer's SQL is the only layer that would need to change to move to Postgres, since Service/API/UI never touch SQL directly (per the layered architecture, this is the intended seam for that future migration).

## 2. Local Dev Bootstrap (current)

`init.sh` (repo root) is the single entry point:

```bash
#!/bin/bash
set -euo pipefail
cd backend && uv sync && cd ..
cd frontend && npm ci && cd ..
[ -f .env.example ] && [ ! -f .env ] && cp .env.example .env
(cd backend && uv run uvicorn app.api.main:app --reload --port 8000 &)
(cd frontend && npm run dev &)
curl --retry 5 --retry-delay 2 --retry-connrefused -sf http://localhost:8000/health
curl --retry 5 --retry-delay 2 --retry-connrefused -sf http://localhost:5173
```

Quick reference commands (from `CLAUDE.md`, used identically in dev and CI):

| Command | Purpose |
|---|---|
| `cd backend && uv run pytest -x -q` | Backend unit + integration tests |
| `cd backend && uv run ruff check --fix .` | Lint/format |
| `cd backend && uv run mypy src/` | Static typing gate (zero `any`) |
| `cd frontend && npm test` | Frontend unit tests (vitest) |
| `cd frontend && npm run lint` | ESLint |
| `cd frontend && npm run typecheck` | `tsc --noEmit` |
| `cd backend && uv run uvicorn app.api.main:app --reload --port 8000` | Run backend |
| `cd frontend && npm run dev` | Run frontend |

`backend/src/app/api/main.py`'s startup hook applies `repository/schema.sql` (idempotent `CREATE TABLE IF NOT EXISTS` + dealer seed `INSERT OR IGNORE`) so a fresh `telcolane.db` is ready on first boot with no separate migration step, matching E2-S1 AC-3 ("seeded... on application startup/migration").

## 3. CI/CD Pipeline (future, once a remote is in scope)

Github Actions-shaped, mirroring the local commands exactly so CI never diverges from what a developer runs locally:

```
on: [push, pull_request]

jobs:
  backend:
    steps:
      - uv sync
      - uv run ruff check .
      - uv run mypy src/
      - uv run pytest -x -q --cov=src --cov-fail-under=80    # coverage floor per CLAUDE.md

  frontend:
    steps:
      - npm ci
      - npm run lint
      - npm run typecheck
      - npm test

  e2e (needs: [backend, frontend]):
    steps:
      - start backend + frontend (init.sh equivalent)
      - npx playwright test

  build-and-push (needs: [backend, frontend, e2e], on: push to main):
    steps:
      - docker build backend -> registry
      - docker build frontend (static build + nginx) -> registry
```

The coverage floor (80%, per `.claude/program.md`) and the ratchet gate block merge on regression — this is enforced identically whether run by `/auto`, `/evaluate`, or CI, since all three call the same `uv run pytest --cov` command.

## 4. Infrastructure-as-Code Approach

For local dev, none is needed — two processes and a file. For staging/prod, the intended approach (not yet implemented, since `deployment.method` is currently `local-dev-servers`) is:

- **Containers**: one `Dockerfile` per app (`backend/Dockerfile`, `frontend/Dockerfile`), composed via `docker-compose.yml` for staging-equivalent local integration testing.
- **Config as environment variables**: every value in `config/settings.py` is sourced from an env var with a documented default (E1-S2 AC-1), so no code change is needed between environments — only the env file/secret store changes.
- No cloud-specific IaC (Terraform/CDK) is warranted yet at this project's single-service, single-database scale; introducing it before there is a second environment to provision would be premature.

## 5. Secrets Management

| Secret | Dev | Staging/Prod (future) |
|---|---|---|
| JWT signing secret (`JWT_SECRET`) | `.env` (gitignored, from `.env.example` template with a dev-only placeholder) | Injected via the platform's secret store (e.g. environment variables set by the orchestrator), never baked into the container image |
| Seeded staff credentials (CSR/admin/dealer test users) | Hardcoded dev-only seed in `schema.sql` with clearly-fake passwords (documented as stub, not real auth, per E1-S2's "deterministic stub-integration flags" framing) | Replaced by a real identity provider or admin-provisioned accounts — out of scope for this stubbed-integration project |

`.env` is gitignored (already present in `.gitignore`); `.env.example` documents every variable name with a safe default and no real secret value, so onboarding never requires asking anyone for a credential to run the app locally.

## 6. Rollback Procedure

**Current (local dev)**: there is no deployed artifact to roll back — `git revert`/`git checkout` to a prior commit and re-run `init.sh`.

**Future (staging/prod)**:
1. Each `build-and-push` CI run tags the container image with the commit SHA — the registry retains all prior tags.
2. Rollback = re-point the running service at the previous known-good image tag and restart; no database migration rollback is normally needed because all schema changes are additive (`CREATE TABLE IF NOT EXISTS`, new nullable columns) — consistent with the append-only design principle, which already avoids destructive migrations by construction.
3. If a schema change ever were destructive, the rule is: ship the additive migration in one release, the removal of the now-unused column in a strictly later release, so any single rollback never depends on a migration that hasn't shipped yet.
