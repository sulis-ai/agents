---
name: run-all
description: >
  Walk the Work Package INDEX in the calling session. Pick the next
  ready WP (no unmet dependencies), spawn the executor agent for it
  via the Agent tool, wait for completion, mark INDEX, continue.
  Usage: /sulis-execution:run-all. The loop runs **inline in the
  calling session** — not via a separate orchestrator subagent —
  because agent-tree-depth limits in Claude Code prevent subagents
  from reliably spawning further subagents.
---

# /sulis-execution:run-all

Walk the Work Package INDEX and ship every ready WP atomically.

## How to invoke (MUST — run the loop inline, not via a subagent)

**This is the marketplace's most important architectural decision.**

When this skill loads, **YOU (the calling session) run the dispatch
loop directly**. Do NOT call `Agent({subagent_type:
"sulis-execution:orchestrator", ...})` first and let the orchestrator
spawn executors. That two-deep pattern fails in Claude Code's
agent-tree-depth model: spawned subagents lose the Agent tool, so
the orchestrator subagent cannot spawn executor subagents.

The calling session DOES have Agent at the top level. So the loop
runs in the calling session, the calling session spawns executors as
its own subagents (one deep, which works), the calling session reads
each executor's exit and advances.

### The loop

```
loop:
    1. Read .architecture/{project}/work-packages/INDEX.md.

    2. Read .architecture/{project}/work-packages/BLOCKER-*.md (any
       existing blockers).

    3. Build the ready set:
       - All WPs with status == "pending"
       - AND all their dependsOn WPs have status == "done"
       - EXCLUDE status == "auto-draft" (v0.7+; these await
         founder disposition via the concierge slice-end review)
       - EXCLUDE status == "blocked" / "cancelled" /
         "dependency_blocked"

    4. If ready set is empty:
       - If any WPs have status == "auto-draft" → surface to
         the founder (via the concierge if active, else inline
         plain-English) the count + source-finding IDs; ask for
         disposition. Exit the loop. The orchestrator does not
         decide auto-draft disposition.
       - If any WPs remain "pending" (deps not met) → blocked on
         dependencies. Surface what's blocking. Exit.
       - If no WPs remain pending and no auto-drafts → all done.
         Celebrate. Exit.

    5. Pick the next WP:
       - Lowest sequence_id first (deterministic, debuggable).
       - Ties broken by ID alphabetical.

    6. Mark the WP status: in_progress in INDEX with a timestamp.

    7. Spawn the executor as a subagent of this calling session:

       Agent({
         subagent_type: "sulis-execution:executor",
         description: "Ship WP-NNN end-to-end",
         prompt: """
   You are dispatched by the run-all loop to ship WP-NNN through
   the full 12-step atomic lifecycle.

   WP file: .architecture/{project}/work-packages/WP-NNN-<title>.md
   INDEX:   .architecture/{project}/work-packages/INDEX.md
   TDD:     .architecture/{project}/TDD.md
   ADRs:    .architecture/{project}/adrs/

   Continuation Discipline applies (see agents/executor.md):
   do not return control until Step 12 success OR a BLOCKER is
   written. Use blocking Bash polling for steps 7-10 per
   references/lifecycle.md. Step 11 invokes sulis-security:
   security-reviewer via Agent — this is the executor's one
   allowed sub-Agent call.

   If the journal at .architecture/{project}/work-packages/
   .executor-WP-NNN.md exists with an incomplete tail, resume
   from the last started-but-not-completed step.

   Output: ## Acceptance Evidence appended; INDEX status: done;
   worktree removed. Or: BLOCKER-WP-NNN.md written; INDEX
   status: blocked.

   Return ONLY when one of those is true.
   """,
       })

    8. Wait for the executor's Agent call to return. (Agent calls
       block by default — the executor's "Continuation Discipline"
       rule ensures the call only returns once the WP is done or
       blocked.)

    9. Read the executor's outcome:
       - Step 12 success — WP is done. INDEX status: done (the
         executor wrote that). Continue.
       - BLOCKER written — INDEX status: blocked (the executor
         wrote that). Continue (the blocked WP doesn't block
         others unless they depend on it transitively).
       - Neither (executor exited mid-lifecycle) — classify as
         "error". Halt entirely. Surface to the founder.

   10. After a "blocked" outcome:
       - Find all WPs whose dependsOn (transitively) includes the
         blocked WP. Mark them status: dependency_blocked with a
         pointer to the blocker. They don't consume executor
         dispatches but stay visible in INDEX.

   11. Emit one plain-English status line for the founder /
       calling session:
       - "WP-NNN done — deployed and healthy at <url>."
       - "WP-NNN blocked — <plain-English reason from BLOCKER>."
       - "Starting WP-MMM next — <plain title>."

   12. Goto step 1.
```

## Note on agent-tree depth

The "orchestrator agent" pattern (run-all spawns orchestrator;
orchestrator spawns executors) does NOT work in Claude Code's
runtime because subagents spawned via Agent() lose access to the
Agent tool — they're leaves of the agent tree. The orchestrator
subagent would run, read INDEX, then fail to dispatch executors,
returning with "no permission to spawn workers."

`agents/orchestrator.md` is kept in the plugin as the
architectural-intent reference for the dispatch logic encoded here.
It's the same logic, just expressed as a standalone agent spec.
Some future runtime version or external execution context (a CI
worker, a dedicated agent runtime) may use it directly. **In Claude
Code today, this skill is the orchestrator**.

The executor agent itself IS allowed one sub-Agent call — for
spawning sulis-security:security-reviewer at Step 11. That's one
level deep from the executor (which is one level deep from the
calling session), so two-deep total. Claude Code allows the
executor → security-reviewer path because the executor is "real"
work, not coordination. The boundary is "subagents can do one final
spawn for a specific Step-11 contract, not arbitrary sub-orchestration."

## When to use this skill

- **The default Phase 5 path.** Founder approves "let it walk the
  index" via the concierge; concierge invokes this skill in the
  calling session.
- **Power user path.** Set up a session, run this command, watch
  the loop dispatch executors.

## When NOT to use

- **One specific WP.** Use `/sulis-execution:run-wp WP-NNN` — the
  same single-WP dispatch (also runs Agent in the calling session).
- **Retry a blocked WP.** Use `/sulis-execution:retry WP-NNN`
  after the external blocker is resolved.

## What it does NOT do

- **It does not promote `dev → main`.** That's the founder's
  ceremony, surfaced by the concierge.
- **It does not retry blocked WPs.** Use
  `/sulis-execution:retry WP-NNN` after fixing the external
  blocker.
- **It does not dispatch auto-draft WPs.** They await founder
  disposition via the concierge's slice-end review.
- **It does not parallelise executor dispatches (v0.7).** v0.8+
  will allow opt-in parallelism for WPs that share no file scope
  AND no shared dependsOn descendant. v0.7 is sequential — one
  executor at a time, waiting for each to complete before
  dispatching the next.

## Gotchas

- The skill expects a non-empty
  `.architecture/{project}/work-packages/INDEX.md`. If empty,
  surface clearly: *"INDEX is empty. Run `/sea:decompose` first."*
- If the calling session is itself a subagent (e.g. spawned by the
  concierge), this skill still works **only if** the concierge was
  spawned at the top level. The concierge → run-all chain is one
  level deep, executor is two levels deep, security-reviewer at
  Step 11 is three levels deep. Claude Code generally allows three
  levels; deeper chains may break.
- If an executor's Agent call returns mid-lifecycle (no Step 12
  success AND no BLOCKER), that's a Continuation Discipline
  violation — classify as "error" and halt entirely.

## See also

- `agents/executor.md` — what the loop spawns per WP.
- `agents/orchestrator.md` — architectural-intent reference for
  the dispatch logic (not actually invoked in Claude Code).
- `references/lifecycle.md` — the 12-step contract per WP.
- `/sulis-execution:run-wp WP-NNN` — single-WP dispatch.
- `/sulis-execution:status` — read-only INDEX summary (inline; no
  agent spawn).
- `/sulis-execution:retry WP-NNN` — re-run a blocked WP.
