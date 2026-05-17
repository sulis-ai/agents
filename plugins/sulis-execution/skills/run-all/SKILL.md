---
name: run-all
description: >
  Spawn the orchestrator agent to walk the full Work Package INDEX.
  The orchestrator picks the next ready WP, spawns the executor for
  it, advances on completion, records blockers, continues until the
  ready set is exhausted. Usage: /sulis-execution:run-all.
---

# /sulis-execution:run-all

This skill **spawns the orchestrator agent** to walk the entire WP
INDEX and ship every ready WP atomically.

## How to invoke (MUST — do not run orchestration inline)

When this skill is loaded, **your sole action is to call the Agent
tool with `subagent_type: "sulis-execution:orchestrator"`**. Do not
read the INDEX, pick a WP, or dispatch executors directly in your
own session — that defeats the orchestrator's purpose (it must own
the dependency walk under its own context window and re-dispatch
strategy).

### The dispatch call

```
Agent({
  subagent_type: "sulis-execution:orchestrator",
  description: "Walk the WP INDEX and ship each ready WP atomically",
  prompt: """
You are dispatched to walk the Work Package INDEX, pick the next
ready WP (no unmet dependencies), and ship it via the executor
agent. Continue until the ready set is exhausted or a real error
halts the loop.

INDEX:   .architecture/{project}/work-packages/INDEX.md
Existing BLOCKERs: .architecture/{project}/work-packages/BLOCKER-*.md

Your contract is in agents/orchestrator.md. Key points:
- Spawn the executor via Agent({subagent_type: "sulis-execution:executor"})
  for each ready WP. Do not run executor work inline.
- After each executor exit: read its outcome (done | blocked | error)
  and update INDEX accordingly.
- Propagate dependency_blocked transitively when a WP blocks.
- Sequential dispatch in v0.4-v0.5; parallelism is opt-in via WP
  frontmatter and lands in a later release.
- Halt entirely on executor "error" (mid-lifecycle return, crash);
  surface plainly.
- Emit one plain-English status line per state transition for the
  invoking session.

Return when ready set is empty (all WPs done or blocked) or a real
error halts the loop.
""",
})
```

### What you do NOT do in this skill's session

- **Do not read INDEX.md directly.** The orchestrator does it.
- **Do not pick the next WP.** The orchestrator's dependency-walk
  logic does it.
- **Do not invoke the executor agent yourself.** The orchestrator
  does it for each ready WP.
- **Do not retry blocked WPs.** That's `/sulis-execution:retry`.

### What you DO in this skill's session

1. Verify INDEX.md exists at the expected path; if not, surface a
   clear error: *"INDEX.md not found. Run `/sea:decompose` first to
   produce work packages."*
2. Make the Agent tool call above.
3. When it returns, surface the orchestrator's terminal summary.

## When to use this skill

- **The default Phase 5 path.** Set up a session, run this command,
  watch the orchestrator walk the INDEX.
- **The concierge's spawn target.** When the concierge enters
  Phase 5 (Implement), it spawns this same orchestrator via Agent
  tool directly — bypassing the skill — for the same effect.

## Gotchas

- An empty INDEX surfaces a clear error. No silent no-op.
- A WP with a primitive outside the v0.5 scope (none currently —
  v0.5 covers all 22) will not trip the orchestrator; the executor's
  primitive-selection check handles it.
- An in-flight WP (orchestrator was previously running, exited
  uncleanly) will be re-picked by the dependency walk; the
  executor's journal-resume logic picks up where the prior
  executor parked.

## See also

- `agents/orchestrator.md` — the agent this skill spawns.
- `agents/executor.md` — what the orchestrator dispatches per WP.
- `/sulis-execution:run-wp WP-NNN` — single-WP dispatch path.
- `/sulis-execution:status` — read-only INDEX summary.
- `/sulis-execution:retry WP-NNN` — re-run a blocked WP.
