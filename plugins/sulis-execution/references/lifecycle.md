# Executor Lifecycle

The 12-step contract per Work Package — split across two owners as of
v0.9.0. **Executor owns Steps 1-7; calling session owns Steps 8-12.**
Each step has input artifacts, a success criterion, a failure-handling
OODA recipe (per `executor-loop-standard.md`), and an escalation
trigger.

| # | Step | Owner |
|---|---|---|
| 1 | Worktree + branch | Executor |
| 1.5 | Plan generation (v0.10.0+) | Executor |
| 2 | RED — failing tests | Executor |
| 3 | GREEN — minimum code | Executor |
| 4 | BLUE — refactor | Executor |
| 5 | Docs | Executor |
| 6 | Lint / type / format | Executor |
| 7 | Commit + push | Executor |
| 8 | CI poll + rebase + squash-merge | Calling session (`wpx-pipeline`) |
| 9 | Deploy poll | Calling session (`wpx-pipeline`) |
| 10 | Health + smoke | Calling session (`wpx-pipeline`) |
| 11 | Security review (post-deploy verification) | Calling session (`Agent({subagent_type: "sulis-security:security-reviewer"})` + `wpx-findings register`) |
| 12 | INDEX flip + acceptance evidence + worktree removal | Calling session (`wpx-step12 wrap`) |

Version coverage: v0.1 implemented steps 1-6. v0.2 added step 7. v0.3
added steps 8-10. v0.6 added step 5 (docs) and step 11 (post-deploy
verification); v0.6 also collapsed health + smoke into one step 10.
v0.7 added findings register + auto-draft WPs at step 11. **v0.9.0
moved Steps 8-12 to the calling session** — fixing the structural
parking failure caused by asking a subagent to poll across turns,
which the harness's cross-turn notification contract doesn't support.

### Why the v0.9.0 contract split

Versions 0.5.1 through 0.8.3 each moved the executor's parking failure
to a new boundary:

| Version | Parked at | Reason |
|---|---|---|
| v0.5.1 | Step 7 → 8 (CI poll start) | "CI is in flight; I'll wait" |
| v0.6.1 | Step 11 → 12 | "Monitors will respond when complete" |
| v0.7.x | Step 8 (rebase loop) | "Rebase in progress" |
| v0.8.3 | Step 9 (deploy poll) | "Background poller will notify me" |

The common root cause: **subagents have atomic turns**. `Bash(run_in_background:
true)` cross-turn notifications work reliably for top-level agents
but NOT for subagents — a subagent's session is one synchronous Agent
tool invocation, and there is no continuing turn for the notification
to fire into.

v0.9.0 moves all polling out of the executor. The calling session
(top-level, where `run_in_background` works) invokes a deterministic
`wpx-pipeline run` script for Steps 8-10, an Agent call for Step 11,
and `wpx-step12 wrap` for Step 12. The executor returns at Step 7
with the branch on remote and the journal recorded; the calling
session takes everything from there.

**On parallel execution (v0.8+).** Each WP's executor runs in its
own `git worktree` per GIT-07. The 12-step lifecycle is identical
whether the executor is running solo or as part of a parallel batch
of N — the executor doesn't know which mode it's in, and shouldn't
care. Concurrent peers have non-overlapping file scopes (the
run-all skill verifies this before dispatching); concurrent worktrees
don't share working files; the `git worktree add` (Step 1) and
worktree removal (Step 12) bracket the per-executor isolation.

---

## Bookkeeping via wpx-* tools (MUST — v0.9.0 commit 1.24b+)

**Every bookkeeping operation in this lifecycle goes through a
`wpx-*` CLI tool, not direct file edits or raw git commands.** The
tools live inside the plugin's `scripts/` directory and are invoked
via Bash. They are deterministic and cannot format-drift. The
detailed per-step recipes below ("Worktree creation", "Pre-flight
tooling check", etc.) describe the *intent* of each step; the
*mechanism* is always a `wpx-*` invocation. Where this reference
shows raw Bash, treat it as background context — the canonical
execution path is the tool.

**Path resolution (v0.10.1+).** When the plugin is installed in a
downstream project, the scripts live at
`~/.claude/plugins/cache/sulis-ai-agents/sulis-execution/<version>/scripts/`,
not at a project-relative path. The executor agent and the
run-all / run-wp skills MUST resolve the tool directory once per
session and capture it as `$WPX_DIR` — see "Resolving wpx-* tool
paths (MUST — first action)" in `agents/executor.md` for the
canonical preamble. All invocation examples in this document use
`"$WPX_DIR/wpx-NAME"` to reflect that contract.

For ad-hoc human use (debug, recovery, ad-hoc journal reads), see
the `wpx` wrapper documented at `scripts/README.md` — install once
to PATH, then `wpx journal read --wp WP-NNN --project <slug>
--field plan` works from any project directory.

The full mapping is in `agents/executor.md` under *Bookkeeping via
wpx-* tools*. Key invocations referenced by this document:

| Step | Tool invocation |
|---|---|
| 1 (worktree) | `wpx-worktree create` |
| 1 (journal init) | `wpx-journal init` |
| 1 (pre-flight) | `wpx-journal record-preflight` |
| Any (step start) | `wpx-journal start-step` |
| Any (step success) | `wpx-journal complete-step` |
| Any (self-heal) | `wpx-journal record-attempt` |
| 8-10 (read frontmatter cadences) | `wpx-wp read-frontmatter` |
| 11 (post-deploy verdict) | `wpx-journal record-postdeploy` |
| 11 (findings register + auto-draft) | `wpx-findings register` then `wpx-findings auto-draft-wp` |
| BLOCKER | `wpx-blocker write` |
| 12 (calling session only — NOT executor) | `wpx-step12 wrap` |

Direct Markdown edits to `.executor-WP-NNN.md`, `INDEX.md`,
`BLOCKER-*.md`, `findings-register.md`, or `SF-NNN-*.md` are
FORBIDDEN. They are the historical source of every post-Step-6
parking failure (`.executor-WP-NNN.md` row misalignment, INDEX status
enum drift, missing acceptance-evidence fields, BLOCKER format
deviation that breaks the concierge's translation step).

The detailed Bash recipes that appear below each step show the
underlying mechanism (helpful for diagnosis if a `wpx-*` tool ever
fails internally), but the executor's first action at every
bookkeeping moment is to invoke the appropriate tool.

---

## Calling-session invocations (Steps 8-12) — v0.9.0+

Once the executor returns with Step 7 journal-recorded, the calling
session (run-all skill, run-wp skill, or founder's main session) takes
over. The full Steps 8-12 sequence is owned by the calling session.
The detailed Step 8-12 sections later in this document remain as
**mechanism reference** for the `wpx-pipeline` script's internals and
for diagnosis when the pipeline fails; they are NOT actions the
executor performs.

The calling session's invocation sequence per WP:

```bash
# Resolve WPX_DIR (the calling session's first Bash call — see the
# "Resolving wpx-* tool paths" preamble in agents/executor.md and
# the run-all / run-wp skill files).

# 0. Read what the executor produced
"$WPX_DIR/wpx-journal" read \
  --wp WP-NNN --project <slug> --field step-trace
# → JSON containing branch, pushed SHA, Step 7 outcome line

# Resolve frontmatter
"$WPX_DIR/wpx-wp" read-frontmatter \
  --wp WP-NNN --project <slug> --field '*'
# → branch, smoke_test, ci_poll_interval_seconds, deploy_workflow,
#   post_deploy_verification, executor_model, security_model

# 1. Steps 8-10: CI poll + rebase + squash-merge + deploy + health + smoke
# Run via top-level Bash(run_in_background:true) — typical wall time
# 15-45 min. The harness notifies on completion.
"$WPX_DIR/wpx-pipeline" run \
  --wp WP-NNN --project <slug> \
  --branch feat/wp-NNN-<slug> \
  --worktree-path ../wp-NNN-worktree \
  --dev-sha-at-creation "$(cat .architecture/<slug>/work-packages/.executor-WP-NNN-dev-sha)" \
  --deploy-workflow "Deploy to Dev Environment" \
  --staging-url https://your-staging.example.com \
  --smoke-cmd "<smoke command from WP frontmatter>" \
  --repo <org/repo>
# Output JSON on completion: { outcome, merge_sha, deploy_url,
#   health_status, smoke_verdict, blocker_reason }
# Exit codes: 0 success / 1 blocker / 2 internal error
```

The calling session reads the JSON. If `outcome: "blocker"`, it
writes a BLOCKER via `wpx-blocker write` describing the pipeline
failure, then flips INDEX to `blocked` and propagates
`dependency_blocked` to descendants. If `outcome: "success"`, it
continues:

```bash
# 2. Step 11: security review (default always-on; opt-out via
#    post_deploy_verification: none in WP frontmatter)
# Spawn the security-reviewer agent via Agent tool (synchronous):

Agent({
  subagent_type: "sulis-security:security-reviewer",
  description: "Step 11 post-deploy verification for WP-NNN",
  prompt: """
    Review the squash-merge at <merge_sha> on dev (deployed to
    <deploy_url>). Health: <health_status>. Smoke: <smoke_verdict>.

    Verify against the WP's Definition of Done. Categorise findings
    by severity (CRITICAL / CONCERN / ADVISORY). Return a structured
    verdict JSON in the format documented at
    plugins/sulis-security/agents/security-reviewer.md.
  """,
})

# 3. Per non-CRITICAL finding from the agent's return:
"$WPX_DIR/wpx-findings" register \
  --wp WP-NNN --project <slug> \
  --severity CONCERN \
  --summary "..." --file <path> \
  --evidence-json @/tmp/finding.json \
  --suggested-fix "..." \
  --primitive SEC-NN
# → Returns SF-NNN id (existing on dedup) + WP-AUTO-NNN id (new)

"$WPX_DIR/wpx-findings" auto-draft-wp \
  --project <slug> \
  --source-finding SF-NNN \
  --source-wp WP-NNN \
  --auto-wp-id WP-AUTO-NNN \
  --primitive Secure --severity CONCERN
# → Creates the auto-draft WP file

# 4. Record the post-deploy verdict in the journal
"$WPX_DIR/wpx-journal" record-postdeploy \
  --wp WP-NNN --project <slug> \
  --verdict PASS \
  --findings-summary "0 CRITICAL, 1 CONCERN (SF-007 → WP-AUTO-003), 2 ADVISORY"

# 5. Step 12: atomic wrap (acceptance evidence + INDEX flip +
#    worktree remove)
cat > /tmp/pipeline-result.json <<JSON
{ "result": <pipeline JSON output from step 1> }
JSON

"$WPX_DIR/wpx-step12" wrap \
  --wp WP-NNN --project <slug> \
  --branch feat/wp-NNN-<slug> \
  --pipeline-result @/tmp/pipeline-result.json \
  --worktree-path ../wp-NNN-worktree
```

On `outcome: "blocker"` from `wpx-pipeline`, the calling session
instead writes a BLOCKER and stops — it does NOT proceed to Step 11
or Step 12.

The full skill prompts for the calling session live in
`plugins/sulis-execution/skills/run-all/SKILL.md` and `run-wp/SKILL.md`.

---

## Step 1 — Worktree + branch

**Input:** WP file (read), `dev` branch HEAD on remote.

### Pre-flight tooling check (v0.8.2+)

Before the worktree is created, verify the project has the tools the
lifecycle depends on. Each absent tool either downgrades to a
documented fallback or escalates to BLOCKER. Outcomes are recorded
in the journal under `## Pre-flight checks`.

```bash
# gh CLI (MUST — used at Step 8 for CI poll + merge).
if ! gh --version >/dev/null 2>&1; then
  echo "BLOCKER: gh CLI not installed; cannot poll CI or merge to dev."
  exit 1
fi

# Coverage tool (SHOULD — used at Step 4/Blue for ≥90% check per RGB-02).
if ! uv run python -m coverage --version >/dev/null 2>&1; then
  COVERAGE_FALLBACK=true
  echo "WARN: coverage tool not installed; will fall back to manual coverage analysis at Step 4."
else
  COVERAGE_FALLBACK=false
fi

# Feature-branch CI (SHOULD per GIT-04 v0.1.3+). Inspect .github/workflows
# (or .gitlab-ci.yml, etc.) for branch globs covering feat/, fix/, etc.
if grep -lE "'feat/\*\*'|feat/\*\*|^\s+- feat/" .github/workflows/*.yml >/dev/null 2>&1; then
  CI_ON_BRANCH=true
else
  CI_ON_BRANCH=false
  echo "WARN: feature-branch CI not configured; will fall back to local pre-commit gate at Step 7."
  echo "  Recommend wiring feature-branch CI per GIT-04 v0.1.3+ before scaling parallel dispatch."
fi
```

Journal entry shape:

```markdown
## Pre-flight checks

| Tool / Check | Status | Fallback |
|---|---|---|
| gh CLI | present | — |
| coverage tool | absent | manual analysis at Step 4 |
| feature-branch CI | absent | local pre-commit gate at Step 7 |
```

### Worktree creation

```bash
git fetch origin
git worktree add ../wp-NNN-worktree -b feat/wp-NNN-<slug> origin/dev
cd ../wp-NNN-worktree

# Record the dev SHA at branch creation. Step 8 uses this to detect
# whether dev has advanced (e.g. a parallel peer merged in the
# meantime) and trigger a rebase before squash-merging.
git rev-parse origin/dev > .executor-WP-NNN-dev-sha
```

Where `<slug>` is kebab-case from the WP's `title`, ≤ 50 chars, per
GIT-02.

**Success criterion:** Worktree clean, branch off latest `dev`, working
directory in the worktree.

**Failure handling:**

- Worktree creation fails because path exists → OODA. Likely cause: a
  previous attempt was not cleaned up. Decide: remove the stale
  worktree (`git worktree remove --force`), retry.
- Branch name collision (branch exists already) → OODA. Likely
  cause: a previous attempt got partway and left the branch. Decide:
  delete the orphan branch on remote (`git push origin :feat/wp-NNN-*`)
  and locally, retry.
- `origin/dev` doesn't exist → halt + escalate. Out of scope — the
  project's `dev` branch is the executor's operating environment;
  the executor doesn't create it.

**Escalation trigger:** Two budget attempts (per
`self-heal-budget.md`) exhausted, or out-of-scope failure (no `dev`
branch).

---

## Step 1.5 — Plan generation (v0.10.0+)

**Input:** WP file (already read), TDD section, ADRs, journal initialised
at Step 1 with empty `## Plan` section.

**Owner:** Executor.

**Purpose:** Produce a structured "here's what I'm about to do" surface
in the journal before any test or code is written. This catches scope
drift before substantive work begins, gives the calling session +
concierge a readable plan to surface to the founder, and creates an
audit record of the executor's intent independent of the eventual
acceptance evidence.

The plan generation has two halves: an **approach** paragraph
(2-3 sentences of strategic shape) and an **item list** (concrete
plan rows, one per testable / implementable unit of work).

### Approach paragraph

Identify the WP's `primitive` field (Create / Reuse / Strangle /
Refactor / ...). Look up the matching scaffold in
`references/primitive-scaffolds.md`. Surface in 2-3 sentences:

- Which primitive applies and what scaffold shape that implies.
- The key risk or non-obvious decision in the WP's Contract.
- Expected scope of file changes (rough estimate: "two new tests in
  X, one new function in Y, possibly a refactor in Z").

Example: *"Create primitive. New `billing.cancel_subscription()`
with happy + expired test cases. Key risk: shared validation with
`refund_subscription` — refactor if 2-consumer threshold fires."*

### Item list

One item per testable or implementable unit of work. Each item is a
JSON object `{description, step, notes?}`:

- **Per Definition-of-Done > Red checklist line**: one item with
  description like *"Write test_cancel_happy in tests/test_billing.py"*
  and `step: "2 (RED)"`.
- **Per implementation target** identified from the Contract + DoD >
  Green: function name + module path, e.g. *"Implement
  `cancel_subscription()` in src/billing.py"* with `step: "3 (GREEN)"`.
- **Zero or one refactor item** from DoD > Blue. If conditional on the
  2-consumer rule firing, include with `notes: "conditional"` so the
  skip-vs-do decision is explicit.
- **Zero or more docs items** from `docs_to_update` frontmatter (or
  auto-detected): one per file.
- **One lint item** (`step: "6 (LINT)"`).
- **One commit + push item** (`step: "7 (COMMIT)"`).

The `step` field uses short canonical phase labels: `2 (RED)`,
`3 (GREEN)`, `4 (BLUE)`, `5 (DOCS)`, `6 (LINT)`, `7 (COMMIT)`.

### Invocation

```bash
cat > /tmp/plan-WP-NNN.json <<JSON
[
  {"description": "Write test_cancel_happy in tests/test_billing.py", "step": "2 (RED)"},
  {"description": "Write test_cancel_expired in tests/test_billing.py", "step": "2 (RED)"},
  {"description": "Implement cancel_subscription() in src/billing.py", "step": "3 (GREEN)"},
  {"description": "Refactor shared validation", "step": "4 (BLUE)", "notes": "conditional"},
  {"description": "Update docs/billing.md cancel-flow section", "step": "5 (DOCS)"},
  {"description": "Run lint + type + format", "step": "6 (LINT)"},
  {"description": "Commit + push", "step": "7 (COMMIT)"}
]
JSON

"$WPX_DIR/wpx-journal" seed-plan \
  --wp WP-NNN --project <slug> \
  --approach "<2-3 sentence summary>" \
  --plan-json @/tmp/plan-WP-NNN.json
```

### Success criterion

`## Plan` section in the journal contains a populated approach
paragraph + a non-empty item table. All items have status `pending`.

### Failure handling

If during plan generation you identify that the WP Contract is
internally contradictory or references files outside any plausible
scope, do NOT seed the plan. Escalate immediately via
`wpx-blocker write` with `--trigger scope-guard --step 1.5` and an
observation describing the contradiction. The journal's `## Plan`
section remains empty; the calling session sees the BLOCKER and
flips INDEX to `blocked`.

If the seed succeeds but you then notice on review that a plan item
references a file outside the WP Contract scope, the same
scope-guard escalation applies — you simply have a populated plan
in the journal alongside the BLOCKER for diagnostic clarity.

### Working through the plan (during Steps 2-7)

As each item begins, flip `pending → in-progress`:

```bash
wpx-journal mark-plan-item --wp WP-NNN --project <slug> \
  --item <N> --status in-progress --expected pending
```

When complete, flip `in-progress → done`:

```bash
wpx-journal mark-plan-item --wp WP-NNN --project <slug> \
  --item <N> --status done --expected in-progress
```

Conditional items that don't fire: `--status skipped --notes "..."`.

New items discovered mid-run: `wpx-journal add-plan-item`.

### Resume semantics

If the executor's session terminates between Step 1.5 completion and
Step 7 success (rare), the journal's `## Plan` section is the resume
point. On re-dispatch, the executor reads the plan via
`wpx-journal read --field plan`, finds the first item with status
`in-progress` or `pending`, and continues from there — does NOT
re-seed.

---

## Step 2 — RED: write failing tests

**Input:** WP Contract (acceptance criteria), TDD section, ADRs,
`red-green-blue.md` (RGB-01).

**Action:** Write tests per the WP's Definition of Done. Three
categories per RGB-01:

1. **Functional happy-path** — the new behaviour produces the expected
   outcome.
2. **Edge cases** — null inputs, boundary values, concurrency, partial
   failures.
3. **Hardening assertions** — fault injection, timeouts, retries,
   observability. Use deterministic test harnesses (toxiproxy, mock
   clock) — never production-observed assertions.

**Success criterion:** Tests written; all run; all fail for the right
reason (each failing test must be failing because the new code doesn't
exist yet, NOT because the test itself is broken).

**Failure handling:**

- A test passes immediately → OODA. Likely cause: test is asserting
  something already true (e.g. the WP is a duplicate of completed
  work). Decide: re-read WP Contract; if WP is genuinely covering
  existing behaviour, escalate (out of scope — duplicate WPs are
  upstream's problem).
- A test fails for the wrong reason (syntax error in the test
  itself) → OODA. Decide: fix the test setup. In scope.
- Cannot write a test because the WP Contract is ambiguous → halt +
  escalate. Out of scope — Contract ambiguity is upstream's.

**Budget:** 3 attempts per `self-heal-budget.md`.

---

## Step 3 — GREEN: minimum code to make tests pass

**Input:** Failing tests from step 2, the codebase, `change-primitives.md`
(for the WP's `primitive` field), CP-01..05 (priority 0: internal
prior art).

**Action:**

1. **Internal prior art check first** (EP-03 + CP-01 priority 0).
   Before writing any new code, grep the codebase for existing
   primitives that already do what the WP needs. Check
   `.architecture/{project}/probe-raw/1_2_capabilities.json` if it
   exists (the SEA probe's capability inventory). If a match exists,
   the primitive for this WP should be `Reuse` or `Compose`, not
   `Create` — re-verify the WP's frontmatter against your finding,
   and if it says `Create` for something that already exists, halt +
   escalate.
2. Apply the per-primitive scaffold from `primitive-scaffolds.md`.
3. Run the test suite.

**Success criterion:** All new tests pass; full suite green; ≥ 90%
coverage on new files (RGB-02).

**Failure handling:** OODA per EL-01..08. Examine failing test output
verbatim (EL-02). Five Whys to root cause. Decide minimum change in
scope. Re-run failed test.

**Budget:** 3 attempts per `self-heal-budget.md`.

**Common Five Whys patterns:**

- Test fails with field-name mismatch → handler reads wrong key.
  Root cause: API convention not followed. Fix: rename the field
  access. In scope.
- Test fails with timeout → external call is slow. Root cause:
  test hit a real service instead of a mock. Fix: apply the mock
  fixture. In scope.
- Test fails with import error → module path wrong. Root cause:
  re-org happened upstream and import wasn't updated. Fix: update
  the import. In scope.

---

## Step 4 — BLUE: mandatory refactor

**Input:** Green test suite from step 3, EP-07 (Boy Scout, scoped).

**Action:** Refactor the code added in step 3. Three categories per
RGB-03:

1. **Duplication extraction.** If a primitive appears in ≥ 2 places
   inside the files this WP touches, extract to a shared helper.
   (Cross-file extraction is a separate WP per EP-07.)
2. **Naming.** Variable / function names express intent, not
   implementation.
3. **Shape.** Boring per CP-01..05. Type annotations. Explicit error
   handling.

**No new behaviour.** Refactor preserves the test outcomes.

**Success criterion:** All tests still pass after refactor; coverage on new files meets RGB-02's ≥ 90% threshold (verified via primary or fallback path below).

### Coverage verification — primary and fallback paths (v0.8.2+)

**Primary path (coverage tool installed):**

```bash
uv run pytest \
  --cov=<new-module-path> \
  --cov-report=term-missing \
  --cov-fail-under=90 \
  tests/unit/<path-to-new-tests>
```

The `--cov-fail-under=90` flag makes pytest exit non-zero if coverage
on the new module is below 90%. RGB-02 satisfied directly.

**Fallback path (coverage tool absent, per Step 1 pre-flight):**

When `COVERAGE_FALLBACK=true` from Step 1, the executor performs a
manual coverage analysis and records it in the journal under
`## Coverage analysis (manual — coverage tool absent)`:

```markdown
## Coverage analysis (manual — coverage tool absent)

File: sulis/shared/workflows/domain/sandbox.py

Branches:
- L42 (if path.is_symlink()): tested by test_symlink_outside_root_fails (line 87)
- L45 (else): tested by test_resolves_simple_relative_path (line 56)
- L51 (try/except UnicodeDecodeError): pragma: no cover — defensive; unprovokable in Python ≥3.12
- L67 (else branch of for-loop): tested by test_no_dot_dot_segments (line 102)
- ... etc

Estimate: ~95% effective coverage (every reachable branch has a named test;
defensive branches marked pragma: no cover).
```

The journal entry is the audit trail. Requirements:

- **Enumerate every branch** in the new code (`if`/`elif`/`else`, exception handlers, `pragma: no cover` markers).
- **Cite the specific test** for each branch (test name + line number).
- **Justify each `pragma: no cover`** explicitly (defensive against
  unprovokable error, fallback for older Python, etc.).
- **Estimate honestly** — not a guess; a concrete reasoned number.

The fallback is acceptable but weaker than tool-based: no automated
verification, no CI gate, depends on the executor's honest analysis.
Recommendation to wire pytest-cov is surfaced via the run-all status
line (same shape as feature-branch-CI recommendation): *"WP-NNN:
coverage tool not installed; used manual coverage analysis. Recommend
installing pytest-cov for stronger guarantees."*

**Failure handling:**

- Refactor breaks a test → OODA. Five Whys often: the refactor
  introduced a regression. Decide: revert the refactor; narrow the
  scope (split into smaller refactors); retry.
- Refactor introduces an unrelated improvement → halt the cycle;
  scope guard fires lightly here — the unrelated improvement
  becomes its own WP per EP-07. Roll back the unrelated part,
  proceed with the in-scope part.

**Budget:** 2 attempts per `self-heal-budget.md`. After 2 failed
refactors, the code stays in its green-but-not-refactored state and
the WP advances. The BLOCKER record is NOT written — Blue failure to
extract a clean refactor is not a blocker; it's a quality-debt note.
The journal records the attempted refactors and the reason for
giving up.

**Note:** This is the only step where exceeding budget is not an
escalation. Blue's purpose is to leave code better than found; if
the agent can't find a clean refactor in 2 attempts, the code is
likely already at its boring shape — that is success-with-no-Blue.

---

## Step 5 — Documentation update

**Input:** Refactored code from step 4. WP frontmatter (optional
`docs_to_update` field listing files SEA pre-identified). The set of
files this WP modified (from the worktree's git diff vs `dev`).

**Action:**

1. **Read the WP frontmatter for `docs_to_update`** (optional list of
   file paths).
2. **If `docs_to_update` is present:** update each named file based on
   the WP's behaviour change. The executor knows what code it changed
   at this point; it correlates the change against each named doc
   (docstrings, README entries, OpenAPI specs, ADRs) and updates
   the relevant sections.
3. **If `docs_to_update` is absent:** auto-detect docs to update.
   Scan the WP's modified source files for:
   - Function/method docstrings (Python: `"""..."""`, TS: `/** ... */`,
     Go: `// ...` preceding signatures). If the signature changed,
     update the docstring.
   - README entries that reference changed symbols. Grep the project
     root for `README.md`, `docs/**/*.md`; look for backtick-quoted
     references to symbols the WP touched.
   - OpenAPI / GraphQL specs that reference changed endpoints. Look
     in `openapi.yaml`, `schema.graphql`, or similar.
   - ADRs that reference changed components. Look in
     `.architecture/{project}/adrs/` for files mentioning the
     primitives this WP touched.
4. **Update any matched docs** to reflect the new behaviour. Keep
   changes minimal — no rewriting unaffected sections (EP-07
   Boy-Scout-Scoped).
5. **If nothing is found**, log a journal note (`docs-step: no
   updates required`) and skip silently — step succeeds as a no-op.

**Success criterion:** Identified docs reflect the new behaviour; no
broken cross-references in the docs the WP touched; markdown lint
passes if the project has it configured.

**Failure handling:**

- **Markdown lint fails / link-check broken** → OODA. Most are
  mechanically fixable (path typos, anchor changes after a heading
  rename). Decide: fix the broken reference; re-lint.
- **Doc inference is ambiguous** (e.g. multiple READMEs could be the
  right target, or a docstring references a behaviour change that
  has multiple plausible re-wordings) → log a journal warning naming
  the ambiguity; advance with no update on the ambiguous doc. **Not a
  BLOCKER.** The next WP with the same doc surface will surface the
  ambiguity again; eventually SEA populates `docs_to_update` to
  disambiguate.
- **No project docs exist at all** (genuinely doc-less project) →
  step is a clean no-op; journal-note `no docs surface in project`;
  advance.

**Budget:** 3 attempts for doc-lint failures.

**Composition.** Maps to the REINFORCE-Document primitive scaffold
in `primitive-scaffolds.md` — the scaffold defines the Red/Green/Blue
shape (which is N/A for docs since they're not runtime artifacts;
docs Red is "review pass"). Step 5 reuses that shape.

This step is **always present in the lifecycle** but no-ops when no
docs are identified. The "standard step" framing means every WP
goes through it; the step's behaviour adapts to what the WP actually
touched.

---

## Step 6 — Lint / type / format

**Input:** The code from step 4.

**Action:** Run the project's lint / type-check / format commands.
Typical:

```bash
ruff check .           # Python
ruff format .          # Python
mypy src/              # Python
npm run lint           # JS / TS
npm run typecheck      # TS
gofmt -l .             # Go
golangci-lint run      # Go
```

The executor reads the project's lint config to know which commands
to run. If no config exists, this step is skipped (with a journal
note); the project lacking lint config is a pre-existing condition,
not the executor's to fix.

**Success criterion:** All checks pass.

**Failure handling:**

- Lint flags an issue with the new code → OODA. Most lint issues
  are auto-fixable (`ruff format`, `npm run lint -- --fix`,
  `gofmt -w .`). Decide: run the auto-fix; re-check. In scope.
- Lint flags an issue with existing code the WP touched (not new
  code) → in scope per EP-07 Boy Scout. Fix it.
- Lint flags an issue in a file outside this WP's Contract →
  out of scope. The lint output is signal; the fix is somewhere
  else. Record in journal; do not fix. Continue.
- Type-check fails → OODA. Typically: missing type annotation, or
  signature mismatch. In scope; fix.
- Formatter ↔ linter rule conflict (one re-introduces what the
  other fixes) → after 5 attempts, halt + escalate (out of scope —
  the config is at the project root, not in this WP).

**Budget:** 5 attempts per `self-heal-budget.md`. Lint is the most
auto-fixable category and warrants the highest budget.

---

## Step 7 — Commit (Conventional Commits) + push branch

**Input:** Clean working tree from step 6, GIT-03 (commit message
format), the WP's frontmatter.

**Action:**

```bash
git add <files-this-wp-touched>
git commit -m "<conventional commit per GIT-03>"
git push -u origin feat/wp-NNN-<slug>
```

The commit message follows GIT-03:

```
<type>(wp-NNN): <subject ≤ 72 chars>

<body explaining why, citing WP-NNN, ADR-NNN, TDD §X.Y, change
primitive>

Refs: WP-NNN, ADR-NNN, TDD-X.Y
Co-Authored-By: sulis-execution executor (1M context) <noreply@sulis.ai>
```

The `git add` is targeted — list exactly the files this WP modified.
**Never `git add .`** (catches untracked files; security-relevant).
**Never `git add -A`** (same risk).

The push uses `-u` to set the upstream tracking branch.

**Success criterion:** Push accepted (CI on the host triggers
automatically on push).

**Failure handling:**

- Push rejected because remote has commits the local branch doesn't →
  OODA. Likely cause: someone (or another executor) pushed to the
  same branch. Decide: this should not happen because branch names
  are WP-keyed; halt + escalate (out of scope — concurrent executor
  collision is the orchestrator's problem).
- Push rejected by branch protection on the feature branch → OODA.
  Unusual; feature branches normally aren't protected. Halt +
  escalate.
- Pre-commit hook fails → OODA. The hook is signal. Five Whys to the
  root cause; usually a lint issue the formatter didn't catch.
  Apply the minimum fix; re-commit; re-push. In scope. **Never
  `--no-verify`** per GIT-09.
- Commit-msg hook rejects the commit format → OODA. Check the commit
  message against GIT-03; usually a missing field. Amend the
  commit; re-attempt. In scope.

**Budget:** 2 attempts per `self-heal-budget.md` for push rejection
(the count is low because most push rejections are out-of-scope
collisions).

---

## Step 8 — Poll CI; on green, squash-merge directly to `dev` (no PR)

> **v0.9.0 ownership note.** Steps 8 through 11 below are run by the
> **calling session** via `wpx-pipeline run` (Steps 8-10), the
> `sulis-security:security-reviewer` Agent (Step 11 verdict), and
> `wpx-findings register` / `auto-draft-wp` + `wpx-journal
> record-postdeploy` (Step 11 bookkeeping). The mechanism descriptions
> below are reference material for the pipeline script's internals and
> for diagnosis when the pipeline fails. The executor does NOT perform
> these steps. See "Calling-session invocations (Steps 8-12)" near the
> top of this file for the canonical invocation sequence.


**Input:** Branch pushed from step 7; CI triggered automatically by
the push.

**Action (Continuation Discipline applies; agent-level polling loop, not single long Bash call):**

1. **Detect host.** Inspect `git remote get-url origin` to determine
   the host (GitHub, GitLab, Bitbucket, self-hosted).

2. **Detect feature-branch CI presence.** From Step 1 pre-flight:
   - **`CI_ON_BRANCH=true`** → proceed to step 3 (poll CI normally).
   - **`CI_ON_BRANCH=false`** → fall back to local pre-commit gate
     per GIT-04 v0.1.3 Local Pre-commit Fallback subsection:
     - Run lint, type-check, full test suite, secret-scan locally
       in the worktree.
     - Record in journal under `## Pre-commit gate (local — feature-branch CI not wired)`.
     - Skip to step 4 (rebase-on-dev verification).

3. **Poll CI via background poller with auto-notification (v0.8.3+
   — handles 15-30 min real CI durations cleanly).**

   Real CI pipelines take 15-30 minutes, not 30-60 seconds. The
   v0.8.2 short-Bash-per-poll pattern works but burns agent turns
   (30+ iterations per WP) and exhausts the previous 15-min budget
   well before realistic pipelines finish. The harness's first-class
   mechanism for "wait until done" is `run_in_background: true`:
   the agent kicks off a background poller, the harness auto-notifies
   the agent when it completes, no agent turns burned on waiting.

   Per the system prompt: *"For one-shot 'wait until done,' use Bash
   with run_in_background instead."* And: *"When an agent runs in the
   background, you will be automatically notified when it completes
   — do NOT sleep, poll, or proactively check on its progress."*

   The polling sub-step has three parts:

   **3a. Initial foreground check.** Cheap; might already be terminal.

   ```bash
   gh api repos/<owner>/<repo>/commits/$BRANCH_SHA/check-runs \
     --jq '[.check_runs[] | {name, status, conclusion}]'
   ```

   If all checks are `status == "completed"` already → parse
   conclusions, advance based on result.

   **3b. If not yet terminal, kick off the background poller.**
   Inside a backgrounded Bash, long `sleep` is allowed (the "long
   leading sleep blocked" rule applies to foreground Bash only — in
   backgrounded shells, `sleep 300` runs normally).

   ```
   Bash({
     command: """
       until gh api repos/<owner>/<repo>/commits/$BRANCH_SHA/check-runs \
             --jq '[.check_runs[] | .status] | all(. == "completed")' \
             | grep -q true; do
         sleep 300
       done
       gh api repos/<owner>/<repo>/commits/$BRANCH_SHA/check-runs \
         --jq '[.check_runs[] | {name, conclusion}]'
     """,
     run_in_background: true,
     timeout: 2700000   // 45 min — covers worst-case CI + buffer
   })
   ```

   The background shell:
   - Polls every 5 minutes (`sleep 300`).
   - Exits the `until` loop when every required check has
     `status == "completed"`.
   - Emits the final conclusions array as stdout.

   **3c. Wait for harness notification.** The agent does NOT poll
   the background process. The harness sends a notification when
   the background Bash exits. The agent reads the stdout (final
   conclusions array) and:

   - All `conclusion in {"success", "skipped", "neutral"}` → CI
     green → advance to step 4.
   - Any `conclusion == "failure"` → CI failure → OODA per
     EL-01..08.
   - Any `conclusion == "cancelled"` → check `cancelled_by` field:
     - **Workflow-triggered cancellation** (concurrency / superseded
       by newer push) → check whether a subsequent run on the same
       branch covers this SHA or a descendant; if yes, wait for that
       run; if no, re-trigger via `gh run rerun <run-id>`.
     - **Human cancellation** (`cancelled_by` is a username, not a
       bot) → see "Human cancellation mid-pipeline" subsection below.
   - Background timeout (45 min elapsed) → treat as terminal failure;
     OODA.

   **Configurable poll interval (v0.8.3+, optional).** WPs that need
   a different cadence can set `ci_poll_interval_seconds` in
   frontmatter (default 300):

   ```yaml
   ci_poll_interval_seconds: 600   # 10-minute polls for slow projects
   ```

   The skill reads this and substitutes the value into the
   background-poller `sleep` command.

4. (Original step 3 — see the rebase-on-dev section below.) Verify
   dev hasn't advanced before squash-merging. Same as v0.8.1; the
   re-CI wait after rebase uses the same background-poller pattern.

**Continuation Discipline at the agent level.** The agent does NOT
return control to its caller while the background poller is running
— it's parked on the tool result, awaiting the harness's
notification. The agent's "session" is preserved across the
background wait. When the notification arrives, the agent resumes
processing in the same conversation thread. No agent-turn budget
consumed during the wait.

### Human cancellation mid-pipeline (v0.8.2+)

A founder, ops engineer, or another tool may cancel a CI run or
deploy via the host's UI mid-WP. The executor detects this via the
host's API (`conclusion: cancelled` with a `cancelled_by` field
naming a human user, not a bot or workflow trigger).

When detected:

1. **Read the host's API** to distinguish human cancellation from
   workflow-triggered cancellation:
   ```bash
   gh api repos/<owner>/<repo>/actions/runs/<run-id> \
     --jq '{conclusion, status, cancelled_by: .triggering_actor.login,
            event: .event}'
   ```
   If `cancelled_by` is `github-actions[bot]` or empty AND `event`
   indicates concurrency cancellation, treat as workflow-triggered
   (handled in step 3 above). If `cancelled_by` is a real username,
   treat as human cancellation.

2. **Read the host's API** to identify whether a SUBSEQUENT run on
   the same branch (for CI) or on dev (for deploy) covers the same
   SHA OR a descendant SHA that includes this WP's code:
   ```bash
   gh run list --workflow="<workflow-name>" --branch=<branch> \
     --json databaseId,headSha,status,conclusion --limit 10
   ```

3. **Decision:**
   - **Covering run exists** (subsequent run on same SHA OR
     descendant SHA): wait for that run instead. The cancellation
     was redundant or superseded by newer work.
   - **No covering run exists**: re-trigger the cancelled workflow
     (`gh run rerun <run-id>` or equivalent). The executor's budget
     for "CI failure" or "deploy failure" applies (re-triggers
     count against the same budget as failures).

4. **Journal-record the human-cancellation event** under
   `## Human-cancellation events`:
   ```markdown
   - 2026-05-18T19:45Z: CI run 26056486348 cancelled by iainn.
     Covering run identified: 26056501608 (SHA 417d1c314, descendant
     of WP-7 SHA). Waiting for covering run.
   ```

**The pattern is: human intervention is signal, not error.** The
executor doesn't fight it — it reads the host API, identifies the
downstream effect on its WP, and integrates the cancellation into
the lifecycle.

3. **Verify dev hasn't advanced (GIT-05 step-4, v0.8.1+).** Before
   squash-merging, check whether dev has moved forward since this
   branch was created. If it has — likely because a parallel peer
   merged — rebase on the new dev HEAD and re-run CI before merging.

```bash
git fetch origin dev
CURRENT_DEV=$(git rev-parse origin/dev)
RECORDED_DEV=$(cat .executor-WP-NNN-dev-sha)

REBASE_ATTEMPTS=0
while [ "$CURRENT_DEV" != "$RECORDED_DEV" ]; do
  REBASE_ATTEMPTS=$((REBASE_ATTEMPTS + 1))
  if [ "$REBASE_ATTEMPTS" -gt 2 ]; then
    # Budget exhausted — branch can't catch up with a moving target
    # (high-parallelism workload; dev keeps advancing during each
    # CI re-run). Halt + BLOCKER per "Merge-to-dev conflict" budget.
    echo "Rebase budget exhausted (dev kept advancing through 2 rebases)"
    exit 124
  fi

  echo "dev advanced ($RECORDED_DEV → $CURRENT_DEV); rebasing (attempt $REBASE_ATTEMPTS)"
  git rebase origin/dev
  # If rebase has file conflicts, exit non-zero — OODA fires per EL-01..08.
  # Bash rebase exit code is the rebase outcome; check it.

  git push --force-with-lease

  # Record new dev SHA and wait for CI on rebased branch.
  echo "$CURRENT_DEV" > .executor-WP-NNN-dev-sha
  BRANCH_SHA=$(git rev-parse HEAD)

  # Re-run the same CI-poll loop above (extracted for clarity here).
  DEADLINE=$(( $(date +%s) + 900 ))
  while true; do
    CHECKS=$(gh api repos/<owner>/<repo>/commits/$BRANCH_SHA/check-runs ...)
    # ... same poll logic as above ...
  done

  # Re-fetch dev — it may have moved again while we were rebasing + re-CI'ing.
  git fetch origin dev
  CURRENT_DEV=$(git rev-parse origin/dev)
  RECORDED_DEV=$(cat .executor-WP-NNN-dev-sha)
done

# Loop exits when CURRENT_DEV == RECORDED_DEV — safe to merge.
echo "dev is stable at $CURRENT_DEV; proceeding to squash-merge"
```

This sub-step prevents the parallel-merge race: WP-A's CI was green
against dev@SHA1, but WP-B merged in between (advancing dev to SHA2).
A direct squash-merge would land WP-A against stale-CI'd dev. The
rebase forces re-CI against current dev.

For sequential single-WP runs, dev never advances during the WP's
lifetime, so `CURRENT_DEV == RECORDED_DEV` and the rebase loop is
skipped entirely (zero overhead).

Budget: 2 rebase attempts per `self-heal-budget.md` "Merge-to-dev
conflict" row. If dev keeps advancing through 2 rebases (livelock
risk under very high parallelism), halt + BLOCKER. Suggested next
step in the BLOCKER: *"WP-A couldn't catch up with a moving dev —
try reducing max_parallel or retry WP-A when the slice is calmer."*

4. **On green AND dev-stable, squash-merge to `dev`** using the host's
   merge API (no PR opened):
   - GitHub: `gh api -X POST repos/<owner>/<repo>/merges` with
     base=dev, head=feat/wp-NNN-<slug>, merge_method=squash. Or, if
     the host requires a PR object even for direct merges (some
     GitHub Enterprise configs), open a PR and immediately
     squash-merge it via `gh pr merge --squash --delete-branch`.
   - GitLab: `glab api projects/.../merge_requests` POST with
     squash=true and source/target. Same fallback.
   - Self-hosted: project-specific merge API, else `git checkout
     dev && git merge --squash feat/wp-NNN-<slug> && git commit -m
     "<merged-message>" && git push origin dev`. Local merge only
     used when the remote API isn't available — branch protection
     still gates the push.
5. **Delete the remote branch** post-merge (`git push origin
   :feat/wp-NNN-<slug>`).

**Success criterion:** Squash-merge commit lands on `dev`; remote
branch deleted; `dev` HEAD now includes the WP's change.

**Failure handling:**

- **CI fails on the branch** → OODA fires. Read the failed-check log
  verbatim (the host's API exposes it). Five Whys to root cause.
  Common patterns:
  - Test passes locally but fails on CI → environment difference.
    Often an unset env var, a hardcoded path, or a missing fixture.
    In scope: fix the test setup.
  - Lint fails on CI but passed locally → version skew between
    local linter and CI linter. In scope: pin the linter version
    or adjust the config to match.
  - Build fails on CI → check for committed-but-not-tested files
    (missing imports, unstaged files). In scope.
  - CI failure is in a job the WP didn't touch (unrelated regression
    landed on `dev`) → out of scope. The base `dev` is broken; the
    executor can't fix it. BLOCKER with `"dev is broken — fix dev
    first."`
- **Merge conflict** → OODA fires. Rebase the feature branch on
  `dev` HEAD (`git fetch origin && git rebase origin/dev`), resolve
  trivial conflicts (imports, formatting, line-number-only
  collisions), re-push, re-poll CI. **Never** `git checkout --theirs`
  or `--ours` (loses information). After 2 rebase attempts, halt +
  escalate — the conflict is structural and needs human resolution.
- **Squash-merge API call fails** → OODA. Check whether branch
  protection's required-checks list is satisfied; check whether the
  executor's auth token has merge permissions. If auth issue, halt
  + escalate (out of scope — auth is operator's). If required-checks
  list has a check that didn't run, halt + escalate (CI config issue,
  out of scope).
- **Remote branch deletion fails after merge** → log a warning in
  the journal but proceed. The merge already happened; orphan branch
  cleanup is a separate concern that doesn't gate the WP.

**Budget:** CI failure 3 attempts; merge conflict 2 attempts.

**The no-PR rule (GIT-05) is non-negotiable.** Even when the host
requires a PR object to mechanically perform the merge, the executor
opens-and-immediately-merges so the PR exists only for the merge
API's benefit, not as a review ceremony. No reviewer is added; no
discussion is invited; the PR exists for milliseconds.

---

## Step 9 — Wait for staging deploy

**Input:** `dev` HEAD with the WP's squash-merge commit (from step 8).

### Deploy-mechanism detection (MUST run first)

Different projects deploy in different ways. The executor detects
the project's deploy mechanism **before** taking action:

1. **Auto-deploy on push (most common in modern CD setups).** The
   push to `dev` (from step 7) automatically triggers a CI/CD
   workflow that deploys to staging. The deploy is **already in
   flight** by the time step 8 begins.

   Detection: look for any of these signals in the project root:
   - `.github/workflows/*.yml` with `on: push: branches: [dev]`
     and a deploy job.
   - `.gitlab-ci.yml` with `deploy_to_staging:` stage triggered on
     `dev`.
   - `.circleci/config.yml`, `azure-pipelines.yml`, etc with
     equivalent triggers.
   - A `deploy-on-push: true` flag in `.sulis/manifest.yaml`.

   If detected: skip the "trigger" sub-step; jump to "wait for
   the in-flight deploy workflow to complete."

2. **Explicit-trigger via Sulis SDK** (when sulis-platform-sdk is
   integrated).

   Detection: look for a `.sulis/manifest.yaml` with a `deploy:
   sulis-sdk` field, OR a `sulis_sdk` import in the project's
   deploy tooling.

   If detected: call `client.deploy.staging(branch='dev',
   sha=<merge_sha>, wp_ref='WP-NNN')` to trigger the deploy. Poll
   `client.deploy.status(deployment.id)` until terminal.

3. **Neither — no automated deploy** (the project doesn't have
   continuous-deployment wired). The executor halts at step 8
   with a BLOCKER recording the gap. Suggested next step:
   *"Wire continuous deployment (Sulis SDK, GitHub Actions, or
   equivalent) so the executor can complete the atomic lifecycle.
   Or accept a partial lifecycle: mark this WP done-at-merge if
   the project intentionally has no auto-deploy."*

### Action for auto-deploy on push (most common case)

Same background-poller + auto-notification pattern as Step 8 (v0.8.3+).
Real deploys take 5-15 min; the 5-minute poll cadence matches.

**Initial foreground check:**

```bash
WORKFLOW="Deploy to Dev Environment"  # read from .github/workflows/
MERGE_SHA=<sha-from-step-8>

gh run list --workflow="$WORKFLOW" --commit="$MERGE_SHA" --limit=1 \
  --json status,conclusion,databaseId --jq '.[0]'
```

If `status == "completed"` already → parse `conclusion`, advance.

**If not yet terminal, kick off background poller:**

```
Bash({
  command: """
    WORKFLOW='Deploy to Dev Environment'
    MERGE_SHA='<sha>'
    until gh run list --workflow="$WORKFLOW" --commit="$MERGE_SHA" \
            --limit=1 --json status --jq '.[0].status == "completed"' \
          | grep -q true; do
      sleep 300
    done
    gh run list --workflow="$WORKFLOW" --commit="$MERGE_SHA" --limit=1 \
      --json status,conclusion,databaseId --jq '.[0]'
  """,
  run_in_background: true,
  timeout: 1800000   // 30 min — covers worst-case deploy duration
})
```

**Wait for harness notification.** Agent does not poll the
background process. On notification, agent reads the conclusion:

- `"success"` → advance to step 10.
- `"failure"` → OODA per EL-01..08; fetch failed logs via
  `gh run view <run-id> --log-failed` for verbatim Observe.
- `"cancelled"` → human-cancellation-mid-pipeline subsection below.
- Background timeout (30 min) → treat as terminal failure; OODA.

### Action for explicit Sulis SDK trigger

```python
from sulis_sdk import client
deployment = client.deploy.staging(
    branch='dev',
    sha=<merge_sha_from_step_7>,
    wp_ref='WP-NNN',
)

# Poll in a blocking Python loop (or equivalent Bash via the SDK CLI):
import time
deadline = time.time() + 600  # 10 min cap
while True:
    status = client.deploy.status(deployment.id)
    if status.status == 'succeeded':
        break
    if status.status == 'failed':
        raise DeployFailed(status)
    if time.time() > deadline:
        raise DeployTimedOut(deployment.id)
    time.sleep(15)
```

Same discipline — the call blocks until terminal.

**Success criterion:** `deployment.status == "succeeded"`.

**Failure handling:**

- **Deploy failed with a build error** → OODA. Read the build log
  verbatim from `client.deploy.logs(deployment.id)`. Five Whys.
  Common cause: a file was modified locally but not committed
  (executor bug — escalate).
- **Deploy failed with a registry / dependency error** → out of
  scope (platform-side). BLOCKER.
- **Deploy failed because staging is at capacity** → out of scope
  (infra). BLOCKER (canonical example — see Example 2 in
  executor-loop-standard.md).
- **Poll timeout (10 min elapsed)** → treat as deploy-failed,
  OODA fires. Likely cause: deploy is hung; staging is in a bad
  state.

**Budget:** 3 attempts.

---

## Step 10 — Health-check + Smoke-test

**Input:** Deployment URL from step 9 (or the staging URL from the
project's `.sulis/manifest.yaml` if auto-deploy doesn't surface a
per-deploy URL); WP's `## Smoke Test` section.

This step is two sub-actions in sequence: first verify the deploy is
healthy (health-check), then verify it's functionally correct
(smoke-test). Both must pass before advancing to Step 11. If
health-check fails, smoke-test does not run.

### Sub-action A — Poll health-checks

Two paths depending on what's wired:

**With Sulis SDK:**

```python
health = client.health.staging(deployment_id)
# Returns healthy | degraded | unhealthy | unknown
```

**Without Sulis SDK — direct probe (v0.8.3 background-poller pattern):**

Health checks typically resolve within 1-5 minutes of a fresh deploy
(container warm-up). The background-poller pattern handles this
cleanly even when warm-up is on the slower end.

**Initial foreground check:**

```bash
HEALTH_URL=$(jq -r '.staging.health_url' .sulis/manifest.yaml \
            2>/dev/null \
            || echo "https://<staging-domain>/health")
curl -s -o /tmp/health-body -w "%{http_code}\n" "$HEALTH_URL"
```

If `200` + body has `status == "healthy"` → advance to sub-action B.

**If not yet healthy, kick off background poller:**

```
Bash({
  command: """
    HEALTH_URL='<url>'
    until response=$(curl -s -o /tmp/health-body -w "%{http_code}" "$HEALTH_URL")
          && [ "$response" = "200" ] \
          && jq -e '.status == "healthy"' /tmp/health-body > /dev/null 2>&1; do
      sleep 60
    done
    echo "healthy"
  """,
  run_in_background: true,
  timeout: 600000   // 10 min — health checks resolve faster than CI/deploy
})
```

The background shell polls every 60 seconds (health-check resolves
quickly once the container warms up; tighter interval than CI/deploy).

**Wait for harness notification.** Agent reads "healthy" → advance.
Timeout (10 min) → treat as terminal failure; trigger rollback per
GIT-10 and OODA.

**(Legacy fallback — kept as a reference for the inline-bash pattern;
no longer the default in v0.8.3+. The background-poller above is the
preferred mechanism.)**

```bash
# Old v0.8.2 pattern, kept for reference only.
HEALTH_URL=$(jq -r '.staging.health_url' .sulis/manifest.yaml \
            2>/dev/null \
            || echo "https://<staging-domain>/health")

ATTEMPTS=0
SLEEP=15
while [ $ATTEMPTS -lt 5 ]; do
  ATTEMPTS=$((ATTEMPTS + 1))
  RESPONSE=$(curl -s -o /tmp/health-body -w "%{http_code}" "$HEALTH_URL")
  if [ "$RESPONSE" = "200" ]; then
    BODY=$(cat /tmp/health-body)
    if echo "$BODY" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
      echo "Healthy"
      break
    fi
  fi
  echo "Attempt $ATTEMPTS: $RESPONSE — backing off ${SLEEP}s"
  sleep $SLEEP
  SLEEP=$((SLEEP * 2))
done

if [ $ATTEMPTS -ge 5 ]; then
  echo "Health-check timed out after 5 attempts"
  exit 1
fi
```

**Blocking.** The Bash call does not return until healthy, budget
exhausted, or terminal failure. Same Continuation Discipline.

**Health-check budget:** 5 attempts.

**Health-check failure handling:**

- **Timeout (warm-up too slow)** → OODA. Likely: new code has a slow
  startup path. In scope: optimise startup (lazy init, async warm-
  up). Or: increase warm-up budget in WP Contract.
- **Consistently unhealthy** → regression in the deployed change.
  Trigger rollback per GIT-10: `git revert` the merge SHA; push the
  revert via the same merge-direct-on-CI-green flow. Mark WP
  `blocked` with BLOCKER pointing at the rollback.

### Sub-action B — Smoke-test

Once health is `healthy`, run the smoke test per the WP's
`## Smoke Test` section. Typical shapes:

- **HTTP endpoint check.** `curl <deploy_url><path>` with expected
  status code and response body assertion.
- **CLI invocation.** Run a binary with known input; verify output.
- **Script.** Run a project-defined smoke-test script
  (`scripts/smoke/wp-NNN.sh`) that exits 0 on success.

**Smoke-test budget:** 2 attempts.

**Smoke-test failure handling:**

- **Known-flaky issue** → OODA. One retry. If still failing, treat
  as real failure.
- **Real regression** → OODA. Five Whys. In scope if regression is
  in WP Contract files; out of scope otherwise. If out of scope,
  trigger rollback per GIT-10 and BLOCKER.
- **Smoke-test infrastructure missing** (WP's `## Smoke Test`
  section blank, script not found) → escalate. Smoke-test definition
  is SEA's responsibility (WP-template field); missing it is a
  contract breach.

**Success criterion:** Health-check passes AND smoke-test passes.

After Step 10 advances, the deploy is functionally correct. The WP
is **not yet done** — Step 11 (post-deploy verification) runs next
to catch any security/quality regression before final mark-done.

---

## Step 11 — Post-deploy verification (security-reviewer agent)

**Input:** Merge SHA from step 8, staging URL from step 9-10, WP
frontmatter (optional `post_deploy_verification` field).

**Default behaviour: always-on.** When the WP frontmatter does not
specify `post_deploy_verification`, the executor treats it as
`security` (the default). Step 11 fires on every WP unless the WP
explicitly opts out via `post_deploy_verification: none`.

This is by design during the v0.6 calibration period — the founder
is observing what the security-reviewer surfaces in practice before
deciding whether to dial the default down to opt-in.

**Action:**

1. Read the WP frontmatter for `post_deploy_verification`. Allowed
   values:
   - `security` (DEFAULT — applies when field is absent) — spawn
     the security-reviewer agent.
   - `security+performance` — additionally trigger perf regression
     checks if available (placeholder for future).
   - `none` — explicit opt-out; skip Step 11; advance to Step 12.
     **Reserved for WPs where the assessment is provably redundant**
     (e.g. a docs-only WP touching no source files). Use sparingly.

2. **If not `none`**: spawn the security-reviewer agent via Agent
   tool, passing both the merge SHA AND the staging URL so the
   agent performs static code analysis **and** passive deployed-
   surface checks (HTTP headers, TLS, file exposure) in one run:

   Read the WP frontmatter for an optional `security_model` field
   (one of `haiku | sonnet | opus`). If present, include the `model`
   parameter in the Agent call. Otherwise omit — the security-
   reviewer inherits the executor's model (which itself inherited
   from the calling session, typically Opus).

   ```
   Agent({
     subagent_type: "sulis-security:security-reviewer",
     description: "Post-deploy security assessment for WP-NNN",
     model: <security_model from WP frontmatter, if present>,
     prompt: """
   Run /sulis-security:codebase-assess <project> <repo> <staging-url>
   against the dev branch at merge SHA <sha>, with the live staging
   URL <staging-url> for passive deployed-surface checks.

   Focus on primitives potentially affected by this WP's changed
   files (listed in WP Contract section). Report findings by
   severity per the security-standard.

   Continuation Discipline applies: complete the assessment OR
   identify a BLOCKER-worthy CRITICAL finding before returning.
   """,
   })
   ```

   The Agent call blocks the executor's turn until the security-
   reviewer returns. Continuation Discipline applies to the
   wrapping executor too — the executor does not return control
   while the security-reviewer is running.

3. Read the resulting `.security/{project}/viability-report-*.md`.
   Triage findings by severity per the security-standard.

### CRITICAL findings — halt + BLOCKER

Halt + write BLOCKER per EL-08 referencing the security finding.
The WP introduced or exacerbated a critical issue and is not done.

### Non-CRITICAL findings — findings register + auto-draft WPs (v0.7+)

For each CONCERN or ADVISORY finding produced by the security-reviewer,
the executor runs this sequence:

1. **Compute the finding's signature.** Hash of severity + summary +
   primary file path (e.g. SHA-1 over `CONCERN|HSTS missing on Cloud
   Run|deploy/cloudrun.yaml`). The signature deduplicates findings
   across WPs.

2. **Check the findings register** at
   `.security/{project}/findings-register.md`. The register is an
   append-only ledger maintained across all WPs in the project.

   - **If the signature already appears**: append a register row
     noting "Duplicate of SF-NN observed on WP-NNN (no new draft
     created)." Do **not** create a new SF file or auto-draft WP.
     Cross-reference both source WPs' acceptance evidence to the
     existing SF for traceability.
   - **If the signature is new**: continue to step 3.

3. **Allocate an SF-NNN ID.** Read+increment a counter at
   `.security/{project}/SECURITY.yaml` (`next_finding_id` field).
   Format: `SF-001`, `SF-002`, ...

4. **Write the finding file** at
   `.security/{project}/findings/SF-NNN-<slug>.md`:

   ```markdown
   ---
   id: SF-NNN
   severity: CONCERN | ADVISORY
   signature: <hash>
   source_wp: WP-NNN
   detected_at: <ISO-8601>
   primitive: SEC-NN | DAT-NN | etc. (from sulis-security catalogue)
   ---

   ## Summary

   <One-paragraph plain-English summary AAF-compliant for the concierge.>

   ## Evidence

   <File:line, tool output snippet, response header, git range —
   exactly as the security-reviewer produced it.>

   ## Suggested fix

   <Recommendation from the security-reviewer; will become the basis
   of the auto-draft WP's Contract section.>

   ## Cross-references

   - Source WP: WP-NNN
   - Auto-draft WP: WP-AUTO-NNN (created by this Step 11 run)
   - Duplicate observations: <if any, list other WPs that observed
     this same finding>
   ```

5. **Append the register entry** to
   `.security/{project}/findings-register.md`:

   ```markdown
   | SF-NNN | <severity> | <one-line summary> | <source WP> | <signature> | <auto-draft WP ID> | <disposition> |
   ```

   Disposition starts as `pending-review`. Final dispositions
   recorded by the concierge during Phase 5 slice-end review (see
   concierge agent prompt): `approved` (run the auto-draft WP),
   `cancelled` (founder declined; rationale required), `duplicate-of-WP-NN`
   (founder merged into existing WP).

6. **Allocate a WP-AUTO-NNN ID.** Read+increment a counter at
   `.architecture/{project}/work-packages/INDEX.md`'s header
   `next_auto_wp_id`.

7. **Create the auto-draft WP** at
   `.architecture/{project}/work-packages/WP-AUTO-NNN-<slug>.md`:

   ```markdown
   ---
   id: WP-AUTO-NNN
   title: <short title from finding summary>
   status: auto-draft
   sequence_id: WP-AUTO-NNN
   dependsOn: [<source_wp>]   # the WP that surfaced the finding
   blocks: []
   primitive: Secure | Harden  # default per finding category
   group: reinforce
   source_finding: SF-NNN
   severity: CONCERN | ADVISORY
   disposition: pending-review
   pillar: armor
   estimated_token_cost: {input: ?, output: ?}  # SEA fleshes out on approval
   tdd_section: null  # SEA fleshes out on approval
   adrs: []
   ---

   ## Context

   Auto-drafted from security finding SF-NNN (severity: <CONCERN | ADVISORY>),
   surfaced during Step 11 of WP-NNN. See
   `.security/{project}/findings/SF-NNN-<slug>.md` for the full finding.

   ## Contract

   <Skeleton — SEA fleshes out when this WP is approved by the
   founder via the concierge's slice-end review.>

   ## Definition of Done

   <Skeleton — SEA fleshes out.>

   Suggested fix from security-reviewer:

   > <verbatim from SF-NNN's Suggested fix section>

   ## Sequence

   <Skeleton — SEA fleshes out.>
   ```

8. **Update INDEX.md** to include the new auto-draft WP. Its row:
   `| WP-AUTO-NNN | <title> | Secure | auto-draft | WP-NNN | — | ? | ? |`
   Plus a section header `### Auto-drafts from security findings (N
   pending-review)` if not already present.

9. **Append to source WP's acceptance evidence** under the
   `## Post-deploy verification` subsection:

   ```markdown
   ## Post-deploy verification

   Security-reviewer verdict: <PASS | N CONCERN | N ADVISORY findings>

   New findings (this WP):
   - SF-NNN (<severity>): <one-line summary> → auto-draft WP-AUTO-NNN
   - SF-NNN (<severity>): <one-line summary> → auto-draft WP-AUTO-NNN

   Duplicate findings (already in register):
   - SF-NNN (<severity>): same signature observed on WP-NNN
   ```

10. **Immediately advance to Step 12 — do NOT return control.**
    Continuation Discipline (executor.md) covers this boundary
    explicitly. The auto-draft WPs sit in the INDEX with `status:
    auto-draft`; the orchestrator skips them from normal dispatch
    until the founder approves them via the concierge's slice-end
    review.

**Important: auto-draft WPs do NOT run automatically.** They're
visible in INDEX but skipped by the orchestrator. The founder owns
the disposition decision (run / cancel / merge into existing WP) —
that's a real product decision about scope, not a process decision,
per Decision Discipline. The concierge surfaces auto-draft WPs at
slice-end in plain English; the founder dispositions them; the
concierge updates each WP's `disposition` and `status` fields.

**For PASS verdict (no findings) — same advance rule applies.**
No SF files, no auto-drafts, no register entries beyond a
"verdict: PASS" line in the source WP's acceptance evidence.
Immediately advance to Step 12 — do NOT return control. This is
the most-likely cognitive trap (executor "feels done" after PASS
verdict and exits before bookkeeping).

**Success criterion:** Security-reviewer completed; findings (if
any) registered + auto-drafted + cross-referenced; results captured
in journal under `## Step trace` row for Step 11 with Completed
timestamp. **Then the executor exits cleanly — Step 12 is the
calling session's responsibility, not the executor's (v0.8.3+).**

**Step 11 is the executor's last step.** After the security-reviewer
returns (any non-CRITICAL verdict) and the journal records the
outcome, the executor's contract is complete. The executor exits;
the calling session reads the journal and performs Step 12
bookkeeping inline. This was changed in v0.8.3 — see the rationale
in Step 12 below.

**Failure handling:**

- **Security-reviewer agent itself errors** (not a finding — a
  tooling failure like assessor crash or missing dependencies) →
  OODA. Budget 2 attempts. After exhaustion, the BLOCKER records
  the assessor failure as out-of-scope (sulis-security plugin issue,
  not the WP's) and notes "Step 11 could not run; assess manually
  before marking done."
- **Security-reviewer returns CRITICAL** → halt + BLOCKER per
  EL-08. The BLOCKER's `## Failure observation (verbatim)` is the
  CRITICAL finding's full text; `## Five Whys trace` drills into
  the vulnerability's root cause; `## Scope verdict` is in-scope if
  the cause is in the WP's Contract files (in which case the WP
  can be fixed via retry), out-of-scope if elsewhere (rollback +
  separate investigation).

**Budget:** 2 attempts for assessor tooling errors. CRITICAL
findings are not retried — they're halt-and-escalate.

**v0.6 calibration period note.** This step is currently always-on.
The founder is monitoring what the assessor surfaces across WPs to
calibrate signal-vs-noise. If the assessor produces too many
false-positive CONCERN/ADVISORY findings (or too few CRITICAL ones),
the default may be dialled down to opt-in (`post_deploy_verification:
security` becomes opt-in via SEA's decompose for security-sensitive
WPs only). Decision deferred until empirical evidence.

---

## Step 12 — Mark done + worktree cleanup (calling session, not executor)

**Important architectural change (v0.8.3+):** Step 12 is no longer
the executor's responsibility. It is performed by the **calling
session** — typically the run-all skill, the run-wp skill, or the
founder's main session — after the executor returns from Step 11.

### Why this changed in v0.8.3

The founder observed a recurring late-lifecycle failure mode across
multiple WPs: executors completed Steps 1-11 cleanly (substantive
engineering done, CI green, deploy succeeded, security review PASS)
and then drifted at Step 12. Three patterns:

1. *"Monitor will notify me"* — executor parked waiting for a
   notification that wasn't coming.
2. *"Advancing to Step 12"* — executor wrote the phrase but exited
   without doing it.
3. *"Report not written because I know the verdict"* — executor
   rationalised that holding the verdict in memory sufficed without
   persisting it.

Root cause: the executor was 200+ tool calls deep by the time it
reached Step 12. Continuation Discipline is *policy, not mechanism*
— the prompt forbids returning before Step 12, but nothing in the
runtime prevents the agent from drifting at depth.

**The fix is architectural, not motivational:** remove Step 12 from
the executor. The executor's job is the engineering work (Steps
1-11). Step 12 is deterministic bookkeeping — three Bash commands +
one Edit + one INDEX update — and doesn't need agent reasoning. It
belongs in a fresh-context caller (the run-all skill, run-wp skill,
or the founder's session) that hasn't accumulated 200 tool calls of
load.

### Calling-session responsibilities

After the executor returns from Step 11 (regardless of outcome), the
calling session:

1. **Reads the executor's journal** at
   `.architecture/{project}/work-packages/.executor-WP-NNN.md`.

2. **Verifies Step 11 completed cleanly:**
   - Step 11 row in journal has a Completed timestamp.
   - `## Post-deploy verification` section is populated.
   - No CRITICAL findings (those would have produced a BLOCKER).

3. **If Step 11 NOT complete** (Completed timestamp missing, OR
   journal shows mid-step drift) → executor parked or errored. The
   calling session does NOT do Step 12. Instead:
   - Classifies the executor exit as `error` per orchestrator
     defence (v0.7.1+).
   - Halts the run-all loop.
   - Surfaces a clear plain-English status line: *"WP-NNN: executor
     returned before Step 11 completed. Likely parked late in
     lifecycle. Re-dispatch via /sulis-execution:run-wp WP-NNN to
     resume from journal."*

4. **If Step 11 complete with CRITICAL finding** → executor wrote a
   BLOCKER per v0.6.0; INDEX status is already `blocked`. Calling
   session does NOT do Step 12 (WP not done). Just propagates
   `dependency_blocked` to transitive descendants and continues.

5. **If Step 11 complete with non-CRITICAL verdict** → calling
   session performs Step 12 inline:

### Action (performed by calling session)

```bash
# Read journal to extract evidence (the executor wrote these during
# Steps 1-11).
WP=WP-NNN
PROJECT=<project-slug>
JOURNAL=.architecture/$PROJECT/work-packages/.executor-$WP.md

# Extract from the journal's Step trace and Post-deploy verification:
BRANCH=$(grep '^- Branch:' "$JOURNAL" | head -1 | awk '{print $3}')
PRESQUASH=$(grep 'Pre-squash SHA' "$JOURNAL" | head -1 | awk '{print $NF}')
MERGE_SHA=$(grep 'Squash-merge SHA on dev' "$JOURNAL" | head -1 | awk '{print $NF}')
DEPLOY_URL=$(grep 'Deployment URL' "$JOURNAL" | head -1 | awk '{print $NF}')
SMOKE=$(grep 'Smoke-test verdict' "$JOURNAL" | head -1 | sed 's/.*verdict: //')
SECURITY=$(grep 'Security-reviewer verdict' "$JOURNAL" | head -1 | sed 's/.*verdict: //')
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

Then via Edit tool, append to the WP file at
`.architecture/{project}/work-packages/WP-NNN-<title>.md`:

```markdown
## Acceptance Evidence

- Branch: `feat/wp-NNN-<slug>` (deleted post-merge)
- Pre-squash SHA: `<presquash>`
- Squash-merge SHA on dev: `<merge_sha>`
- Deployment URL: `<deploy_url>`
- Health status: `healthy`
- Smoke-test verdict: `<smoke>`
- Post-deploy verification: `<security>`
- Completed: `<now>` (Step 12 by calling session)
```

Then update INDEX.md to flip the WP's status from `in_progress` to
`done`.

Then remove the worktree:
```bash
git worktree remove ../wp-NNN-worktree
# Acceptable to use --force if the worktree has stale tracking files
# the executor cleaned up during step 11 cleanup.
```

Then emit the plain-English status line:
*"WP-NNN done — deployed and healthy at <url>. Smoke-test passed.
Security assessment: <PASS | N CONCERN | N ADVISORY>."*

### Success criterion (calling session)

- WP file has `## Acceptance Evidence` block with all journal-derived
  fields.
- INDEX status is `done` with timestamp.
- Worktree removed.
- Status line emitted.

### What this fixes

- **No more late-lifecycle drift.** The executor's contract ends at
  Step 11 success; Step 12 happens in a fresh context that hasn't
  accumulated deep load.
- **Bookkeeping is deterministic and reliable.** Three Bash + one
  Edit + one INDEX update; takes ~30 seconds; can't drift because
  there's no reasoning to drift on.
- **Parked executors are detectable.** If the executor returns
  without Step 11 completed in the journal, the calling session
  classifies as `error` and surfaces explicitly. No silent
  "looks-done-but-isn't" states.

### Recovery for previously-parked WPs

For WPs in the parked state from before this version (Steps 1-11
complete on dev but no `## Acceptance Evidence` and worktree still
present), apply the same Step 12 mechanics manually:

1. Read the WP's `.executor-WP-NNN.md` journal.
2. Append `## Acceptance Evidence` to the WP file using journal data.
3. Edit INDEX to flip status to `done`.
4. Remove the worktree.

Roughly 30 seconds per WP. Founder or concierge can do this for any
already-parked WPs as a one-off cleanup before next run-all.

After Step 12 succeeds, the WP is **done** in the full atomic sense
the founder articulated: implemented, tested, documented, merged,
deployed, healthy, smoke-tested, security-verified. The orchestrator
(v0.4) reads the INDEX, sees `status: done`, marks the WP off, and
picks the next ready WP.

If any of Steps 5-11 escalated, the worktree is **left in place** as
evidence per the executor-loop-standard's scope-guard / BLOCKER
discipline. The BLOCKER record points at the worktree path. Cleanup
happens only when the BLOCKER is resolved.

---

## v0.6 exit shape

In v0.6, after Step 12 succeeds:

1. Full `## Acceptance Evidence` block on WP file (branch, pre-
   squash SHA, merge SHA, deploy URL, health status, smoke verdict,
   post-deploy verification, timestamp).
2. INDEX entry → `status: done`.
3. Local worktree removed.
4. Plain-English status line emitted.
5. Exit.

The WP is now atomically done in the full sense:
implementation, tests, docs, lint, commit, push, CI, merge,
deploy, health, smoke, security verification — all green.

---

## Composition with executor-loop-standard.md

Every step's failure-handling section above is shorthand for "run
the EL-01..08 spiral." The OODA loop's discipline (verbatim
Observe, bounded Five Whys, minimum-change Decide, re-run-the-failed-
step Act) applies uniformly. The per-step notes above name the
common patterns and the scope-guard verdicts; the spiral mechanics
are uniform.

When the spiral terminates with escalation, the BLOCKER record
(EL-08 format) goes to
`.architecture/{project}/work-packages/BLOCKER-WP-NNN.md`. The
executor exits cleanly after writing it.
