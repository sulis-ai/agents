# Executor Lifecycle

The 12-step contract the executor runs per Work Package. Each step has
input artifacts, a success criterion, a failure-handling OODA recipe
(per `executor-loop-standard.md`), and an escalation trigger.

Version coverage: v0.1 implements steps 1-6. v0.2 adds step 7. v0.3
adds steps 8-10. v0.6 adds step 5 (docs) and step 11 (post-deploy
verification); v0.6 also collapses health + smoke into one step 10.
v0.7 adds findings register + auto-draft WPs at step 11.

**On parallel execution (v0.8+).** Each WP's executor runs in its
own `git worktree` per GIT-07. The 12-step lifecycle is identical
whether the executor is running solo or as part of a parallel batch
of N — the executor doesn't know which mode it's in, and shouldn't
care. Concurrent peers have non-overlapping file scopes (the
run-all skill verifies this before dispatching); concurrent worktrees
don't share working files; the `git worktree add` (Step 1) and
worktree removal (Step 12) bracket the per-executor isolation.

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

3. **Poll CI as an agent-level turn loop, not a long-blocking Bash
   call (v0.8.2+ — avoids harness backgrounding heuristic).**

   The harness backgrounds Bash calls whose runtime exceeds its
   threshold heuristic. A `while true; do ...; sleep 30; done` loop
   triggers this and breaks Continuation Discipline silently. The
   fix: each poll is one short Bash call (≤ ~30-60s including
   sleep); the agent re-issues across turns until terminal. Each
   call exits cleanly; the harness doesn't background; the agent's
   turn-level loop is the poll loop.

   Each agent turn issues one short Bash call:

   ```bash
   # First call (no sleep — immediate check):
   gh api repos/<owner>/<repo>/commits/$BRANCH_SHA/check-runs \
     --jq '[.check_runs[] | {name, status, conclusion}]'
   ```

   ```bash
   # Subsequent calls (sleep 30 + one check):
   sleep 30 && gh api repos/<owner>/<repo>/commits/$BRANCH_SHA/check-runs \
     --jq '[.check_runs[] | {name, status, conclusion}]'
   ```

   The agent parses each result. Terminal states:
   - All `status == "completed"` AND no `conclusion in {failure,
     cancelled, timed_out}` → CI green → advance to step 4.
   - Any `conclusion == "failure"` → CI failure → OODA per EL-01..08.
   - Any `conclusion == "cancelled"` → check `cancelled_by` field:
     - **Workflow-triggered cancellation** (concurrency / superseded
       by newer push) → check whether a subsequent run on the same
       branch covers this SHA or a descendant; if yes, wait for that
       run; if no, re-trigger via `gh run rerun <run-id>`.
     - **Human cancellation** (`cancelled_by` is a username, not a
       bot) → see "Human cancellation mid-pipeline" subsection below.

   Budget for total poll wall-time: 15 minutes (~30 agent-turn
   iterations at 30s each). After budget, treat as CI timeout (exit
   124-equivalent).

4. (Original step 3 — see the rebase-on-dev section below.) Verify
   dev hasn't advanced before squash-merging. Same as v0.8.1; uses
   the same short-Bash-per-poll pattern for the re-CI wait after
   rebase.

**Continuation Discipline.** The agent does NOT return control to
its caller (the run-all loop or the founder's session) while
polling. Each Bash call returns; the agent reads the result and
decides whether to re-issue. The agent's turn-level loop is the
load-bearing mechanism; Bash's job is the single short status check.

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

```bash
# Identify the deploy workflow's name from the project's CI config.
# Common names: "Deploy to Dev Environment", "deploy-staging",
# "Deploy", "CD".
WORKFLOW="Deploy to Dev Environment"  # read from .github/workflows/
MERGE_SHA=<sha-from-step-7>

# Wait up to 20 minutes for the workflow run triggered by the merge
# push to complete.
DEADLINE=$(( $(date +%s) + 1200 ))
while true; do
  STATUS=$(gh run list \
    --workflow="$WORKFLOW" \
    --commit="$MERGE_SHA" \
    --limit=1 \
    --json status,conclusion,databaseId)
  if [ "$(echo "$STATUS" | jq -r '.[0].status')" = "completed" ]; then
    CONCLUSION=$(echo "$STATUS" | jq -r '.[0].conclusion')
    if [ "$CONCLUSION" = "success" ]; then
      echo "Deploy succeeded"
      break
    else
      echo "Deploy failed: $CONCLUSION"
      RUN_ID=$(echo "$STATUS" | jq -r '.[0].databaseId')
      gh run view "$RUN_ID" --log-failed  # verbatim log for OODA Observe
      exit 1
    fi
  fi
  if [ "$(date +%s)" -gt "$DEADLINE" ]; then
    echo "Deploy poll timed out after 20 minutes"
    exit 124
  fi
  sleep 30
done
```

The Bash call **blocks** until success, failure, or timeout. The
executor does not return control during this wait.

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

**Without Sulis SDK — direct probe:**

```bash
HEALTH_URL=$(jq -r '.staging.health_url' .sulis/manifest.yaml \
            2>/dev/null \
            || echo "https://<staging-domain>/health")

# Exponential backoff: 15s, 30s, 60s, 120s, 240s — up to 5 attempts.
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
in source WP's acceptance evidence; **executor has advanced to Step
12 in the same turn.**

**Step 11 → Step 12 transition is part of the atomic unit.** After
the security-reviewer returns (any non-CRITICAL verdict), the next
action in the same executor turn is Step 12. Returning control here
is a Continuation Discipline violation — equivalent to returning
after CI green pre-merge. The WP is not done until Step 12 success.

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

## Step 12 — Mark done + worktree cleanup

**Input:** Successful Step 11 (PASS, CONCERN, or ADVISORY — anything
that wasn't CRITICAL). This step runs **in the same executor turn**
as Step 11's completion — Continuation Discipline forbids returning
control between Step 11 and Step 12.

**This step is required.** Skipping or deferring Step 12 leaves the
WP in an indeterminate state (INDEX not updated, worktree not
removed, acceptance evidence not appended). The orchestrator
classifies an executor exit without Step 12 success as `error` and
halts; the journal-resume mechanism picks the WP back up at Step 12
on re-dispatch. Either way the bookkeeping happens — the question is
whether it happens cleanly in the executor's own turn (cheap,
canonical) or via recovery (expensive, audit-trail-noisy).

**Action:**

1. Append the full evidence block to the WP's `## Acceptance
   Evidence` section:

   ```markdown
   ## Acceptance Evidence

   - Branch: `feat/wp-NNN-<slug>` (deleted post-merge)
   - Pre-squash SHA: `<sha>`
   - Squash-merge SHA on dev: `<sha>`
   - Deployment URL: `<url>`
   - Health status: `healthy`
   - Smoke-test verdict: `PASS — <one-line summary>`
   - Post-deploy verification: `<PASS | N CONCERN | N ADVISORY>` (see
     .security/{project}/viability-report-<date>.md for detail)
   - Completed: `<ISO-8601>`
   ```

2. Update INDEX entry to `status: done`.
3. Remove the local worktree (`git worktree remove
   ../wp-NNN-worktree`).
4. Emit one plain-English status line for the orchestrator / invoking
   session: `"WP-007 done — deployed and healthy at <url>. Smoke-test
   passed. Security assessment: PASS (no findings) / N CONCERN
   findings logged."`
5. Exit cleanly.

**Success criterion:** Evidence appended; INDEX updated; worktree
removed; status line emitted.

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
