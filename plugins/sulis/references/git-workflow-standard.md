# Git Workflow Standard

<!-- summary -->
A marketplace-wide encoding of how branches, commits, merges, and releases
flow. Two long-lived branches: `dev` (integration, CI-gated, deploys to
staging) and `main` (production-deploy marker, updated only on release
cut). Feature branches merge **directly to `dev`** via squash-merge when
CI on the branch is green — **no PR ceremony**. Branch protection on
`dev` enforces the CI-green status check; that is the quality gate.
`main` is promoted from `dev` only with explicit founder authorisation.
Conventional Commits 1.0.0 for commit messages. SemVer 2.0.0 for release
tags. No `--no-verify`, no force-push to protected branches, no hook
bypass.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period (90 days from 2026-05-16)
> **Applies to:** All agents and projects in the Sulis AI marketplace,
> and any downstream project an executor or orchestrator operates on.

---

## Provenance

This standard codifies a practice the existing rules implied but did not
encode. Convention Preference (CP-01..CP-05) says *"default to the
established convention"* but never named *which* convention for git
flow. A production session in which the founder said *"I don't want to
start until we have a clear view on the git/branching strategy"*
surfaced the gap.

The branching model is a variant of the simplified two-branch
production pattern (dev / main) common in continuous-deployment shops:
`dev` behaves as `main` traditionally would (integration, CI-gated,
deploys to staging) and `main` is the production-deploy marker. This is
neither full GitFlow (which adds `release/*`, `hotfix/*`, `develop`,
`feature/*` ceremonies) nor pure trunk-based development (which has no
integration buffer). It is the middle ground that gives autonomous
executors a CI-gated landing strip without the overhead of release
branches.

The **no-PR-ceremony rule** (GIT-05) is the load-bearing departure from
the GitHub-default workflow. Pull requests exist as a human-review
ceremony. For autonomously-executed Work Packages, a human review
either rubber-stamps (adds no value) or blocks (defeats autonomous
execution). CI is the gate; branch protection enforces it; the merge is
the action.

---

## Boundary Definition

This standard governs **git branching, commits, merges, and releases**
across the marketplace. It does NOT govern:

- CI configuration shape (build steps, runners, caches) — project-specific.
- Code review for human-authored PRs — not in the autonomous-executor path.
- Code style or formatting — that is `boring-code.md` and language-specific lint configs.
- Deployment plumbing — covered by `executor-loop-standard.md` (steps 8-10 of
  the lifecycle) and the Sulis SDK contract.
- Issue tracking, project management, sprint mechanics — out of scope.

The intersection between this standard and others is explicit at GIT-09
(no `--no-verify` composes with the security standard) and the
Composition section.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification (an ADR or equivalent decision record). |

---

## GIT-01: Two-branch model — `dev` and `main` (MUST)

Every project the marketplace operates on has two long-lived branches:

- **`dev`** — the **integration branch**. Behaves as `main` traditionally
  would: protected, CI-gated, all feature work lands here. Deploys to
  staging on every merge.
- **`main`** — the **production-deploy marker**. Updated only when `dev`
  is promoted to production (the release cut). Deploys to production
  on every update.

Feature branches always branch off `dev` and merge back to `dev`.
**Feature branches never target `main` directly.** A WP that lands in
`dev` is "done" from the executor's perspective; promotion to `main` is
the founder's separate ceremony (per GIT-06).

There is **no `develop`, no `release/*`, no `hotfix/*`** ceremony. If a
production hotfix is needed, the fix lands in `dev` first (full executor
lifecycle), then `dev → main` is promoted immediately. The simpler
two-branch model loses no capability and removes ceremony.

---

## GIT-02: Branch naming (MUST)

Feature branches follow the pattern:

```
<type>/<wp-or-scope>-<slug>
```

Where:

- **`<type>`** ∈ `feat` | `fix` | `chore` | `docs` | `refactor` | `test`
  | `perf` | `ci` | `build` | `style` (same set as Conventional Commits).
- **`<wp-or-scope>`** — for Work-Package-driven work, this is the WP
  ID in lowercase: `wp-007`. For ad-hoc work not tied to a WP, use a
  short scope name: `auth`, `billing`, etc.
- **`<slug>`** — kebab-case description, ≤ 50 chars, describes the
  branch's intent.

Examples:

- `feat/wp-007-cancel-subscription-flow`
- `fix/wp-012-idempotency-key-collision`
- `chore/wp-018-deprecate-legacy-billing-adapter`
- `docs/architecture-decision-records-index`

Branches are deleted post-merge (per GIT-05). Long-lived feature
branches are forbidden — if work cannot complete inside one branch
within a reasonable cycle time, the WP is too large and should be
re-decomposed.

---

## GIT-03: Commit message format — Conventional Commits 1.0.0 (MUST)

Every commit message follows Conventional Commits 1.0.0
(https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **`<type>`** — same enum as GIT-02 branch naming.
- **`<scope>`** — optional. For WP-driven commits, the WP ID in
  lowercase: `feat(wp-007): cancel-subscription flow`.
- **`<subject>`** — imperative mood (*"add"*, not *"adds"* or
  *"added"*); ≤ 72 chars; no trailing period.
- **`<body>`** — optional; explains *why* (not *what* — diff shows
  what). Wraps at 72 chars. For executor-produced commits, the body
  cites the WP ID, the TDD section, the change primitive applied, and
  the ADRs referenced.
- **`<footer>`** — `BREAKING CHANGE: <description>` when applicable;
  `Refs: WP-NNN, ADR-NNN`; co-author trailers for executor-authored
  commits.

### Example (executor-authored)

```
feat(wp-007): cancel-subscription flow

Implements the customer-initiated cancellation path. TDD §3.4
covers the adapter shape; ADR-014 records the chosen state-machine
encoding (terminal state `cancelled`, no resurrection path).
Change primitive: Compose (wires existing billing + notification
adapters).

Refs: WP-007, ADR-014, TDD-3.4
Co-Authored-By: sulis-execution executor (1M context) <noreply@sulis.ai>
```

The squash-merge commit on `dev` (GIT-05) takes the executor's commit
message verbatim. Pre-squash commits on the feature branch may be less
disciplined (`WIP`, `fixing tests`, etc.) — the squash discards them.

---

## GIT-04: Branch protection (MUST)

Both long-lived branches are protected at the host level (GitHub /
GitLab / Bitbucket branch protection rules).

### `dev` protection

- **Required status checks** before merge:
  - CI test suite green.
  - Lint clean.
  - Type-check clean.
  - Secret-scan clean (no new secrets flagged; per security standard).
- **Force-push disabled.** History on `dev` is append-only.
- **No PR review required.** CI is the gate; see GIT-05.
- **Direct commits disabled** — `dev` only receives merges from feature
  branches.
- **Linear history required.** Squash-merge only; no merge commits from
  feature branches.
- **CI concurrency must support concurrent runs across different
  feature branches** (load-bearing for sulis-execution v0.8.0+ parallel
  dispatch). Workflow concurrency rules that cancel in-progress runs
  globally — `concurrency: group: <static>, cancel-in-progress: true`
  — **break parallel dispatch** by terminating one branch's CI when
  another branch pushes. The acceptable shape is **per-branch
  concurrency keying**:

  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
  ```

  This allows different branches to run concurrently while still
  cancelling stale runs on the same branch (e.g. after a rebase push).
  Equivalent shapes in GitLab CI, CircleCI, etc. — the principle is
  the same: concurrency keyed by branch, not globally.

### CI must run on feature branches (MUST, v0.1.3+)

Required status checks fire **on every feature-branch push**, not
only on merge to `dev`. Without feature-branch CI, the merge gate is
*post-merge* — broken code can land on `dev` before any CI catches
it. The executor's "verify CI green before squash-merge" step
(GIT-05 mechanics step 3) presumes CI runs on the branch; without
it, the executor falls back to a local pre-commit substitute (see
the fallback subsection below) which has known weaknesses.

Example trigger config for GitHub Actions (Conventional Commits
prefix globs from GIT-02):

```yaml
on:
  push:
    branches:
      - dev
      - main
      - 'feat/**'
      - 'fix/**'
      - 'chore/**'
      - 'docs/**'
      - 'refactor/**'
      - 'test/**'
      - 'perf/**'
      - 'ci/**'
      - 'build/**'
      - 'style/**'
```

Equivalent shapes apply for GitLab CI (`workflow.rules` keyed on
`$CI_COMMIT_REF_NAME`), CircleCI (`triggers` with branch filters),
Bitbucket Pipelines (`branches:` selectors), etc.

Branch protection on `dev` then names the feature-branch CI run as a
required status check. Most hosts auto-link the status check from
branch protection to the workflow run on the merged commit's
ancestor SHA — so the gate fires both at the branch level (during
the run) and at the dev-merge level (when branch protection
verifies before allowing the merge).

### Confirm CI by reading the conclusion, not a shell exit code (MUST, v0.1.4+)

The CI-green gate (GIT-04 above; GIT-05 merge-mechanics step 3) only
holds if the agent reads the **CI conclusion** — not a shell exit
code that happens to be `0`. When confirming CI for a feature branch
**read the conclusion explicitly**:

```bash
# Authoritative: read the recorded conclusion (expect "success").
gh run view <run-id> --json conclusion -q .conclusion

# Or watch with the exit status wired through (exits non-zero on failure):
gh pr checks <branch> --watch
```

- **NEVER** trust a chained `; echo $?` after `gh run watch`. The
  `echo` always exits `0`, so `$?` reports the **echo's** exit code,
  not `gh`'s — a guaranteed false green.
- **NEVER** use `gh run watch` *without* `--exit-status` as a gate
  signal. Plain `gh run watch` exits `0` on run **completion**
  regardless of pass/fail; only `--exit-status` makes the exit code
  track the conclusion.

This is the single guardrail that defends the don't-merge-on-red gate
against a hand-typed CI watch. A red merge on a foundation branch has
already slipped through this way (issue #59); the marketplace tooling
(`wpx-train` / `wpx-pipeline` read the verdict explicitly; the
`/sulis:change` ship flow uses `gh pr checks --watch`) is safe — the
rule exists so an agent improvising an ad-hoc watch cannot reintroduce
the false green. GIT-05's merge-mechanics step 3 (*"poll CI status …
on green, proceed"*) is governed by this subsection: "green" means
`conclusion == success`, never a bare exit `0`.

### Local pre-commit fallback (SHOULD when feature-branch CI is absent)

When a project's CI does not yet run on feature branches (legacy
projects, work-in-progress setup), the executor's gate becomes the
**local pre-commit suite** (test + lint + type-check + secret-scan
run in the worktree before push). This is acceptable as a
transitional state but has known weaknesses:

- Local machine state may differ from CI runners (Python version,
  dependency versions, OS).
- The executor's local pass doesn't prove the code passes on shared
  infrastructure.
- No audit trail external to the executor's session.

When operating in fallback mode:

1. The executor records the substitution in the WP journal under
   `## Pre-commit gate (local — feature-branch CI not wired)`,
   listing the commands run and their outcomes.
2. The executor surfaces a recommendation in its run-all status
   line: *"WP-NNN: feature-branch CI not configured; used local
   pre-commit gate. Recommend wiring feature-branch CI per GIT-04
   before scaling parallel dispatch."*
3. The concierge surfaces this recommendation to the founder at
   slice-end.

The fallback is a SHOULD pattern, not MUST — projects must
eventually wire feature-branch CI to satisfy GIT-04's full MUST
requirement. The pattern exists to keep the executor unblocked
during the transitional period, not to license the gap permanently.

### `main` protection

- **Direct commits disabled** — `main` only receives merges from `dev`.
- **Required status check:** the same CI suite as `dev`, plus any
  production-gate checks (e.g. canary deploy succeeded on dev).
- **Force-push disabled.**
- **Promotion requires founder authorisation** — per Decision Discipline
  (sulis concierge), `main` promotion is a hard-to-reverse external-
  blast-radius action. The concierge surfaces it to the founder; the
  founder confirms; only then does the executor or orchestrator perform
  the promotion (GIT-06).

---

## GIT-05: Direct merge to `dev` — no PR ceremony (MUST)

**Feature branches merge directly to `dev` via squash-merge when CI on
the branch is green.** No pull request is opened. No human review is
required. Branch protection (GIT-04) enforces the CI-green status check;
that is the quality gate.

### Mechanics

1. Executor commits to feature branch following GIT-03.
2. Executor pushes the feature branch to the remote. The push triggers
   CI on the branch.
3. Executor polls CI status (per `executor-loop-standard.md` self-heal
   budget). On green, proceeds to step 4. On red, runs OODA + Five Whys
   per the loop standard. **"Green" means `conclusion == success`, read
   explicitly — never a bare shell exit `0`.** See GIT-04 *"Confirm CI
   by reading the conclusion, not a shell exit code"* for the exact
   commands and the two never-rules.
4. **Verify dev hasn't advanced since CI ran (load-bearing for parallel
   dispatch, sulis-execution v0.8.1+).** Fetch the latest dev. Compare
   the current `origin/dev` SHA against the dev SHA recorded when the
   branch was created (per executor lifecycle Step 1, sidecar file
   `.executor-WP-NNN-dev-sha`).

   - **dev hasn't moved** → safe to squash-merge directly; proceed to
     step 5.
   - **dev has moved** → rebase the branch on the new dev HEAD,
     `git push --force-with-lease`, wait for CI on the rebased branch
     to be green (blocking poll per Continuation Discipline), update
     the sidecar file with the new dev SHA, then re-verify in case dev
     moved again. Bounded by the "Merge-to-dev conflict" budget
     (2 attempts in `self-heal-budget.md`); after exhaustion, halt +
     BLOCKER — the branch can't catch up with a moving target.

   This sub-step prevents the parallel-merge race: WP-A's CI was green
   against dev@SHA1, but WP-B merged in between, advancing dev to
   SHA2. A direct squash-merge would land WP-A's change against a dev
   state different from what its CI tested. The rebase forces a
   re-test against current dev.

5. Executor performs `git merge --squash` of the (now-rebased) feature
   branch into `dev` (or the equivalent via the host's API), using
   the executor's commit message verbatim.

6. Branch is deleted from the remote.

### Anti-pattern: `git switch dev` from a worktree (v0.1.3+)

**Do NOT `git switch dev` (or `git checkout dev`)** from a parallel
worktree to perform the merge locally. Two reasons:

1. `git switch dev` fails when `dev` is already checked out by
   another worktree (the founder's main session, or another parallel
   executor's bookkeeping worktree). Git refuses multi-checkout of
   the same ref — the operation returns *"fatal: 'dev' is already
   checked out at '<other-path>'"*. Under v0.8.0+ parallel dispatch,
   this is the normal state, not an exception.
2. Even if it succeeded, local-merge-then-push doesn't generate a
   host-API-recognised squash-merge commit shape with the right CI
   triggers; the host's merge-API path is the canonical mechanism.

The correct path is **host-API merge OR refspec push from the
worktree** — both leave the local `dev` ref untouched:

- **Host API (preferred for all cases):**

  ```bash
  gh api -X POST repos/<owner>/<repo>/merges \
    -f base=dev \
    -f head=feat/wp-NNN-<slug> \
    -f merge_method=squash \
    -f commit_message="<executor's commit message verbatim>"
  ```

  Generates a squash-merge commit on the remote with the executor's
  commit message. Works for branches with any number of commits.

- **Refspec push (acceptable shortcut for single-commit branches):**

  ```bash
  git push origin feat/wp-NNN-<slug>:dev
  ```

  Fast-forwards remote `dev` to the branch tip. Same end-state as a
  squash-merge **when the branch has exactly one commit** (which the
  executor's standard workflow produces — one commit per WP per
  GIT-03 commit shape). The branch's single commit lands on dev with
  its commit message intact.

- **Multi-commit feature branches:** must use the host API, not
  refspec push — refspec push would land all intermediate commits
  unsquashed, violating GIT-04's linear-history requirement on dev.

If the executor's worktree somehow accumulates multiple commits
(e.g. multiple Step-3 commits during a complex WP), it must
squash-merge via the host API, not refspec push. Single-commit is
the default; multi-commit is the exception requiring host API.

**Tooling enforces this (v0.75.0+, issue #56).** `sulis-change finish
--merge` is **worktree-aware**: it locates which worktree holds the base
ref (via `git worktree list --porcelain`) and performs the squash-merge
THERE, rather than blind-`git checkout {base}` in the repo root. The norm
above — *a change worktree only ever holds its own change branch; never
`git checkout dev` inside one* — is therefore upheld by the tool, not just
by convention. A worktree only ever has its own `change/*` branch checked
out.

### Worktree lifecycle: remove on ship, recreate on demand (v0.75.0+, issue #56)

On a successful ship, the change's worktree is **removed** (ending the
worktree sprawl that accumulated under parallel dispatch), while the
**branch + change record are kept** as the audit trail. The change-branch
tip is pinned as `shipped_sha` ("the state it was in when we shipped"). The
removal is gated: a worktree with a **live bound session** or with
**genuine uncommitted work** is kept (only regenerable `.changes/` metadata
is safe to discard). `sulis-change recreate <handle>` re-materialises the
worktree on demand — on the kept branch (resume work), or detached at
`shipped_sha` if the branch is gone (view the exact shipped state). This
keeps the #38 "changes stay visible/retraceable" intent (via the branch +
record + cockpit) while the redundant working copy no longer lingers.

### Anti-pattern: `git stash` in a change worktree (v0.74.0+, issue #53)

**Never `git stash` in a change worktree.** The stash stack is shared
per-repository across ALL of that repo's worktrees, so a positional
`git stash pop` (top-of-stack) can grab an **unrelated** sibling
worktree's stash — silent cross-worktree contamination. This already
happened once (the DC-04 incident): a `git stash pop` in a change
worktree popped a hardening stash pushed from a different worktree and
dumped its files in as untracked cruft. To park transient state,
either make a throwaway WIP commit on the branch, or transfer
working-tree work between trees with explicit file movement (capture
`git diff HEAD --binary` + `git ls-files --others --exclude-standard`,
apply into the destination, restore/clean the source) — never the
shared stash stack. See `_wpxlib.transfer_worktree_changes`.

### Rationale

Pull requests are a **human-review ceremony**. For autonomously-executed
Work Packages, a human reviewer either rubber-stamps (adds no value
because they didn't write the code) or blocks (defeats the autonomous
execution that the marketplace is designed to enable). CI is the
quality gate; if the test suite + lint + type-check + secret-scan are
adequate, then green CI is a sufficient pre-merge signal. If they are
not adequate, the answer is to strengthen CI, not to add a human
ratification ceremony on top.

This is **not novel**. CD shops (Netflix, Etsy, Facebook's monorepo)
merge direct to trunk many times per day without per-commit human
review. The Linux kernel has no PRs — it uses Reviewed-by / Signed-off-by
trailers on patches. Trunk-based development is the dominant pattern in
high-velocity engineering organisations.

### When human review is required

The no-PR rule applies to **autonomously-executed WPs only**. Three
categories still require human review (which can be implemented as
either a comment-on-commit flow or a manual `dev → main` ratification):

1. **Hand-authored commits** that did not come from an executor — the
   author asks for review explicitly.
2. **`dev → main` promotion** (per GIT-06) — founder authorisation
   required.
3. **Standards changes** — modifications to anything under
   `plugins/sulis/references/` or `plugins/sulis/references/` follow the
   standards governance process (CONTRIBUTING.md), which does include
   review.

---

## GIT-06: `dev → main` promotion (MUST)

Production releases occur by merging `dev` into `main`. This is a
**fast-forward merge** (or merge commit if fast-forward is not possible)
that **does not squash** — `main` preserves `dev`'s history of
individual WP squash-merges.

### Mechanics

1. **Founder requests promotion.** The concierge surfaces the request
   in plain English (*"You have 12 things ready to ship to production.
   Want to promote them?"*) and waits for explicit confirmation.
2. **Pre-promotion gates.** Same CI suite as `dev`, plus any additional
   production-gate checks (canary deploy on dev healthy for N minutes;
   no open BLOCKER files; security scan clean).
3. **Promotion.** `git merge dev` on `main`. Tag the resulting commit
   with a SemVer release tag per GIT-08.
4. **Production deploy.** Tag push triggers production deploy via the
   Sulis SDK or project-equivalent CD pipeline.
5. **Post-promotion verification.** Production health-checks pass; if
   any fail within the rollback window, automatic revert per GIT-10.

### Cadence

The cadence is **founder-driven, not time-driven**. Continuous-deployment
shops promote on every dev-green; smaller teams promote weekly or per
sprint. The standard does not prescribe; the founder decides per
release.

The concierge tracks the count of dev-merges since the last `main`
promotion and surfaces a gentle nudge if the gap exceeds a sensible
default (e.g. 14 days or 20 unpromoted WPs).

---

## GIT-07: Worktrees for concurrent executors (SHOULD)

When the orchestrator dispatches multiple executors in parallel (per the
orchestrator's parallelism rules), each executor operates in its own
**`git worktree`**, isolated from the others.

### Mechanics

```bash
# At lifecycle step 1 — create the worktree off dev HEAD:
git worktree add ../wp-007-worktree -b feat/wp-007-cancel-subscription dev

# Executor operates in ../wp-007-worktree for steps 2-6 (RGB cycle,
# lint, commit, push). At step 7 the branch is squash-merged into dev
# and the remote branch is deleted.

# At lifecycle step 10 — after WP is marked done in INDEX:
git worktree remove ../wp-007-worktree
```

### Cleanup timing (MUST)

The worktree is removed **at the end of the lifecycle, after the WP is
marked `done` in the INDEX** (step 10) — not at the merge (step 7).

Two reasons:

1. **Diagnosis.** If the deploy (step 8), health-check (step 9), or
   smoke-test (step 10) fails, having the worktree still present lets
   the executor (or a human investigator) examine the build state
   directly. Cleaning up at merge throws away the evidence.
2. **Simpler mental model.** Everything related to one WP exists until
   that WP is done.

The **remote branch** is separately deleted **at step 7** (immediately
after the squash-merge to `dev`). That is about shared-remote hygiene;
the local worktree is about per-WP working state and persists longer.

### On escalation (scope guard fires)

If the executor halts mid-WP via the scope guard (per
`executor-loop-standard.md`), the worktree is **left in place** as
evidence. The orchestrator's `BLOCKER-WP-NNN.md` record points at the
worktree path. Human investigation can inspect the state. Cleanup
happens only when the BLOCKER is resolved (the WP either retries
successfully → mark done → remove worktree, or is permanently abandoned
→ mark abandoned → remove worktree).

### Rationale

Worktrees give each executor a clean working tree with its own
checked-out branch, without the overhead of full repository clones.
Concurrent executors operating on the same repo (single working tree)
would step on each other's checkouts.

### When worktrees are not required

For single-executor (sequential) operation, a single working tree
suffices. v0.1 of the orchestrator is sequential-only, so worktrees are
optional. v0.2+ adds parallelism, at which point worktrees become
required.

---

## GIT-08: SemVer 2.0.0 for release tags (MUST)

Production releases (every `dev → main` promotion) are tagged following
SemVer 2.0.0 (https://semver.org/spec/v2.0.0.html):

- **`vMAJOR.MINOR.PATCH`** — e.g. `v1.4.2`.
- **MAJOR** — breaking changes (incompatible API changes, removed
  features, changed contract semantics).
- **MINOR** — new features added in a backward-compatible manner.
- **PATCH** — backward-compatible bug fixes.
- **Pre-release tags** (`v1.4.2-alpha.1`, `v1.4.2-rc.3`) allowed for
  integration testing on `dev` before promotion to `main`.

Marketplace plugins follow the same convention — concierge `0.1.2` is a
patch over `0.1.1`; SEA `0.11.1` is a patch over `0.11.0`; the marketplace
metadata `1.11.4` is a patch over `1.11.3`.

---

## GIT-09: No hook bypass, no force-push to protected branches (MUST)

The following are **forbidden on protected branches** (`dev`, `main`):

- `--no-verify` (pre-commit, commit-msg, pre-push hook bypass).
- `--no-gpg-sign` / `-c commit.gpgsign=false` (signature bypass).
- `--force` / `-f` push.
- Any equivalent flag in non-`git` tooling that achieves the same
  bypass effect.

Hook failures must be **investigated, not bypassed**. If a hook is
producing false-positives, fix the hook configuration — do not skip
it. Composes with `security-standard.md` (hook bypass on protected
branches is a security-relevant policy violation).

### On unprotected feature branches

- `--force-with-lease` is **permitted** during rebase (the lease
  protects against overwriting upstream changes another executor
  pushed).
- `--force` (without lease) is **discouraged**. Use
  `--force-with-lease` instead.
- `--no-verify` is **discouraged** even on feature branches; if a hook
  is failing, the failure is signal, not noise.

---

## GIT-10: Rollback procedure (MUST)

When a merged WP causes a regression in `dev` (caught by post-merge CI,
staging deploy failure, or smoke-test failure that wasn't caught
pre-merge), the rollback is performed by **reverting the merge commit**
on `dev`.

### Mechanics

1. Identify the offending merge commit SHA on `dev`.
2. `git revert -m 1 <merge-commit-sha>` — creates a new commit that
   undoes the merge.
3. Push the revert commit to `dev` (via the standard merge-direct-on-
   CI-green flow — the revert is itself a small commit that goes
   through CI).
4. The reverted WP is marked **`blocked`** in INDEX, not `pending` —
   the WP needs root-cause investigation before re-attempting.
5. A `BLOCKER-WP-NNN.md` is written with the Five Whys trace and the
   rollback context.
6. The original feature branch is **not** force-reset. The revert is
   its own audit trail; the original branch (if not already deleted)
   stays as evidence.

### Rationale

Reverting (rather than force-pushing to remove the commit) preserves
the audit trail. Someone investigating *"why was this WP rolled back?"*
six months later can see both the original merge commit and the revert,
read the BLOCKER file, and understand the history. Force-pushing erases
that history and breaks any downstream clone.

### Production rollback

If a `main` deploy fails post-promotion, the same procedure applies on
`main`: revert the merge commit, push the revert (with founder
authorisation per GIT-06 — production rollback is itself a hard-to-
reverse external action). The associated `dev` state is also reverted to
keep the two branches consistent.

### Rollback during parallel execution (v0.8.1+)

When a rollback fires while other WPs are in-flight (the realistic case
under `max_parallel > 1` parallel dispatch), the revert commit advances
`dev`. Concurrent executors at GIT-05 step 4 (verify-dev-hasn't-
advanced) detect the change and trigger their own rebase. The rebased
branch may now fail CI because the revert undid a change the in-flight
WP's tests depended on. **That's the right outcome** — the rebased CI
tests against truthful current dev, surfacing the dependency.

Three protocol points:

1. **The rollback executor (the one writing the revert) does NOT
   coordinate with in-flight peers.** It writes the revert, pushes,
   and exits. In-flight peers detect the change via their own GIT-05
   step 4 rebase logic — they don't need to be notified.

2. **An in-flight peer whose CI now fails on the rebased branch**
   enters OODA per `executor-loop-standard.md` (EL-01..08). Five Whys
   often surfaces the revert as root cause: *"Why does test_X now
   fail? → because the rebase pulled in revert commit Y which undid
   the helper test_X depends on."* Scope verdict: out-of-scope (the
   revert is upstream's work, not this WP's). The executor writes a
   BLOCKER citing the revert SHA; the founder decides whether to also
   revert the in-flight peer or proceed with a fix.

3. **The rolled-back WP is marked `blocked`** per the standard GIT-10
   flow (above). Its transitively-dependent WPs become
   `dependency_blocked` automatically on the next orchestrator loop
   iteration.

The discipline is: don't let the rollback silently produce broken dev
states elsewhere. The rebase-on-dev sub-step from GIT-05 catches the
case for in-flight peers; the BLOCKER chain catches it for dependent
peers.

---

## GIT-11: Hot-fix path for production (MUST)

The standard path for any fix is feature branch → `dev` → `main` per
GIT-05 and GIT-06. **There is one bypass for production emergencies.**

A production hot-fix is a fix landed directly on a hot-fix branch off
`main`, merged to `main`, deployed to production, and then backported
to `dev`. This bypass exists because the standard path (fix on dev,
wait for dev's CI, wait for dev → main promotion ceremony) is too slow
when production is actively broken.

### Severity threshold (MUST)

The hot-fix path is permitted **only** when ALL of these hold:

- Production is currently broken (user-facing outage, data integrity
  issue, security incident).
- The fix is provably small and targeted (one bug, one or a few files).
- The standard dev → main path would take longer than the founder can
  accept given the severity.

If any of these fails, use the standard path. *"Convenience"* is not a
hot-fix justification.

### Mechanics

1. **Founder authorisation.** The concierge surfaces the situation; the
   founder explicitly approves the hot-fix path. This is a Decision
   Discipline founder-owned call — the concierge does NOT auto-decide
   this is a hot-fix.
2. **Branch off `main`** (not `dev`): `git checkout -b
   hotfix/<incident-slug> main`.
3. **Apply the fix** with the same RGB discipline as a normal WP:
   failing test, minimum code, mandatory refactor (RGB-01..03). No
   skipping tests. No `--no-verify`.
4. **CI must pass.** Branch protection on `main` requires the same
   status checks as normal merges to `main`.
5. **Squash-merge to `main`** with a Conventional Commits message:
   `fix(hotfix): <subject>` and a `Refs:` footer naming the incident
   (e.g. `Refs: INC-2026-05-18-billing-outage`).
6. **Tag a SemVer patch release** per GIT-08 (e.g. `v1.5.0` →
   `v1.5.1`).
7. **Production deploy** triggered by the tag push.
8. **Backport to `dev` immediately** by cherry-picking the hot-fix
   commit onto a normal feature branch and running it through the
   standard merge-to-dev flow per GIT-05. The backport may require
   minor adaptation if `dev` has since diverged. **Do not leave
   `main` and `dev` in semantic conflict.**

### Post-mortem (MUST)

Every hot-fix triggers a post-mortem document at
`.post-mortems/<date>-<incident-slug>.md` within 48 hours. Includes:
timeline, root cause, what failed in the normal dev → main path
(otherwise why was hot-fix needed?), prevention measures. The
post-mortem is a real document; not a checkbox.

### What hot-fix is NOT for

- Cosmetic fixes (*"the button is the wrong colour"*).
- Performance regressions that aren't user-blocking.
- Tech-debt cleanup.
- Anything where the standard dev → main ceremony is *"annoying"* but
  not actually too slow given the severity.

The concierge and founder enforce this together. When a founder
requests a hot-fix, the concierge surfaces honestly: *"This sounds
like a hot-fix candidate. The standard path would take ~N minutes.
Is production actively broken?"* If no, recommend the standard path.

### Composition with other standards

- **GIT-05 (direct merge to dev — no PR)** — still applies to the
  backport. The hot-fix landed on `main` first; the backport lands on
  `dev` through normal CI + rebase + squash-merge.
- **GIT-06 (dev → main promotion)** — bypassed by hot-fix. Founder
  authorisation per GIT-11 takes the place of the promotion ceremony.
  Hot-fix tags are SemVer patches per GIT-08.
- **GIT-09 (no hook bypass, no force-push)** — fully applies. Hot-fix
  is NOT a license to bypass quality gates. The whole point is to fix
  prod quickly *without* skipping discipline.

---

## Worked Examples

### Example 1 — feature WP, happy path

```
# Executor starts on WP-007.

# Step 1: worktree + branch
$ git worktree add ../wp-007 -b feat/wp-007-cancel-subscription dev
$ cd ../wp-007

# Steps 2-4: RGB cycle (red → green → blue).
$ pytest tests/billing/test_cancel.py  # fails as expected
$ # ... write code ...
$ pytest                                # all green
$ # ... refactor ...
$ pytest                                # still green

# Step 5: lint + type
$ ruff check .
$ mypy src/

# Step 6: commit + push
$ git add .
$ git commit -m "feat(wp-007): cancel-subscription flow

Implements the customer-initiated cancellation path. TDD §3.4
covers the adapter shape; ADR-014 records the chosen state-machine
encoding (terminal state cancelled, no resurrection path).
Change primitive: Compose.

Refs: WP-007, ADR-014, TDD-3.4
Co-Authored-By: sulis-execution executor <noreply@sulis.ai>"
$ git push -u origin feat/wp-007-cancel-subscription

# Step 7: poll CI; on green, squash-merge to dev
# (via host API or equivalent)

# Step 8-10: deploy + health + smoke. Mark WP done.
$ cd ../main-worktree
$ git worktree remove ../wp-007
```

### Example 2 — `dev → main` promotion

```
# Founder confirms via concierge: "yes, promote these 12 WPs."

# Orchestrator (with founder authorisation):
$ git checkout main
$ git merge dev   # fast-forward
$ git tag -a v1.5.0 -m "Release v1.5.0 — adds cancel-subscription, ..."
$ git push origin main --tags

# Production deploy triggered by tag push.
# Health-check window: 10 minutes.
# If healthy → release announced.
# If failing → automatic revert per GIT-10.
```

### Example 3 — parallel-merge race condition + rebase

Two executors running in parallel under `max_parallel: 2`. Both
branches were cut from `dev@SHA1` at the same time.

```
# t=0: both executors at Step 1 — worktrees created from dev@SHA1
$ # WP-A executor:
$ git worktree add ../wp-007 -b feat/wp-007-cancel-flow dev
$ echo "SHA1" > ../wp-007/.executor-WP-007-dev-sha

$ # WP-B executor (in parallel):
$ git worktree add ../wp-008 -b feat/wp-008-cancel-email dev
$ echo "SHA1" > ../wp-008/.executor-WP-008-dev-sha

# t=10min: both executors finish Step 6 (commit + push). CI starts on
# both branches in parallel (CI workflow correctly scoped per-branch
# concurrency, so neither cancels the other — per GIT-04).

# t=25min: WP-B's CI completes first. WP-B's executor enters GIT-05
# step 4 (verify-dev-hasn't-advanced).
$ # WP-B executor:
$ git fetch origin dev
$ CURRENT_DEV=$(git rev-parse origin/dev)   # → SHA1 (still)
$ RECORDED_DEV=$(cat .executor-WP-008-dev-sha)  # → SHA1
$ # Equal — dev hasn't moved. Safe to squash-merge.
$ # ... squash-merge happens via host API; dev becomes SHA2 ...

# t=27min: WP-A's CI completes. WP-A's executor enters GIT-05 step 4.
$ # WP-A executor:
$ git fetch origin dev
$ CURRENT_DEV=$(git rev-parse origin/dev)   # → SHA2 (WP-B merged)
$ RECORDED_DEV=$(cat .executor-WP-007-dev-sha)  # → SHA1
$ # Unequal — dev advanced. Rebase required.
$ git rebase origin/dev
$ git push --force-with-lease
$ echo "SHA2" > .executor-WP-007-dev-sha
$ # Wait for CI on rebased branch (blocking poll per Continuation Discipline)

# t=37min: rebased CI completes green. WP-A's executor proceeds to
# squash-merge. dev becomes SHA3.
$ # Squash-merge via host API; dev now SHA3.

# t=40min: both executors continue through Step 9-12 (deploy, health,
# smoke, mark done). No parallel-merge race; both squash-merges are
# against the actual dev state at merge time.
```

Without the GIT-05 step-4 rebase: WP-A would have squash-merged
against stale dev. If WP-B's merge changed an interface WP-A's code
depends on, WP-A's merged code would be broken on dev — but each
individual CI run had been green.

---

## Anti-Patterns

### "Just let me open a PR for review on this one"

The no-PR rule is universal for executor-authored work. If the executor
has produced code that the founder wants reviewed before it lands,
that is a signal the executor's quality bar is wrong — strengthen CI,
add a checks-as-code rule, or upgrade the WP contract. Don't add a
human-review ceremony for one branch; either CI is enough or it isn't.

### "I'll force-push to clean up the history"

Force-pushing on a protected branch is forbidden (GIT-09). Force-pushing
on a feature branch you're about to merge is *technically* allowed with
`--force-with-lease` during rebase, but the squash-merge to `dev`
flattens the history anyway — the cleanup is automatic. Force-push to
"clean up" pre-squash is wasted effort.

### "We'll cherry-pick the hotfix straight to `main`"

Hotfixes go to `dev` first, then `dev → main` promotion. Cherry-picking
to `main` directly bypasses CI on `dev` and creates a divergence
between the two branches that has to be reconciled later. The two-branch
model is simpler than three+ for a reason — keep it simple.

### "The hook is broken so I'll `--no-verify`"

GIT-09 forbids this. Fix the hook. If the hook is genuinely producing
a false positive, that is a hook bug — file it as such, fix the hook
config, and continue. Bypassing it once teaches everyone (including
future executors) that the hook is optional, which defeats the gate.

### "Three branches: develop, staging, main"

The marketplace standard is **two** branches. Adding `staging` between
`dev` and `main` reintroduces ceremony (when does staging cut from dev?
who promotes staging to main?) without adding capability — `dev` already
deploys to staging on every merge. The third branch is the smell.

### "We'll use merge commits instead of squash-merge for traceability"

Squash-merge produces one commit per WP on `dev`, which is the right
level of granularity for the audit trail. Merge commits preserve every
intermediate commit on the feature branch (`WIP`, `fixing tests`,
`addressing review`) — those are noise, not signal. The audit trail
lives in the squash-merged commit message + the WP file's `##
Acceptance Evidence` section.

---

## Composition with Other Standards

- **Convention Preference (CP-01..CP-05)** — every choice in this
  standard defaults to the established convention. Two-branch dev/main
  is the dominant CD pattern. Conventional Commits is the dominant
  commit-message format. SemVer is the dominant versioning. No
  bespoke alternatives.
- **Engineering Principles (EP-02 / EP-03 / EP-07)** — quality is
  paramount (CI gate enforces; squash-merge ensures clean history;
  branch protection prevents bypass). Reuse first applies inside the
  RGB cycle that produces the commit. Boy Scout scoping means commits
  are tight and the WP file captures the cleanup.
- **Audience-Adapted Framing (AAF-01..AAF-09)** — every founder-facing
  message about git workflow goes through the concierge's translation
  layer. The founder never sees a commit hash, branch name, or merge
  command unless they specifically ask.
- **Decision Discipline (concierge agent)** — the founder owns the
  `dev → main` promotion authorisation (per GIT-06); everything else
  on the path to `dev` is concierge / executor / orchestrator owned.
- **Executor Loop Standard (EL-01..EL-NN — when shipped)** — every
  failure-handling step in the executor's git workflow runs OODA +
  Five Whys + scope guard + self-heal budget per that standard. This
  standard names the git mechanics; the loop standard names the
  diagnosis discipline.
- **Security Standard** — hook bypass on protected branches is a
  security-relevant policy violation. Force-push on protected branches
  is equivalent. No secret values in commit messages or branch names.

---

## Version History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1.0 | 2026-05-16 | Initial draft. Calibration period: 90 days. Promotion to MUST repo-wide requires evidence from three executor sessions in which the standard was followed end-to-end and no rollback was triggered. Encodes GIT-01..GIT-10. Provenance: founder gate-blocked pickup of "Kinds and Tools" work pending a clear git/branching strategy; the standard names the convention defaults that CP-01..CP-05 implied. | Standards team |
| 0.1.1 | 2026-05-17 | GIT-07 tightening — the original draft was ambiguous about worktree cleanup timing (prose said "after merge" while the worked example showed cleanup at end of lifecycle). Founder caught the inconsistency. Now explicit: local worktree removed at lifecycle **step 10** (after WP marked `done` in INDEX), not at the merge. Remote branch is still deleted at step 7 (separate cleanup). New subsection covers the escalation case — worktree left in place when scope guard fires, so the BLOCKER record can point at it. | Standards team |
| 0.1.2 | 2026-05-18 | Parallel-safe merge discipline (load-bearing for sulis-execution v0.8.0+ parallel dispatch). **GIT-04** extended with CI concurrency requirement — workflows must support concurrent runs across different feature branches via per-branch concurrency keying (not global). **GIT-05** mechanics insert a step-4 fetch-dev + rebase-if-advanced + re-CI sub-step before the squash-merge — prevents the parallel-merge race condition where WP-A's CI was green against stale dev that WP-B has since advanced. **GIT-10** extended with "Rollback during parallel execution" subsection — the rollback executor doesn't coordinate with in-flight peers; peers detect via their own GIT-05 step-4 rebase logic; rebased CI surfaces semantic dependencies on the reverted code as BLOCKERs. **NEW GIT-11**: Hot-fix path for production — encodes the bypass for prod emergencies (severity threshold, founder authorisation, hotfix branch off main, RGB discipline preserved, SemVer patch tag, backport to dev within 48 hours, post-mortem MUST). New Example 3 walks through the parallel-merge race scenario showing the rebase resolving it. | Standards team |
| 0.1.3 | 2026-05-18 | First-live-run gaps from WP-7 execution surface two clarifications. **GIT-04** new subsection "CI must run on feature branches (MUST)" — required status checks must fire on every feature-branch push, not only on dev/main pushes. Without feature-branch CI, the merge gate is post-merge and broken code can land before any CI catches it. Example trigger config covers all Conventional Commits prefix globs (feat/, fix/, chore/, etc.) per GIT-02. Plus new subsection "Local pre-commit fallback (SHOULD when feature-branch CI is absent)" — documents the substitute pattern for transitional projects with explicit guard-rails (journal record, recommendation surfaced to founder via concierge). Fallback is SHOULD, not MUST — projects must eventually wire feature-branch CI to satisfy GIT-04's MUST. **GIT-05** new anti-pattern subsection "git switch dev from a worktree" — explicit forbidden mental model (`git switch dev` fails when dev is checked out elsewhere, which is the normal state under parallel dispatch). Canonical merge paths named: host API for all cases (preferred); refspec push (`git push origin feat/wp-NNN:dev`) acceptable shortcut for single-commit branches only; multi-commit feature branches must use host API to satisfy GIT-04's linear-history requirement. Provenance: WP-7 executor improvised both patterns correctly under stress; this commit makes them canonical. | Standards team |
| 0.1.4 | 2026-05-28 | False-green guardrail (issue #59). **GIT-04** new subsection "Confirm CI by reading the conclusion, not a shell exit code (MUST)" — confirming CI MUST read the conclusion explicitly (`gh run view <id> --json conclusion -q .conclusion`, expect `success`; or `gh pr checks --watch`, exit-status-correct). Two never-rules: NEVER trust a chained `; echo $?` after `gh run watch` (the echo's exit is always 0, not gh's); NEVER use `gh run watch` without `--exit-status` as a gate signal (it exits 0 on completion regardless of pass/fail). **GIT-05** merge-mechanics step 3 now cross-references the subsection — "green" means `conclusion == success`, never a bare exit 0. Provenance: a run-all session merged a foundation WP on a RED CI by trusting a hand-typed `gh run watch <id>; echo "exit: $?"`; 9 downstream WPs depended on it. Marketplace tooling (`wpx-train` / `wpx-pipeline`, `/sulis:change` ship) was already safe — this encodes the correct pattern as a citable guardrail so an improvised watch cannot reintroduce the bug. | Standards team |
