---
name: run-all
description: >
  Walk the Work Package INDEX in the calling session with parallel
  dispatch (up to max_parallel concurrent executors per batch, gated
  by dependency-graph eligibility). After each executor batch returns,
  the loop polls wpx-train for eligibility and fires `wpx-train run`
  when the train trigger is met (size ≥3 OR ≥1 WP older than 4h OR
  --force). The train handles Steps 8-10 (rebase / bundled-tip CI /
  sequential merge / deploy / health / smoke); after the train returns
  outcome=success, the calling session dispatches Step 11 per-WP
  (security-reviewer Agent) over the batch's wps_shipped, drafting
  remediation WPs for any findings — the distributed loop closes when
  a subsequent train's Step 11 produces zero NEW findings (v0.20.0+).
  Per-WP wpx-pipeline shipping remains available via `/sulis:run-wp
  WP-X --force-single` for hotfixes. Usage: /sulis:run-all.
  The loop runs inline in the calling session — not via a separate
  orchestrator subagent — because agent-tree-depth limits prevent
  subagents from reliably spawning further subagents.
---

# /sulis:run-all

Walk the Work Package INDEX and ship every ready WP, with parallel
executor dispatch and train-based integration:

- **Per-WP (executors, Steps 1-7):** parallel — `max_parallel` executors
  at a time, gated by INDEX dependency graph.
- **Per-batch (Steps 8-10, wpx-train):** after each executor batch
  returns success and WPs are flipped to `step-7-complete`, this
  skill polls `wpx-train queue-list` and fires `wpx-train run` if
  the trigger is met. The train batches up to 5 WPs into one rebase
  + bundled-tip CI + sequential merge + deploy + health + smoke.
- **Per-batch (Step 10.5, in the calling session, v0.21.1+):** after
  `wpx-train run` returns `outcome: success`, the calling session
  dispatches `/sulis:code-review` against the BATCH DIFF RANGE
  (`<first WP's pre_train_sha>..<last WP's merge_sha_on_dev>`).
  Catches cross-WP composition issues — N+1 across sibling WPs,
  integration regressions, contract drift between interdependent
  WPs. Findings auto-draft remediation WPs (`WP-AUTO-*`); CRITICAL
  findings BLOCKER batch-wide. **Note:** this is post-merge — it
  catches + remediates but doesn't pre-merge-gate; the pre-merge
  variant is deferred future work.
- **Per-batch (Step 11, in the calling session):** after Step 10.5,
  the calling session iterates over the batch's `wps_shipped` and
  dispatches the `sulis-security:security-reviewer` Agent per WP.
  Findings register; non-duplicate findings auto-draft remediation
  WPs (`WP-AUTO-*`). CRITICAL findings BLOCKER + `step-11-blocked`.
  The distributed loop terminates when a subsequent train's Step 11
  produces zero NEW findings (signature-hash dedup ensures
  convergence).
- **Per-WP again (Step 12):** worktree cleanup + INDEX flip from
  `step-7-complete` → `done`. Owned by the WP's executor return
  contract; documented in lifecycle.md.

## How to invoke (MUST — run the loop inline, with parallel batching)

**This is the marketplace's load-bearing dispatch logic.**

When this skill loads, **YOU (the calling session) run the dispatch
loop directly**. Do NOT call `Agent({subagent_type:
"orchestrator", ...})` first. The orchestrator agent
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
inside the sulis plugin. When the plugin is installed in
a downstream project, the scripts are at
`~/.claude/plugins/cache/sulis-ai-agents/sulis/<version>/scripts/`,
NOT at a project-relative path. You MUST resolve the tool directory
ONCE at the start of every dispatch session, before reading the
INDEX or doing anything else, and capture the result as
`$WPX_DIR`:

```bash
WPX_DIR=$(
  find ~/.claude/plugins/cache \
    -name wpx-journal -type f \
    -path '*/sulis/*/scripts/*' \
    2>/dev/null \
  | sort -r | head -1 | xargs -I{} dirname {} 2>/dev/null
)
# Dev fallback: marketplace repo cwd
if [ -z "$WPX_DIR" ] && [ -f "plugins/sulis/scripts/wpx-journal" ]; then
  WPX_DIR="$(pwd)/plugins/sulis/scripts"
fi
if [ -z "$WPX_DIR" ]; then
  echo "ERROR: cannot locate wpx-* scripts. Run: claude plugin install sulis@sulis-ai-agents" >&2
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

       HD-008 note (v0.24.0+): status here refers to the STORED
       INDEX.md cell for "pending" / "auto-draft" / "blocked" / etc.
       (operator/executor intent — no authoritative-state correlate)
       and to the COMPUTED status for the "done" check on dependencies
       (derived from origin + train-runs via compute_wp_status). The
       ready-set rule is therefore: stored pending + computed-done
       deps. In practice the loop reads stored cells from INDEX.md
       and treats them as authoritative for operator-intent states;
       the computed-done check fires through wpx-index status
       (--mode computed) or implicitly through wpx-train queue-list
       which now uses computed status per HD-008. A dep whose stored
       cell says done but whose computed status is step-7-complete
       (reverted) correctly blocks the downstream WP from entering
       the ready set.

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
         subagent_type: "executor",
         description: "Ship WP-007 end-to-end",
         model: <executor_model from WP frontmatter, if present>,
         prompt: """<executor brief per below>""",
       })
       Agent({
         subagent_type: "executor",
         description: "Ship WP-008 end-to-end",
         model: <executor_model from WP frontmatter, if present>,
         prompt: """<executor brief per below>""",
       })
       Agent({
         subagent_type: "executor",
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
       .executor-WP-NNN.md. Use the MCP tool
       `mcp__sulis-execution-mcp__journal_read` with
       `wp: WP-NNN, project: <slug>, field: step-7-status`.

       (Fallback if the MCP server isn't loaded:
       `wpx-journal read --wp WP-NNN --project <slug> --field step-7-status`.)

       Three branches:

       (a) **Step 7 complete** (status: complete; outcome row
           records branch + pushed SHA) — proceed with Steps 8-12
           via the calling-session pipeline below.

       (b) **BLOCKER written** (BLOCKER-WP-NNN.md exists at
           .architecture/{project}/work-packages/) — surface its
           plain-English summary; flip INDEX to blocked via MCP tool
           `mcp__sulis-execution-mcp__index_flip_status` with
           `wp: WP-NNN, project: <slug>, to: blocked, expected: in_progress`.

           Then propagate dependency_blocked to descendants via MCP
           tool `mcp__sulis-execution-mcp__index_mark_downstream_blocked`
           with `wp: WP-NNN, project: <slug>`.

           (Fallbacks if MCP unavailable:
           `wpx-index flip-status --wp ... --to blocked --expected in_progress`,
           then `wpx-index propagate-blocked --wp ...` — same wire format.)

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
                item>. Re-dispatch via /sulis:run-wp WP-NNN
                to resume from journal."

           The plan in the journal makes the parked-state diagnosis
           specific. v0.10.0+ executors that have completed Step 1.5
           leave a readable item list showing exactly which item was
           in-progress when the session ended.

   12. **For each Step-7-complete WP, flip INDEX status; the train ships them as a batch.**

       In v0.11.0+, individual WPs do NOT invoke wpx-pipeline directly
       at the end of run-all's executor batch. Instead:

       - Flip the WP's INDEX status to `step-7-complete` (the executor
         contract emits this via the journal).
       - After all WPs in this run-all parallel batch are flipped,
         invoke `wpx-train run` ONCE for the project. The train picks
         up all `step-7-complete` WPs (whose dependencies are merged
         and whose branches are CI-green) and batches them into one
         rebase / merge / deploy / health / smoke pass.

       Per CW-04, when run-all is invoked from inside a change worktree,
       detect the change branch first and pass it as `--base-branch`:

       ```bash
       CURRENT_BRANCH=$(git -C <repo-root> branch --show-current)
       if [[ "$CURRENT_BRANCH" == change/* ]]; then
           BASE_BRANCH="$CURRENT_BRANCH"
       else
           BASE_BRANCH="dev"
       fi

       "$WPX_DIR/wpx-train" run \
         --project <slug> \
         --repo <org/repo> \
         --base-branch "$BASE_BRANCH" \
         --deploy-workflow "<workflow name>" \
         --staging-url "<staging-url>" \
         --smoke-cmd "<smoke command>" \
         --health-path "<health-path>" \
         --enable-gate-handoff \
         # Add --force to bypass size/staleness trigger
       ```

       **v0.23.0 (HD-007): pass `--enable-gate-handoff`** so the train
       stops at the new `verifying_gates` phase after deploy/health/smoke
       complete green, instead of going directly to terminal success.
       The train emits `outcome: awaiting_gates` (exit 0) with a
       `gate_handoff` envelope describing the batch diff range +
       wps_shipped. The calling session (this skill) then dispatches
       Step 10.5 + Step 11 inside that phase and invokes
       `wpx-train mark-gates-complete --train-id <id>` to finalise (see
       Step 14.5 below). The gates are now part of the train's
       transaction in lifecycle terms — the dispatch mechanism stays
       here because a Python CLI can't spawn Agents.

       **Legacy fallback:** if `--enable-gate-handoff` is omitted, the
       train returns `outcome: success` directly (today's pre-v0.23.0
       behaviour) and Steps 13-14 below run as post-train follow-on.
       Both shapes are supported during the deprecation cycle; new
       projects SHOULD pass the flag.

       If the train trigger isn't met (e.g. only 1 WP eligible and no
       force), `wpx-train run` exits cleanly with `outcome:
       not_triggered`. The eligible WPs wait for the next invocation
       (typically the next run-all loop, or a manual
       `wpx-train run --force`).

       For backwards-compatibility / hotfix shipping of a single WP,
       see `/sulis:run-wp WP-X --force-single` which preserves
       the wpx-pipeline per-WP path.

       The remainder of this section (the historical Steps 8-12
       per-WP flow via wpx-pipeline) is preserved below as v0.10.7
       fallback documentation. **Do not invoke this in v0.11.0+ —
       wpx-train is the path.**

   13. **Step 10.5 (per-batch, v0.21.1+): bundled-tip code-review
       for cross-WP composition issues.**

       After `wpx-train run` returns, but BEFORE Step 11, review the
       composition of all WPs in the batch via `/sulis:code-review` against
       the batch's diff range on the base branch. This catches issues
       only visible when WPs compose: N+1 queries across sibling WPs,
       integration regressions, contract drift between interdependent
       WPs.

       **Trigger outcome (v0.23.0, HD-007):**

       - When `--enable-gate-handoff` was passed (recommended), the
         train returns `outcome: awaiting_gates` (exit 0) and the train
         state is in phase=`verifying_gates`. Dispatch Step 10.5 + 11
         INSIDE this phase. The `gate_handoff` envelope on the result
         JSON carries the diff range + wps_shipped — use those instead
         of reading the train state YAML.
       - When `--enable-gate-handoff` was omitted (legacy), dispatch
         ONLY when `outcome: "success"` per pre-v0.23.0 semantics.
       - In either case: if `outcome` is `not_triggered`, `paused`,
         `failed`, or `blocker`, **skip Step 10.5** — the train's own
         recovery flow owns those states.

       Capture the batch diff range from the train state YAML:

           BATCH_START_SHA=$(jq -r '.data.result.bundle[0].pre_train_sha' \
             /tmp/train-result.json)
           BATCH_END_SHA=$(jq -r '.data.result.final_merge_sha' \
             /tmp/train-result.json)

           # Diff range: from "just before the train started" to
           # "after the last squash-merge lands".
           # Equivalent: <BATCH_START_SHA>..<BATCH_END_SHA> on the base branch.

       Invoke `/sulis:code-review` against the range:

           /code-review "${BATCH_START_SHA}..${BATCH_END_SHA}" <project>

       The skill writes its bundle to:
           .architecture/<project>/code-reviews/PR-<range-or-hash>-<TS>/
             REVIEW.md
             signals.json
             tool-outputs/

       Capture the bundle path:

           BUNDLE_DIR=$(ls -td .architecture/<project>/code-reviews/PR-*-*/ \
             | head -1)

       Parse `signals.json`. For each finding (mirroring Step 11's
       loop pattern):

       - **CRITICAL** → write a BLOCKER for the batch; SKIP Step 12
         for the affected WPs; founder responds via remediation WPs
         that ship in the next train:

             "$WPX_DIR/wpx-blocker" write \
               --wp <project>-train-<train_id> --project <project> \
               --title "Step 10.5 CRITICAL composition finding" \
               --step "Step 10.5 (bundled-tip code-review)" \
               --trigger "step-10.5-critical" \
               --observation "<finding summary>" \
               --root-cause "Cross-WP composition issue surfaced by /sulis:code-review against batch diff <range>" \
               --scope in-scope \
               --suggested-next "Founder review; auto-drafted remediation WPs ship in next train cycle"

       - **CONCERN or ADVISORY** → register the finding (signature-hash
         dedup automatic); if not a duplicate, auto-draft a follow-up
         WP and register it in INDEX:

             # 1. Register
             "$WPX_DIR/wpx-findings" register \
               --wp <project>-train-<train_id> --project <project> \
               --severity <CONCERN|ADVISORY> \
               --summary "<one-line>" \
               --file <path> \
               --evidence-json @/tmp/finding-N.json \
               --suggested-fix "<suggested fix>" \
               --primitive <CR-NN code>

             # 2. Auto-draft (only if is_duplicate == false)
             "$WPX_DIR/wpx-findings" auto-draft-wp --project <project> \
               --source-finding <SF-NNN> \
               --source-wp <project>-train-<train_id> \
               --auto-wp-id <WP-AUTO-NNN from register output> \
               --primitive Refactor \
               --severity <CONCERN|ADVISORY>

             # 3. Register in INDEX
             "$WPX_DIR/wpx-index" add-wp \
               --wp WP-AUTO-NNN --project <project> --from-wp-file

       Record the verdict in the journal:

           "$WPX_DIR/wpx-journal" record-step \
             --wp <project>-train-<train_id> --project <project> \
             --step 10.5 \
             --outcome "addressed: <K_total> findings (<K_critical> CRITICAL, <K_concern> CONCERN, <K_advisory> ADVISORY); bundle=<BUNDLE_DIR>"

       Emit a plain-English summary, then proceed to Step 11 (security
       review per-WP — same batch, complementary perspective):

           "Step 10.5 complete for train <train_id>.
            Bundled-tip code-review against <range>.
            <K_total> findings (<K_critical> CRITICAL → BLOCKER;
             <K_new_drafts> CONCERN/ADVISORY → WP-AUTO-* drafted;
             <K_duplicates> duplicates skipped).
            Founder: review the drafted WPs in INDEX; promote to
            `pending` for the next train cycle. The next train's
            Step 10.5 will re-review the new bundled-tip — this is
            the loop-until-clean closure (the distributed loop
            terminates when an iteration produces zero NEW findings)."

       **Honesty about this post-merge variant:** Step 10.5 catches
       cross-WP findings AFTER merges land — it doesn't pre-merge-gate
       them. CRITICAL findings result in BLOCKER + remediation-WP
       cycle, not in a halt of the deploy. The TRUE pre-merge gate
       (cmd_run pause/resume; v0.16.1 deferred design) is still
       future work; this commit ships the visibility + remediation
       loop without that refactor.

   14. **Step 11 (per-batch, v0.20.0+): post-deploy security review
       for every WP shipped by the train.**

       Read the train's JSON envelope (the `/tmp/train-result.json`
       file from the previous step):

           jq -r '.data.result | {outcome, train_id, wps_shipped, deploy_url, final_merge_sha}' \
             /tmp/train-result.json > /tmp/train-summary.json

       Dispatch only when `outcome: "success"`. If `outcome` is
       `not_triggered`, `paused`, `failed`, or `blocker`, **skip Step 11**
       — the train's own recovery flow owns the WPs in those states.

       For each `wp_id` in `result.wps_shipped`, spawn the
       security-reviewer Agent ONCE. Iterate sequentially (subagent
       calls are synchronous and one level deep). Up to 2 attempts per
       WP if the subagent errors out transiently; on third failure
       write a BLOCKER and skip that WP's Step 12.

           # For each wp_id in wps_shipped:
           Agent({
             subagent_type: "sulis-security:security-reviewer",
             description: "Step 11 post-batch verification for <wp_id>",
             model: <security_model from frontmatter, if present>,
             prompt: """
               Review the squash-merge at <merge_sha> on dev
               (deployed to <deploy_url>). Health: <health_status>.
               Smoke: <smoke_verdict>.

               Verify against <wp_id>'s Definition of Done. Categorise
               findings by severity (CRITICAL / CONCERN / ADVISORY).
               Return a structured verdict JSON in the format
               documented at plugins/sulis/agents/
               security-reviewer.md.
             """,
           })

       Parse the returned verdict. For each finding from this WP:

       - **CRITICAL** → write a BLOCKER for the WP; flip status to
         `step-11-blocked`; **skip Step 12 for this WP only**; continue
         with the next WP in `wps_shipped` (do NOT halt the whole
         per-batch loop):

             "$WPX_DIR/wpx-blocker" write \
               --wp <wp_id> --project <slug> \
               --title "Step 11 CRITICAL finding on <wp_id>" \
               --step "Step 11 (post-deploy security review)" \
               --trigger "step-11-critical" \
               --observation "<finding summary>" \
               --root-cause "<root cause from verdict>" \
               --scope in-scope \
               --suggested-next "Founder review; remediate before next train cycle"

             "$WPX_DIR/wpx-index" flip-status \
               --wp <wp_id> --project <slug> \
               --to step-11-blocked --expected done

       - **CONCERN or ADVISORY** → register the finding (signature-hash
         dedup automatic); if not a duplicate, auto-draft a follow-up
         WP and register it in INDEX:

             # 1. Register
             "$WPX_DIR/wpx-findings" register --wp <wp_id> --project <slug> \
               --severity <CONCERN|ADVISORY> \
               --summary "<one-line>" \
               --file <path> \
               --evidence-json @/tmp/finding-N.json \
               --suggested-fix "<suggested fix>" \
               --primitive <SEC-NN>

             # 2. Auto-draft (only if is_duplicate == false in register output)
             "$WPX_DIR/wpx-findings" auto-draft-wp --project <slug> \
               --source-finding <SF-NNN> \
               --source-wp <wp_id> \
               --auto-wp-id <WP-AUTO-NNN from register output> \
               --primitive <Secure|Harden|Instrument|Gate> \
               --severity <CONCERN|ADVISORY>

             # 3. Register in INDEX (status: auto-draft; founder promotes)
             "$WPX_DIR/wpx-index" add-wp \
               --wp WP-AUTO-NNN --project <slug> --from-wp-file

       After ALL findings handled for this WP (and assuming no CRITICAL),
       record the verdict in the journal:

           "$WPX_DIR/wpx-journal" record-postdeploy \
             --wp <wp_id> --project <slug> \
             --verdict <PASS|PASS-WITH-FOLLOW-UPS> \
             --findings-summary "0 CRITICAL, <N> CONCERN, <M> ADVISORY"

       After the loop completes — every WP in `wps_shipped` reviewed —
       emit a plain-English summary:

           "Step 11 complete for train <train_id>.
            <N> WPs reviewed; <K_total> findings registered
            (<K_critical> CRITICAL → BLOCKER + step-11-blocked;
             <K_new> CONCERN/ADVISORY new → <K_new> WP-AUTO-* drafted;
             <K_dup> duplicates skipped).
            Founder: review the auto-drafted WPs in INDEX (status
            `auto-draft`); promote to `pending` for the next train
            cycle. The next train's Step 11 will re-review their
            merge SHAs — this is the loop-until-clean closure (the
            distributed loop terminates when an iteration produces
            zero NEW findings)."

       **Loop-until-clean semantic (the user-required behaviour):**

       Step 11 doesn't tight-loop within one train run (re-spawning
       the reviewer per WP after a fix isn't useful — the merge is
       already on dev). Instead, the loop is DISTRIBUTED across trains:

       - This train's Step 11 produces N findings + M auto-drafted WPs
       - Founder promotes WP-AUTO-* to `pending`
       - The next train ships them
       - That train's Step 11 re-reviews their merge SHAs
       - If new findings → more WP-AUTO; if zero new findings → loop
         closes (the codebase is clean from Step 11's perspective)

       `wpx-findings register`'s signature-hash dedup ensures
       previously-registered findings don't generate duplicate
       WP-AUTO drafts (the loop converges, doesn't oscillate).

       For an explicit, retroactive sweep over WPs that shipped
       before v0.20.0 (i.e., slice-1 and slice-2's 12 WPs that
       missed Step 11), invoke `/sulis:backfill-gates`
       (v0.20.2+).

   14.5. **HD-007 gate completion (v0.23.0+, only when `--enable-gate-handoff`
        was passed at Step 12).**

        After Step 10.5 + Step 11 have both completed for every WP in
        the batch, finalise the train by invoking the new
        `mark-gates-complete` subcommand:

            # Clean verdict — no CRITICAL found in Step 10.5 OR Step 11:
            "$WPX_DIR/wpx-train" mark-gates-complete \
              --project <slug> \
              --train-id <train_id from train-result.json> \
              --gate-findings "$BUNDLE_DIR/REVIEW.md"

            # CRITICAL verdict — at least one Step 10.5 or Step 11 CRITICAL
            # finding fired (and the dispatcher above already wrote BLOCKERs +
            # drafted remediation WPs):
            "$WPX_DIR/wpx-train" mark-gates-complete \
              --project <slug> \
              --train-id <train_id> \
              --gate-findings "$BUNDLE_DIR/REVIEW.md" \
              --critical-found

        Behaviour:

        - **Clean** → train transitions to terminal `success`; YAML
          record's `outcome` becomes `success`; state file cleaned up.
          Exits 0.
        - **`--critical-found`** → transitions to terminal `failed`;
          YAML record's `outcome` becomes `gate_blocker`. **No ADR-212
          revert runs** — the gate dispatchers above (Steps 13-14)
          already wrote per-WP BLOCKERs + drafted remediation WPs.
          Production stays live; the founder owns the remediation
          cycle (the next train ships the remediation WPs and that
          train's Step 10.5 + 11 re-evaluate). Exits 1.

        **Skip this step when `--enable-gate-handoff` was NOT passed at
        Step 12** — the train already transitioned to terminal `success`
        on its own, and `mark-gates-complete` will reject the call with
        "expected phase=verifying_gates" since the state file no longer
        exists.

       ---

       **(v0.10.7 fallback — preserved for reference)**

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
               documented at plugins/sulis/agents/
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
  subagent_type: "executor",
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

- **One specific WP.** Use `/sulis:run-wp WP-NNN` — single-
  WP dispatch (also runs Agent in the calling session; no parallel
  logic needed).
- **Retry a blocked WP.** Use `/sulis:retry WP-NNN` after
  the external blocker is resolved.

## Gotchas

- The skill expects a non-empty
  `.architecture/{project}/work-packages/INDEX.md`. If empty,
  surface: *"INDEX is empty. Run `/sulis:plan-work` first."*
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
- `/sulis:run-wp WP-NNN` — single-WP dispatch.
- `/sulis:status` — read-only INDEX summary.
- `/sulis:retry WP-NNN` — re-run a blocked WP.
