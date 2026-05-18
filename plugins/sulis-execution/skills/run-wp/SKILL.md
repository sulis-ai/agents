---
name: run-wp
description: >
  Spawn the executor agent on a single Work Package. Usage:
  /sulis-execution:run-wp WP-NNN. The skill's load-bearing action is
  invoking the Agent tool — the executor agent then takes over and
  runs the 10-step lifecycle under its own context window and
  Continuation Discipline.
---

# /sulis-execution:run-wp

This skill **spawns the executor agent** to ship one Work Package
atomically to `dev`.

## How to invoke (MUST — do not run the executor's work inline)

When this skill is loaded, **your sole action is to call the Agent
tool with `subagent_type: "sulis-execution:executor"`**. Do not run
the lifecycle steps inline in your own session — that defeats the
executor's Continuation Discipline (the executor must own its own
turn boundary and the polling loops). The skill exists to dispatch
the agent, not to replace it.

### The dispatch call

Given the user invokes `/sulis-execution:run-wp WP-NNN`:

1. Read the WP frontmatter. If it has an `executor_model` field
   (optional; one of `haiku | sonnet | opus`), include the `model`
   parameter in the Agent call. Otherwise omit `model` (the executor
   inherits the calling session's model — typically Opus).

```
Agent({
  subagent_type: "sulis-execution:executor",
  description: "Ship WP-NNN end-to-end",
  model: <executor_model from WP frontmatter, if present>,
  prompt: """
You are dispatched to ship WP-NNN through the full 10-step atomic
lifecycle. Read your agent prompt (agents/executor.md) for the full
contract; the user has already approved the dispatch.

WP file: .architecture/{project}/work-packages/WP-NNN-<title>.md
INDEX:   .architecture/{project}/work-packages/INDEX.md
TDD:     .architecture/{project}/TDD.md
ADRs:    .architecture/{project}/adrs/

Continuation Discipline applies: do not return control until step 10
succeeds OR a BLOCKER is written. Use blocking Bash polling for
steps 7-10 per references/lifecycle.md.

If the journal at .architecture/{project}/work-packages/.executor-WP-NNN.md
exists and shows an incomplete tail, resume from the last started-but-
not-completed step. Do not start over.

Output contract:
- On success: ## Acceptance Evidence appended to the WP file;
  INDEX status: done; worktree removed.
- On escalation: BLOCKER-WP-NNN.md written; INDEX status: blocked.

Return ONLY when one of those output conditions is true.
""",
})
```

Replace `{project}` and `<title>` based on the actual project path
and WP title. The `subagent_type` value is **exactly**
`sulis-execution:executor` — that's the fully-qualified agent name.

### What you do NOT do in this skill's session

- **Do not read the WP file yourself.** The executor reads it.
- **Do not run `git worktree add`.** The executor does it.
- **Do not write tests, code, lint, commit, push, poll CI, merge,
  deploy, or health-check.** All of those are the executor's job.
- **Do not summarise the executor's output for the user.** When the
  executor's Agent tool call returns, surface its terminal status
  line directly. The concierge (if upstream) does the founder
  translation; this skill is power-user-facing and the executor's
  status line is already plain-English.

### What you DO in this skill's session

1. Parse the WP-NNN argument from the user's invocation.
2. Verify the WP file exists at the expected path; if not, surface
   a clear error and exit.
3. Make the Agent tool call above.
4. When it returns, surface the executor's terminal status line.

That is the entire skill. Three steps. The executor does the work.

## When to use this skill

- **Single-WP execution** — when you want to ship one specific WP
  rather than walking the whole INDEX. The orchestrator's
  `/sulis-execution:run-all` is the normal multi-WP path; this is
  the single-shot.
- **Re-running a blocked WP** after fixing an external blocker. The
  semantically-clearer alternative for this case is
  `/sulis-execution:retry WP-NNN`, which archives the prior BLOCKER
  and dispatches a fresh executor.

## Gotchas

- If the WP's `primitive` is outside the v0.5 scope (the file
  doesn't yet define the scaffold), the executor escalates
  immediately with a primitive-coverage BLOCKER. The skill itself
  doesn't pre-check this — the executor's primitive-selection check
  at step 3 handles it.
- If the project's git remote isn't reachable, the executor will
  fail at step 6 (push). That's a connectivity issue surfaced by
  the executor; not the skill's problem.
- If a prior executor session left an in-flight WP (journal shows
  steps complete up to step N, but no step 10 success and no
  BLOCKER), invoking this skill resumes from step N+1. Do not
  manually delete the journal to "start fresh" — the journal is the
  audit trail.

## See also

- `agents/executor.md` — the agent this skill spawns.
- `references/lifecycle.md` — the 10-step contract.
- `references/self-heal-budget.md` — per-failure-type budgets.
- `/sulis-execution:run-all` — orchestrator path for the whole INDEX.
- `/sulis-execution:status` — read-only INDEX summary (skill, not
  agent).
- `/sulis-execution:retry` — re-run a blocked WP with archive.
