---
name: run-all
description: >
  Walk the Work Package INDEX in the calling session with parallel
  dispatch (up to max_parallel concurrent executors per batch, gated
  by dependency-graph eligibility). Usage: /sulis-execution:run-all.
  The loop runs inline in the calling session — not via a separate
  orchestrator subagent — because agent-tree-depth limits prevent
  subagents from reliably spawning further subagents.
---

# /sulis-execution:run-all

Walk the Work Package INDEX and ship every ready WP atomically, with
parallel dispatch of graph-independent WPs.

## How to invoke (MUST — run the loop inline, with parallel batching)

**This is the marketplace's load-bearing dispatch logic.**

When this skill loads, **YOU (the calling session) run the dispatch
loop directly**. Do NOT call `Agent({subagent_type:
"sulis-execution:orchestrator", ...})` first. The orchestrator agent
file is architectural-intent reference only — Claude Code's runtime
treats spawned subagents as leaves of the agent tree, so an
orchestrator subagent could not dispatch executor subagents
(production failure observed 2026-05-18).

The calling session DOES have Agent at the top level. So the loop
runs in the calling session; the calling session spawns multiple
executors in parallel as its own subagents; each executor's Step 11
spawns the security-reviewer as its subagent. That's one level deep
for executors and two levels deep for the security-reviewer — both
within Claude Code's depth limits.

### The parallel loop

```
loop:
    1. Read .architecture/{project}/work-packages/INDEX.md.

    2. Read INDEX header for max_parallel (default 3 if absent).
       Example header:
           ## Orchestrator Config
           max_parallel: 3

    3. Read .architecture/{project}/work-packages/BLOCKER-*.md
       (any existing blockers).

    4. Build the ready set:
       - All WPs with status == "pending"
       - AND all their dependsOn WPs have status == "done"
       - EXCLUDE status == "auto-draft" (await founder disposition
         via concierge slice-end review)
       - EXCLUDE status == "blocked" / "cancelled" /
         "dependency_blocked"

    5. If ready set is empty:
       - If any WPs have status == "auto-draft" → surface count +
         source-finding IDs to concierge / founder; exit.
       - If any WPs remain "pending" (deps not met) → blocked on
         dependencies; surface what's blocking; exit.
       - If no WPs remain pending and no auto-drafts → all done;
         celebrate; exit.

    6. Compute the parallel-eligible subset (cap at max_parallel):

       Greedy selection — iterate ready set in lowest-sequence_id
       order; pick a WP if it satisfies ALL of these vs every WP
       already picked for THIS batch:
           (a) Neither dependsOn the other (transitively).
           (b) Declared file scope (from WP Contract section)
               doesn't overlap.
           (c) They don't share a dependsOn descendant currently
               in the same batch (prevents racing two children
               of the same parent on the same descendant outcome).
           (d) **Migration-lock serialisation (v0.8.1+).** No WP
               with `requires_migration_lock: true` in its
               frontmatter is included unless the batch contains
               EXACTLY that one WP. If the next-ready WP has the
               flag, the batch is just that one WP — dispatch
               solo, wait for completion, then continue. This
               handles WPs that touch shared persistent state
               non-idempotently (schema migrations, database
               seeds, Redis flushes) where parallel execution
               would deadlock, race on row locks, or leave the
               schema in an inconsistent state.

       Stop when batch has max_parallel WPs OR ready set is
       exhausted. Single-WP batch (size 1) is fine — sequential
       fallback when no parallelism is available, or required
       serialisation when a migration-locked WP is up.

    7. Mark each picked WP status: in_progress in INDEX with
       timestamp.

    8. Dispatch ALL picked WPs in a SINGLE message containing
       multiple Agent tool_use blocks — Claude Code runs them
       concurrently:

       Agent({
         subagent_type: "sulis-execution:executor",
         description: "Ship WP-007 end-to-end",
         model: <executor_model from WP frontmatter, if present>,
         prompt: """<executor brief per below>""",
       })
       Agent({
         subagent_type: "sulis-execution:executor",
         description: "Ship WP-008 end-to-end",
         model: <executor_model from WP frontmatter, if present>,
         prompt: """<executor brief per below>""",
       })
       Agent({
         subagent_type: "sulis-execution:executor",
         description: "Ship WP-009 end-to-end",
         model: <executor_model from WP frontmatter, if present>,
         prompt: """<executor brief per below>""",
       })

       Send all three in one message. Claude Code dispatches them
       in parallel; the calling turn blocks until ALL return.

    9. Per-WP executor brief (substitute WP-NNN, project, etc.):

       You are dispatched by the run-all loop (parallel batch
       of N) to ship WP-NNN through Steps 1-11 of the lifecycle.
       Step 12 is the calling session's responsibility (v0.8.3+);
       you complete Step 11 and exit cleanly.

       WP file: .architecture/{project}/work-packages/WP-NNN-<title>.md
       INDEX:   .architecture/{project}/work-packages/INDEX.md
       TDD:     .architecture/{project}/TDD.md
       ADRs:    .architecture/{project}/adrs/

       Continuation Discipline applies (see agents/executor.md):
       do not return control until Step 11 succeeds (journal-
       recorded) OR a BLOCKER is written. Use the v0.8.3
       background-poller pattern for steps 8/9/10 — kick off
       run_in_background:true Bash with sleep 300 inside; the
       harness auto-notifies you when complete. Step 11 invokes
       sulis-security:security-reviewer via Agent — the executor's
       one allowed sub-Agent call.

       You are running in your own git worktree (Step 1 creates
       it). Parallel peers are running their own worktrees. No
       file-system collision between you.

       If the journal at .architecture/{project}/work-packages/
       .executor-WP-NNN.md exists with an incomplete tail,
       resume from the last started-but-not-completed step.

       Output: journal updated through Step 11 with Completed
       timestamp on the Step 11 trace row AND a populated
       ## Post-deploy verification section. The calling session
       will read the journal and perform Step 12 (acceptance
       evidence + INDEX update + worktree removal) inline.

       Or: BLOCKER-WP-NNN.md written; INDEX status: blocked.

       Return when Step 11 is journal-recorded OR a BLOCKER is
       written. Do NOT do Step 12 yourself.

   10. Wait for ALL parallel Agent calls to return. Claude Code's
       Agent tool blocks the calling turn until every parallel
       call resolves.

   11. For each executor outcome, do the calling session's
       responsibilities (Step 12 inline, or error classification).
       Read the executor's journal at
       .architecture/{project}/work-packages/.executor-WP-NNN.md
       to determine which outcome:

       (a) Step 11 complete with non-CRITICAL verdict — Step 11
           trace row has Completed timestamp; ## Post-deploy
           verification section is populated with PASS / CONCERN /
           ADVISORY (not CRITICAL); INDEX status is still in_progress.

           → DO STEP 12 INLINE per references/lifecycle.md Step 12.

           Inline mechanics (Bash + Edit per WP):

             Bash:
               # Extract evidence from journal
               JOURNAL=.architecture/$PROJECT/work-packages/.executor-WP-NNN.md
               BRANCH=$(grep '^- Branch:' "$JOURNAL" | head -1 | awk '{print $3}')
               MERGE_SHA=$(grep 'Squash-merge SHA' "$JOURNAL" | head -1 | awk '{print $NF}')
               DEPLOY_URL=$(grep 'Deployment URL' "$JOURNAL" | head -1 | awk '{print $NF}')
               # ... etc.

             Edit:
               WP file at .architecture/$PROJECT/work-packages/WP-NNN-*.md
               Append ## Acceptance Evidence block with the journal data.

             Edit:
               INDEX.md
               Change WP-NNN row's status from in_progress to done.

             Bash:
               git worktree remove ../wp-NNN-worktree

           Emit plain-English status: "WP-NNN done — deployed and
           healthy at <url>. Security: <verdict>."

       (b) BLOCKER written — INDEX status is already blocked
           (executor wrote that during Step 11 or earlier). Skip
           Step 12 (WP not done). Propagate dependency_blocked to
           transitive descendants in the next loop iteration.

       (c) Step 11 NOT complete (no Completed timestamp on Step 11
           trace row, OR ## Post-deploy verification section
           missing/incomplete) — classify as "error". Executor
           parked late or errored mid-lifecycle. Do NOT do Step 12
           (substantive work not proven complete). Halt the loop
           entirely. Surface clearly:

             "WP-NNN: executor returned before Step 11 completed.
              Likely parked late in lifecycle. Re-dispatch via
              /sulis-execution:run-wp WP-NNN to resume from journal."

   12. Emit per-batch plain-English status to the founder /
       concierge / calling session:
       - "Starting N in parallel: WP-A (title), WP-B (title), ..."
       - As each completes (in the order they return):
         "WP-A done — deployed and healthy at <url>. N-1 still in
          flight."
       - When the batch returns:
         "Batch complete. M done, K blocked. Starting next batch:
          WP-X, WP-Y, ..."

   13. Goto step 1.
```

## Concurrency limit configuration

Default: `max_parallel: 3`. Configurable per-project via the INDEX
header. To change:

```yaml
## Orchestrator Config
max_parallel: 5   # If staging cluster + machine can handle more.
```

Three is a safe starting point covering most graph-parallelisable
cases without overwhelming staging. The founder can dial up as
confidence grows.

## Per-WP model override (opt-in)

Optional WP frontmatter field:

```yaml
executor_model: opus | sonnet | haiku
```

When present, the run-all skill includes the `model` parameter in
that WP's Agent call:

```
Agent({
  subagent_type: "sulis-execution:executor",
  model: "haiku",
  ...
})
```

When absent (default behaviour), no `model` parameter is sent and
the executor inherits the calling session's model (typically Opus).
**No automatic model substitution.** The override is purely opt-in;
defaults are unchanged from v0.7.1.

## Per-executor isolation

Each parallel executor uses its own `git worktree` per GIT-07. Worktree
paths use the WP ID: `../wp-NNN-worktree/`. Concurrent worktrees do
not share working files; they share only the bare repository's git
objects + refs (which git handles thread-safely).

Per-executor journals live at `.architecture/{project}/work-packages/
.executor-WP-NNN.md` — one per WP, no cross-WP collisions.

## Failure isolation

One executor's BLOCKER doesn't affect concurrent peers. Each executor
runs its own OODA spiral (per executor-loop-standard.md EL-01..08)
independently. When the parallel batch returns, the calling session
sees a mix of outcomes (some done, some blocked) and updates INDEX
accordingly.

The next loop iteration uses the updated INDEX to compute the new
ready set. Transitively-dependent descendants of blocked WPs get
`dependency_blocked`; the loop continues with what's still ready.

## When NOT to use

- **One specific WP.** Use `/sulis-execution:run-wp WP-NNN` — single-
  WP dispatch (also runs Agent in the calling session; no parallel
  logic needed).
- **Retry a blocked WP.** Use `/sulis-execution:retry WP-NNN` after
  the external blocker is resolved.

## Gotchas

- The skill expects a non-empty
  `.architecture/{project}/work-packages/INDEX.md`. If empty,
  surface: *"INDEX is empty. Run `/sea:decompose` first."*
- `max_parallel: 1` in INDEX header is a valid configuration —
  forces sequential dispatch. Useful when staging capacity is
  constrained or the founder wants one-at-a-time observability.
- An executor's Agent call that returns mid-lifecycle (no Step 12
  success AND no BLOCKER) is classified as `error` and halts the
  entire loop. This is intentional — silent advance past a
  half-finished WP is the failure mode v0.6.1 + v0.7.1 fixed.
- WPs with declared file scope that's *very* broad (e.g. "everywhere
  under src/") will conflict with every other WP and effectively
  serialise. SEA's decompose should produce narrower file scopes;
  if your WPs systematically over-claim scope, that's a SEA
  configuration concern, not a run-all issue.
- The depth chain via concierge: concierge (depth 0) → run-all skill
  (inline in concierge) → executor (depth 1) → security-reviewer at
  Step 11 (depth 2). Two deep at deepest from concierge. Same chain
  one level shallower from a top-level user session. Both work.

## See also

- `agents/executor.md` — what the loop spawns per WP.
- `agents/orchestrator.md` — architectural-intent reference for the
  dispatch logic (not actively invoked).
- `references/lifecycle.md` — the 12-step contract per WP.
- `/sulis-execution:run-wp WP-NNN` — single-WP dispatch.
- `/sulis-execution:status` — read-only INDEX summary.
- `/sulis-execution:retry WP-NNN` — re-run a blocked WP.
