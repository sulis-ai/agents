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
executors in parallel as its own subagents (Steps 1-7); after the
executors return, the calling session itself spawns the
security-reviewer for Step 11 (v0.9.0+). All Agent calls are one
level deep from the calling session — well within Claude Code's
depth limits.

### Resolving wpx-* tool paths (MUST — first action, v0.10.1+)

The wpx-* CLI tools (journal, pipeline, blocker, step12, …) live
inside the sulis-execution plugin. When the plugin is installed in
a downstream project, the scripts are at
`~/.claude/plugins/cache/sulis-ai-agents/sulis-execution/<version>/scripts/`,
NOT at a project-relative path. You MUST resolve the tool directory
ONCE at the start of every dispatch session, before reading the
INDEX or doing anything else, and capture the result as
`$WPX_DIR`:

```bash
WPX_DIR=$(
  find ~/.claude/plugins/cache \
    -name wpx-journal -type f \
    -path '*/sulis-execution/*/scripts/*' \
    2>/dev/null \
  | sort -r | head -1 | xargs -I{} dirname {} 2>/dev/null
)
# Dev fallback: marketplace repo cwd
if [ -z "$WPX_DIR" ] && [ -f "plugins/sulis-execution/scripts/wpx-journal" ]; then
  WPX_DIR="$(pwd)/plugins/sulis-execution/scripts"
fi
if [ -z "$WPX_DIR" ]; then
  echo "ERROR: cannot locate wpx-* scripts. Run: claude plugin install sulis-execution@sulis-ai-agents" >&2
  exit 1
fi
echo "WPX_DIR=$WPX_DIR"
```

Capture the printed `WPX_DIR` value into your working memory. Every
subsequent wpx-* invocation in this skill uses `"$WPX_DIR/wpx-NAME"`
— substitute the resolved literal path inline at each Bash call.
Environment variables do NOT persist between Bash tool invocations
in Claude Code, so the substitution happens in the prompt text the
agent sends to Bash, not in shell state.

The executor subagents you spawn have the same resolution preamble
in their own prompts (`agents/executor.md`) — they resolve
independently in their own contexts. You do NOT pass `$WPX_DIR` to
them; each subagent finds its own.

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

    9. Per-WP executor brief (v0.9.0+; substitute WP-NNN, project,
       etc.):

       You are dispatched by the run-all loop (parallel batch
       of N) to ship WP-NNN through Steps 1-7 of the lifecycle:
       worktree, plan generation (Step 1.5, v0.10.0+), RGB, docs,
       lint, commit, push. Steps 8-12 (CI poll, merge, deploy,
       health, smoke, security review, INDEX flip, acceptance
       evidence, worktree removal) are the calling session's
       responsibility — do NOT do them.

       At Step 1.5 you MUST emit a structured plan to the journal
       via `wpx-journal seed-plan` before starting Step 2 (RED).
       See agents/executor.md "Step 1.5 — Plan generation (MUST)"
       for the approach + item-list shape. The plan is the
       calling session's pre-execution audit surface.

       WP file: .architecture/{project}/work-packages/WP-NNN-<title>.md
       INDEX:   .architecture/{project}/work-packages/INDEX.md
       TDD:     .architecture/{project}/TDD.md
       ADRs:    .architecture/{project}/adrs/

       Continuation Discipline applies (see agents/executor.md):
       do not return control until Step 7 is journal-recorded
       (push succeeded; wpx-journal complete-step --step 7 called
       with the pushed SHA in --outcome) OR a BLOCKER is written
       via wpx-blocker. No polling boundaries inside your
       contract — Steps 1-7 are all synchronous; the calling
       session handles the long async waits at Steps 8-10.

       You are running in your own git worktree (wpx-worktree
       create at Step 1). Parallel peers are running their own
       worktrees. No file-system collision between you.

       Use wpx-* CLI tools for all bookkeeping (journal, blocker)
       per "Bookkeeping via wpx-* tools" in agents/executor.md.
       Direct Markdown edits to .executor-WP-NNN.md or BLOCKER-*.md
       are FORBIDDEN.

       If the journal at .architecture/{project}/work-packages/
       .executor-WP-NNN.md exists with an incomplete tail (read
       via wpx-journal read --field step-trace), resume from the
       last started-but-not-completed step.

       Output: journal updated through Step 7 with Completed
       timestamp; pushed branch + SHA in the Step 7 trace row.

       Or: BLOCKER-WP-NNN.md written via wpx-blocker.

       Return when Step 7 is journal-recorded OR a BLOCKER is
       written. Do NOT do Steps 8-12.

   10. Wait for ALL parallel Agent calls to return. Claude Code's
       Agent tool blocks the calling turn until every parallel
       call resolves.

   11. For each returned executor, classify the outcome by reading
       the journal at .architecture/{project}/work-packages/
       .executor-WP-NNN.md via:

           wpx-journal read --wp WP-NNN --project <slug> \
             --field step-7-status

       Three branches:

       (a) **Step 7 complete** (status: complete; outcome row
           records branch + pushed SHA) — proceed with Steps 8-12
           via the calling-session pipeline below.

       (b) **BLOCKER written** (BLOCKER-WP-NNN.md exists at
           .architecture/{project}/work-packages/) — surface its
           plain-English summary; flip INDEX to blocked:

               wpx-index flip-status --wp WP-NNN --project <slug> \
                 --to blocked --expected in_progress

           Then propagate dependency_blocked to descendants:

               wpx-index propagate-blocked --wp WP-NNN \
                 --project <slug>

           Skip Steps 8-12. Continue to next WP in the loop.

           Note: a Step 1.5 scope-guard BLOCKER (executor identified
           that the WP's Contract references files outside scope, or
           the plan would violate scope) lands here too — surface the
           plain-English summary normally; the upstream fix is for
           SEA to reconcile the WP Contract.

       (c) **Step 7 NOT complete AND no BLOCKER** (executor returned
           prematurely) — classify as "error". Halt the entire loop.
           Optionally check whether the journal has a populated
           `## Plan` section (read via `wpx-journal read --field plan`)
           to determine where the executor parked:

               "WP-NNN: executor returned before Step 7 completed
                and no BLOCKER was written. Plan: <N items, M done>.
                Likely parked at <step inferred from in-progress
                item>. Re-dispatch via /sulis-execution:run-wp WP-NNN
                to resume from journal."

           The plan in the journal makes the parked-state diagnosis
           specific. v0.10.0+ executors that have completed Step 1.5
           leave a readable item list showing exactly which item was
           in-progress when the session ended.

   12. **For each Step-7-complete WP, run the Steps 8-12 pipeline.**

       Read frontmatter to determine pipeline arguments:

           wpx-wp read-frontmatter --wp WP-NNN --project <slug> \
             --field '*'

       Capture: branch, smoke_test, deploy_workflow, staging_url,
       ci_poll_interval_seconds, post_deploy_verification,
       security_model, dev-sha-at-creation (from the sidecar at
       .architecture/{project}/work-packages/.executor-WP-NNN-dev-sha).

       **Step 8-10: invoke wpx-pipeline via top-level
       Bash(run_in_background:true).** This is the load-bearing
       v0.9.0 change — the wait happens in a deterministic Python
       script, not in an agent's turn. Typical wall time: 15-45 min.

           Bash({
             command: """"$WPX_DIR/wpx-pipeline" run \
                --wp WP-NNN --project <slug> \
                --branch feat/wp-NNN-<slug> \
                --worktree-path ../wp-NNN-worktree \
                --dev-sha-at-creation <sha-from-sidecar> \
                --deploy-workflow "<workflow name from frontmatter>" \
                --staging-url <staging-url> \
                --smoke-cmd "<smoke command from frontmatter>" \
                --repo <org/repo> \
                > /tmp/pipeline-WP-NNN.json 2> /tmp/pipeline-WP-NNN.log""",
             run_in_background: true,
             timeout: 5400000   # 90 min cap
           })

       The harness auto-notifies the calling session when the
       background Bash exits. **No polling, no sleep, no manual
       check.** Read /tmp/pipeline-WP-NNN.json on completion.

       Inspect the JSON. If `outcome: "blocker"`:

           # Write BLOCKER capturing the pipeline failure
           "$WPX_DIR/wpx-blocker" write \
             --wp WP-NNN --project <slug> \
             --title "<pipeline step> failed" \
             --step <8|9|10> \
             --trigger budget-exhausted \
             --observation @/tmp/pipeline-WP-NNN.log \
             --root-cause "<from blocker_reason>" \
             --scope out-of-scope \
             --plain-english "..." \
             --suggested-next "..."

           wpx-index flip-status --wp WP-NNN --project <slug> \
             --to blocked --expected in_progress
           wpx-index propagate-blocked --wp WP-NNN --project <slug>
           # Skip Steps 11-12; continue to next WP

       If `outcome: "success"`, proceed to Step 11.

       **Step 11: spawn the security-reviewer Agent.** Synchronous
       Agent call; ~5-15 min wall time.

           Agent({
             subagent_type: "sulis-security:security-reviewer",
             description: "Step 11 post-deploy verification for WP-NNN",
             model: <security_model from frontmatter, if present>,
             prompt: """
               Review the squash-merge at <merge_sha> on dev
               (deployed to <deploy_url>). Health: <health_status>.
               Smoke: <smoke_verdict>.

               Verify against the WP's Definition of Done. Categorise
               findings by severity (CRITICAL / CONCERN / ADVISORY).
               Return a structured verdict JSON in the format
               documented at plugins/sulis-security/agents/
               security-reviewer.md.
             """,
           })

       Parse the returned verdict. For each non-CRITICAL finding:

           # Register the finding (signature-hash dedup automatic)
           wpx-findings register --wp WP-NNN --project <slug> \
             --severity <CONCERN|ADVISORY> \
             --summary "<one-line>" \
             --file <path> \
             --evidence-json @/tmp/finding-N.json \
             --suggested-fix "<suggested fix>" \
             --primitive <SEC-NN>

           # If new (not is_duplicate), auto-draft the follow-up WP
           "$WPX_DIR/wpx-findings" auto-draft-wp --project <slug> \
             --source-finding <SF-NNN> \
             --source-wp WP-NNN \
             --auto-wp-id <WP-AUTO-NNN from register output> \
             --primitive <Secure|Harden|Instrument|Gate> \
             --severity <CONCERN|ADVISORY>

           # (v0.10.3+) Register the new auto-draft WP in INDEX so
           # downstream dispatch + wpx-step12 wrap can see it. The
           # tool reads the WP file's frontmatter (id, title,
           # primitive, dependsOn, blocks, status) and appends a row.
           # Status remains `auto-draft` — the founder promotes to
           # `pending` via the concierge's slice-end review.
           "$WPX_DIR/wpx-index" add-wp \
             --wp WP-AUTO-NNN --project <slug> --from-wp-file

       If CRITICAL findings exist, write a BLOCKER and stop (do NOT
       proceed to Step 12). Otherwise record the post-deploy verdict
       in the executor's journal:

           wpx-journal record-postdeploy --wp WP-NNN --project <slug> \
             --verdict PASS \
             --findings-summary "0 CRITICAL, N CONCERN, M ADVISORY"

       **Step 12: atomic wrap.** Composes acceptance evidence + INDEX
       flip + worktree remove into one transactional call.

           # Build pipeline-result file
           jq '.' /tmp/pipeline-WP-NNN.json > /tmp/pipeline-result-WP-NNN.json

           "$WPX_DIR/wpx-step12" wrap \
             --wp WP-NNN --project <slug> \
             --branch feat/wp-NNN-<slug> \
             --pipeline-result @/tmp/pipeline-result-WP-NNN.json \
             --worktree-path ../wp-NNN-worktree

       Emit plain-English status:

           "WP-NNN done — deployed and healthy at <deploy_url>.
            Security: PASS (N CONCERN, M ADVISORY auto-drafted as
            WP-AUTO-XXX for founder review)."

   13. Emit per-batch plain-English status to the founder /
       concierge / calling session:
       - "Starting N in parallel: WP-A (title), WP-B (title), ..."
       - As each completes (in the order they return):
         "WP-A done — deployed and healthy at <url>. N-1 still in
          flight."
       - When the batch returns:
         "Batch complete. M done, K blocked. Starting next batch:
          WP-X, WP-Y, ..."

   14. Goto step 1.
```

### v0.9.0 sequencing — sequential post-push, parallel pre-push

Steps 1-7 (the executor's contract) run in parallel: N executors
dispatched at once via N Agent tool_use blocks in a single message.
The harness runs them concurrently and the calling turn blocks until
all N return.

Steps 8-12 (the calling session's pipeline) run **sequentially per
WP** in v0.9.0 — the calling session invokes `wpx-pipeline` for the
first Step-7-complete WP, waits for the harness notification, then
proceeds. This preserves merge ordering on `dev` (avoids racing two
WPs trying to squash-merge concurrently) and keeps the calling
session's reasoning simple.

A future v0.9.1 may add concurrent `wpx-pipeline` invocations per WP
(N parallel `Bash(run_in_background:true)` calls; harness aggregates
notifications) when many WPs are in late stages simultaneously. For
v0.9.0, the sequential pattern is enough — most projects have
sub-five-WP batches and `wpx-pipeline` typically completes in 20-30
min, so the wall-clock benefit of concurrent pipelines is modest.

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
- An executor's Agent call that returns mid-lifecycle (no Step 7
  success AND no BLOCKER written via wpx-blocker) is classified as
  `error` and halts the entire loop. This is intentional — silent
  advance past a half-finished WP is the failure mode v0.6.1 +
  v0.7.1 + v0.9.0 each tightened.
- WPs with declared file scope that's *very* broad (e.g. "everywhere
  under src/") will conflict with every other WP and effectively
  serialise. SEA's decompose should produce narrower file scopes;
  if your WPs systematically over-claim scope, that's a SEA
  configuration concern, not a run-all issue.
- The depth chain via concierge (v0.9.0+): concierge (depth 0) →
  run-all skill (inline in concierge) → executor at depth 1 (Steps
  1-7) → calling session resumes → security-reviewer at depth 1
  (Step 11). All Agent calls one level deep from the concierge.
  Same shape one level shallower from a top-level user session.

## See also

- `agents/executor.md` — what the loop spawns per WP.
- `agents/orchestrator.md` — architectural-intent reference for the
  dispatch logic (not actively invoked).
- `references/lifecycle.md` — the 12-step contract per WP.
- `/sulis-execution:run-wp WP-NNN` — single-WP dispatch.
- `/sulis-execution:status` — read-only INDEX summary.
- `/sulis-execution:retry WP-NNN` — re-run a blocked WP.
