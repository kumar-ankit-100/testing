# Failure Log
<!-- Append-only. Used for pattern detection → learned rules extraction. -->
<!-- When 2+ entries share the same Category, extract a Learned Rule to .claude/state/learned-rules.md -->

<!-- ENTRY FORMAT (copy this for each new failure):

## Group {ID} — Failure #{N}
- **Date:** {ISO 8601}
- **Category:** {lint_format | type_error | test_failure | import_error | coverage_drop | api_check_fail | playwright_fail | design_score_low | docker_fail | architecture_drift}
- **Story:** {story ID}
- **Attempt 1:**
  - Error: {error message with file:line if available}
  - Fix: {what was tried}
  - Result: FAIL — {why it failed}
- **Attempt 2:**
  - Error: {error message}
  - Fix: {what was tried}
  - Result: FAIL — {why it failed}
- **Attempt 3:**
  - Error: {error message}
  - Fix: {what was tried}
  - Result: FAIL — 3 attempts exhausted
- **Escalation:** User notified. Marked BLOCKED. Skipped to next group.
- **Pattern:** {describe the recurring pattern if visible}

-->

## Group A — Failure #1
- **Date:** 2026-09-30
- **Category:** architecture_drift (closest fit — this is a teammate-coordination/tooling-capability gap, not a code defect; no failures.md category exists for it yet)
- **Story:** E1-S1, E1-S2 (both teammates affected identically)
- **Attempt 1:**
  - Error: Spawned teammate-types (E1-S1) and teammate-config (E1-S2) via the Agent tool with instructions to present a plan and stop/wait for coordinator approval before writing code, per the Implement skill's plan-approval gate.
  - Fix: N/A — this was the initial approach, not a fix.
  - Result: FAIL — the generator's tool grant has no SendMessage, so the approval the teammates were told to wait for could never be delivered. A new Agent call starts a fresh agent, it does not resume the waiting one. Both teammates stalled; zero files written, zero commits. Coordinator observed only scaffolding on disk and flagged it.
- **Escalation:** Not a 3-attempt exhaustion — root-caused on first occurrence (tooling capability is a deterministic fact, not a flaky retry candidate). Corrective action: abandoned both stuck teammates, generator implemented E1-S1 and E1-S2 directly via strict TDD in the same session, committed on feat/group-a-types-config, merged --no-ff into develop (d62e740). Promoted directly to Learned Rule 1 rather than waiting for a second occurrence, since the failure is 100% reproducible any time this exact gate pattern is used and the cost of a second occurrence (another fully-stalled sprint group) is high.
- **Pattern:** Any agent whose tool grant excludes SendMessage must not design a teammate workflow around "stop and wait for a follow-up approval message" — see Learned Rule 1.
