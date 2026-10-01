# TelcoLane

TelcoLane is a telecom Subscriber & Plan Lifecycle Management Platform. It handles subscriber self-registration and rule-based activation (KYC, dealer code, MNP, all stubbed), a versioned prepaid/postpaid plan catalog with immutable published plans, plan upgrade/downgrade with pro-rata billing, suspend/resume, a 7-day port-out cooling-period workflow, CSR overrides with audit trail, and admin reports (activation funnel, churn, plan mix, stubbed ARPU). All money is computed with Decimal. State transitions, plan versions, billing records and overrides are append-only. PII is masked in logs. Roles are subscriber, CSR, admin and dealer.

## Quick Reference

**Backend:** `cd backend && uv run pytest -x -q` | `uv run ruff check --fix .` | `uv run mypy src/`
**Frontend:** `cd frontend && npm test` | `npm run lint` | `npm run typecheck`
**Full stack:** `cd backend && uv run uvicorn app.api.main:app --reload --port 8000` and `cd frontend && npm run dev` (see init.sh)

## Architecture

Strict layered architecture: Types → Config → Repository → Service → API → UI.
One-way dependencies only. See `.claude/architecture.md` for full rules.

## Where to Find Things

| What | Where |
|------|-------|
| Architecture rules | `.claude/architecture.md` |
| Quality principles | `.claude/skills/code-gen/SKILL.md` |
| Testing patterns | `.claude/skills/testing/SKILL.md` |
| Evaluation rubric | `.claude/skills/evaluation/SKILL.md` |
| Sprint contract format | `.claude/skills/evaluation/references/contract-schema.json` |
| Playwright patterns | `.claude/skills/evaluation/references/playwright-patterns.md` |
| Human control knobs | `.claude/program.md` |
| Session recovery | `claude-progress.txt` |
| Feature tracking | `features.json` |
| Learned rules | `.claude/state/learned-rules.md` |

## Pipeline Commands

| Command | Purpose |
|---------|---------|
| `/brd` | Socratic interview → BRD |
| `/spec` | BRD → stories + features.json |
| `/design` | Architecture + schemas + mockups |
| `/build` | Full 8-phase pipeline |
| `/auto` | Autonomous ratcheting loop |
| `/implement` | Code gen with agent teams |
| `/evaluate` | Run app, verify contract |
| `/review` | Evaluator + security review |
| `/test` | Test plan + Playwright E2E |
| `/deploy` | Local dev bootstrap via init.sh |

## Code Style

- TDD mandatory: test first, then implement
- 100% meaningful coverage target, 80% floor
- Functions < 50 lines, files < 300 lines
- Static typing everywhere (zero `any`)
- All money computed with `Decimal`, never `float`
- State transitions, plan versions, billing records and overrides are append-only
- PII must be masked in logs
- See `.claude/skills/code-gen/SKILL.md` for full rules

## Git

Branch: `<type>/<description>` (e.g., `feat/user-auth`)
Commits: conventional format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`)
