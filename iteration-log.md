# Iteration Log

## Group A

Group A micro-DAG:
  Phase 1: teammate-types (E1-S1, produces: Types layer — no upstream deps)
  Phase 1: teammate-config (E1-S2, produces: Config layer — no upstream deps)
  No shared files between E1-S1 and E1-S2 per component-map.md. No Produces:/Consumes:
  annotations present in component-map.md and no shared files identified — handshake
  skipped per generator SOP; both teammates spawned in parallel.

Backend project scaffolded by orchestrator prior to teammate spawn (shared bootstrap,
not owned by either story): backend/pyproject.toml, backend/src/app/**/__init__.py,
backend/tests/**/__init__.py, uv sync completed, Python 3.12 pinned.

Process gap discovered and corrected this group: teammate spawn used a blocking
"present plan, wait for approval" gate the generator cannot fulfill (no SendMessage
in its tool grant). Promoted to Learned Rule 1 (.claude/state/learned-rules.md) and
failures.md Group A Failure #1. Both stuck teammates abandoned; generator
implemented E1-S1/E1-S2 directly instead. Group A passed evaluator review
(VERDICT PASS, 11/11 checks, sprint-contracts/group-a.json) and merged to develop
as a64b4f8.

## Group B

9 stories: E1-S3, E1-S4, E1-S5, E2-S1, E3-S1, E4-S1, E5-S1, E6-S1, E7-S1.

Micro-DAG / execution decision: component-map.md's cross-cutting table shows
schema.sql touched by 5 of these 9 stories (E2-S1, E3-S1, E4-S1, E5-S1, E6-S1),
and E7-S1 semantically reads tables those 5 stories create even though the
dependency-graph treats all of Group B as parallel (no intra-group depends_on).
Combined with Learned Rule 1 (no SendMessage available to coordinate live
teammates sharing one working directory/git branch), the generator did not spawn
an agent team for this group — it implemented all 9 stories itself, sequentially,
in dependency-safe order: E1-S3 -> E1-S5 -> E1-S4 -> E2-S1 -> E3-S1 -> E4-S1 ->
E5-S1 -> E6-S1 -> E7-S1 (schema.sql grown incrementally by the story that first
needs each table; each of E2-S1 through E6-S1 appends only its own table(s)).
One commit per story on feat/group-b-foundations, TDD throughout (failing test
first, verified failure reason, then implementation, verified pass).

Notable in-flight findings (not failures — both self-corrected within the same
story's work, no rework across stories):
  - E1-S4: initial deps.py had current_principal() call get_settings() at module
    scope instead of receiving Settings via Depends() — the integration test
    caught this immediately (all role/ownership-positive cases returned 401
    because the token was verified against real-env settings, not the test's
    constructed settings). Fixed by making settings itself a FastAPI dependency
    (Depends(get_settings)), overridable via app.dependency_overrides in tests.
  - E1-S1 (extended in E1-S4): added a `_row_to_subscription` helper to
    subscriber_repository.py speculatively before any caller needed it; caught
    as dead code before commit and removed (no AC in E2-S1 requires reading back
    a Subscription; a future story that needs it will add it when it does).
  - E7-S1: activation_funnel_counts' three middle stages (kyc_passed,
    dealer_passed, mnp_passed) are documented as equal to activated, not
    fabricated as distinct — the data model (per E2-S3's own spec) records only
    whole-attempt pass/fail with no persisted signal for which individual rule a
    rejected attempt failed at. Documented in the repository module's docstring
    and the test file's module docstring rather than silently faked.

Result: 129 tests, 100% line coverage across the entire backend (546 statements),
ruff clean, mypy --strict clean, zero upward-layer imports (grep-verified for all
five layer boundaries). All commits on feat/group-b-foundations, merged --no-ff
into develop. Awaiting evaluator review (not self-assessed by the generator).
