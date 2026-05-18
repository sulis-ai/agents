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

   ```
   Agent({
     subagent_type: "sulis-security:security-reviewer",
     description: "Post-deploy security assessment for WP-NNN",
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
