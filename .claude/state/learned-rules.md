# Learned Rules
<!-- Monotonic — rules are NEVER deleted. Only add new rules. -->
<!-- Format: Each rule includes Impact, Pattern, Mistake description, Anti-Pattern code, Better Approach code, Rule, and Applied-in fields. See .claude/skills/auto/SKILL.md SECTION 12 for full format. -->

## Rule 1: Never spawn a teammate that blocks on an approval message the coordinator cannot send

- **Source:** Group A, Stories E1-S1 + E1-S2, Iteration 1
- **Impact:** Both parallel teammates stalled with zero files written and zero commits — a full sprint group's worth of spawn overhead produced no usable output; the coordinator had to intervene mid-task, and the generator had to abandon both agents and reimplement everything itself from scratch in the same session.
- **Pattern:** Generator (and the Implement skill it follows) spawned teammates with an explicit instruction to "present a plan and STOP — wait for coordinator approval before writing any code." The generator's own tool grant (Read, Write, Edit, Glob, Grep, Bash, Agent) does not include SendMessage. A fresh `Agent` call never resumes a previously spawned agent — it starts a new agent with no memory of the prior run. So there was no mechanism to deliver the approval the teammates were told to wait for.

### Mistake
The teammate prompts said: "Stop and wait — I (the coordinator) will reply with approval or requested changes before you write any code." This assumed a SendMessage-style channel back to the running agent existed for the spawning role. It does not exist in this agent's toolset. The teammates correctly followed instructions and stopped; the generator had no way to unblock them.

### Anti-Pattern (Avoid This)
```
Agent({
  subagent_type: "general-purpose",
  name: "teammate-x",
  prompt: "... Reply with your PLAN ONLY. Do NOT write or edit any files yet.
           Stop and wait — I will reply with approval before you write any code."
})
# Coordinator has no SendMessage tool -> teammate waits forever, no code, no commit.
```

### Better Approach
```
Agent({
  subagent_type: "general-purpose",
  name: "teammate-x",
  prompt: "... Before writing code, restate your plan (files, signatures, test
           list) as the first section of your final report so the coordinator
           can review it post-hoc against the diff you produce. Then follow
           strict TDD end-to-end in this same run: write failing tests, implement,
           verify green, run lint/typecheck/coverage, and commit — all in one
           continuous run. Do not stop mid-task waiting for a follow-up message."
})
# Coordinator reviews the plan-section + diff + commit together after the run
# completes, and can still reject/redo the work — just not via a mid-run gate
# it cannot fulfill with its actual tool grant.
```

- **Rule:** Before instructing any spawned teammate to stop and wait for approval mid-task, confirm the spawning agent's own tool list actually includes a way to message a running agent (e.g., SendMessage). If it does not, do not use a blocking plan-approval gate — require the plan as the first section of a single continuous run (plan -> TDD -> implement -> verify -> commit), and review it post-hoc via the committed diff instead.
- **Applied in:** generator agent, `.claude/skills/implement/SKILL.md` (Step 5's "await plan approval before writing any code" instruction must be read as "confirm SendMessage is available before choosing a blocking gate").

