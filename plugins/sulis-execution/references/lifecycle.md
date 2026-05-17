# Executor Lifecycle

The 10-step contract the executor runs per Work Package. Each step has
input artifacts, a success criterion, a failure-handling OODA recipe
(per `executor-loop-standard.md`), and an escalation trigger.

v0.1 implements steps 1-6. v0.2 adds step 7. v0.3 adds steps 8-10.

---

## Step 1 — Worktree + branch

**Input:** WP file (read), `dev` branch HEAD on remote.

**Action:**

```bash
git fetch origin
git worktree add ../wp-NNN-worktree -b feat/wp-NNN-<slug> origin/dev
cd ../wp-NNN-worktree
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

**Success criterion:** All tests still pass after refactor.

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

## Step 5 — Lint / type / format

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

## Step 6 — Commit (Conventional Commits) + push branch

**Input:** Clean working tree from step 5, GIT-03 (commit message
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

## Step 7 — Poll CI; on green, squash-merge directly to `dev` (no PR)

**Input:** Branch pushed from step 6; CI triggered automatically by
the push.

**Action (blocking — Continuation Discipline applies):**

1. **Detect host.** Inspect `git remote get-url origin` to determine
   the host (GitHub, GitLab, Bitbucket, self-hosted).
2. **Poll the CI status** for the branch HEAD commit in a **blocking
   Bash loop** that does not return until terminal:

```bash
BRANCH_SHA=<sha-from-step-6>
DEADLINE=$(( $(date +%s) + 900 ))  # 15 min cap

# GitHub example. Adapt for GitLab (glab api), Bitbucket, etc.
while true; do
  CHECKS=$(gh api repos/<owner>/<repo>/commits/$BRANCH_SHA/check-runs \
           --jq '[.check_runs[] | {name: .name, status: .status, conclusion: .conclusion}]')

  # Are all required checks completed?
  PENDING=$(echo "$CHECKS" | jq '[.[] | select(.status != "completed")] | length')

  if [ "$PENDING" = "0" ]; then
    # All completed. Did any fail?
    FAILED=$(echo "$CHECKS" | jq '[.[] | select(.conclusion != "success" and .conclusion != "skipped" and .conclusion != "neutral")] | length')
    if [ "$FAILED" = "0" ]; then
      echo "CI green"
      break
    fi
    echo "CI failed: $(echo "$CHECKS" | jq -c '[.[] | select(.conclusion == "failure")]')"
    exit 1
  fi

  if [ "$(date +%s)" -gt "$DEADLINE" ]; then
    echo "CI poll timed out after 15 min"
    exit 124
  fi
  sleep 30
done
```

The Bash call blocks the executor's turn until CI is terminal. The
executor does not return control mid-poll (Continuation Discipline).
4. **On green, squash-merge to `dev`** using the host's merge API
   (no PR opened):
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

## Step 8 — Wait for staging deploy

**Input:** `dev` HEAD with the WP's squash-merge commit (from step 7).

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

## Step 9 — Poll health-checks

**Input:** Deployment URL from step 8 (or the staging URL from the
project's `.sulis/manifest.yaml` if auto-deploy doesn't surface a
per-deploy URL).

**Action:**

Two paths depending on what's wired:

### With Sulis SDK

```python
health = client.health.staging(deployment_id)
```

- Returns `healthy` | `degraded` | `unhealthy` | `unknown`.

### Without Sulis SDK — direct probe

The executor hits the deployed app's health endpoint directly. The
endpoint comes from the project's manifest or the deploy workflow's
output URL.

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

**Success criterion:** `health.status == "healthy"` within budget.

**Failure handling:**

- **Health-check timeout (warm-up too slow)** → OODA. Five Whys.
  Likely: the new code has a slow startup path. In scope: optimise
  the startup (lazy init, async warm-up). Or: increase the health-
  check warm-up budget in the WP's Contract.
- **Health-check fails consistently** → likely a regression in the
  deployed change. Out of scope as a fix (the deploy is what's
  unhealthy; the WP code itself may be fine, but the env may be
  wrong). Trigger rollback per GIT-10: `git revert` the merge SHA;
  push the revert to `dev` via the same merge-direct-on-CI-green
  flow. Mark WP `blocked` with BLOCKER pointing at the rollback.

**Budget:** 5 attempts (exponential backoff covers slow starts).

---

## Step 10 — Smoke-test + mark done

**Input:** Healthy deployment from step 9; WP's `## Smoke Test`
section (added to WP-format in v0.3 by SEA's decompose skill).

**Action:**

1. Run the smoke test per the WP's specification. Typical shapes:
   - **HTTP endpoint check.** `curl <deploy_url><path>` with
     expected status code and response body assertion.
   - **CLI invocation.** Run a binary with known input; verify
     output.
   - **Script.** Run a project-defined smoke-test script
     (`scripts/smoke/wp-NNN.sh`) that exits 0 on success.
2. On success:
   - Update INDEX entry: `status: done`.
   - Append to WP's `## Acceptance Evidence`:

     ```markdown
     ## Acceptance Evidence

     - Branch: `feat/wp-NNN-<slug>` (deleted post-merge)
     - Pre-squash SHA: `<sha>`
     - Squash-merge SHA on dev: `<sha>`
     - Deployment URL: `<url>`
     - Health status: `healthy`
     - Smoke-test verdict: `PASS — <one-line summary>`
     - Completed: `<ISO-8601>`
     ```

   - Remove the worktree: `git worktree remove ../wp-NNN-worktree`.
   - Emit plain-English status line: `"WP-007 done — deployed and
     healthy at <url>. Smoke-test passed."`
   - Exit cleanly.

**Success criterion:** Smoke-test asserts pass; INDEX updated;
worktree removed.

**Failure handling:**

- **Smoke-test fails on a known-flaky issue** → OODA. One retry
  (budget 2 total). If still failing, treat as a real failure.
- **Smoke-test fails on a real regression** → OODA. Five Whys.
  Common cause: the deployed change broke something the WP didn't
  intend to break. In scope if the regression is in the WP's
  Contract files; out of scope otherwise. If out of scope, trigger
  rollback per GIT-10 and BLOCKER.
- **Smoke-test infrastructure missing** (WP's `## Smoke Test`
  section blank or script not found) → escalate. Smoke-test
  definition is SEA's responsibility (WP-template field); missing
  it is a contract breach.

**Budget:** 2 attempts.

After step 10 succeeds, the WP is **done** in the full atomic sense
the founder articulated: implemented, tested, merged, deployed,
healthy, smoke-tested. The orchestrator (v0.4) reads the INDEX,
sees `status: done`, marks the WP off, and picks the next ready WP.

---

## v0.3 exit shape

In v0.3, after step 10 succeeds:

1. Append the full evidence block to the WP's
   `## Acceptance Evidence` section (branch, pre-squash SHA,
   merge SHA, deploy URL, health status, smoke verdict, timestamp).
2. Update INDEX entry to `status: done`.
3. Remove the local worktree (`git worktree remove
   ../wp-NNN-worktree`).
4. Emit one plain-English status line for the orchestrator /
   invoking session: `"WP-007 done — deployed and healthy at
   <url>. Smoke-test passed."`
5. Exit.

The WP is **done** in the founder's full-atomic sense: implemented,
tested, merged, deployed, healthy, smoke-tested. The orchestrator
(v0.4) picks the next ready WP from the INDEX.

If step 10 escalates (smoke fails on a regression, infrastructure
missing, etc.), the worktree is **left in place** as evidence per
the executor-loop-standard's scope-guard / BLOCKER discipline. The
BLOCKER record points at the worktree path. Cleanup happens only
when the BLOCKER is resolved.

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
