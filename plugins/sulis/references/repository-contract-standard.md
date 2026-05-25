# Repository Contract Standard (RC-01..RC-13)

<!-- summary -->
The marketplace-wide specification of what a GitHub repository must look
like before any Sulis agent operates on it. Defines the branching model
operationalised on GitHub (composes with GIT-01..GIT-10), the merge queue
configuration, the required Actions workflows, the environment ladder, the
secrets and tokens, the repository settings, the tag protection, and the
arrival-check protocol the executor runs before touching any branch.
**Strict mode for v1:** if the repo does not conform to every MUST rule,
agents refuse to operate and surface a delta list. No support for repos
that maintain their own process.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period (90 days from 2026-05-19)
> **Applies to:** All Sulis marketplace agents that operate on a GitHub
> repository (`sulis-execution`, `sulis` (concierge) when dispatching the
> executor, `sea` when proposing infrastructure work).

---

## Provenance

GIT-01..GIT-10 defines *how* code moves through branches, commits, and
merges. It does not define *what GitHub must look like* for that workflow
to be operational. Executor runs surfaced this gap repeatedly:

- A repo with `main` as the default branch and no `dev` — the executor's
  branch-creation step failed silently because it assumed `dev` existed.
- A repo without branch protection on `dev` — a parallel-peer rebase
  collision corrupted the merge sequence.
- A repo without a `merge_group` workflow trigger — the speculative-merge
  CI that the batching strategy in `cicd-batching-analysis.md`
  recommends had no entry point.
- A repo where the staging environment used a different deploy token
  name — `wpx-pipeline` could not deploy and produced a misleading
  *"deploy timed out"* BLOCKER.

The pattern: every executor run is gated by N implicit assumptions about
GitHub config. When any assumption breaks, the failure mode is opaque.
This standard makes the assumptions explicit and verifiable.

**The v1 trade-off (strict mode).** The marketplace currently supports
*one* repo shape. Repos with bespoke processes (custom branch names,
trunk-based without dev, GitFlow with `release/*` branches, GitLab Flow
with multiple environments) are unsupported. This is deliberate: the
executor needs deterministic structure to make hard assumptions and fail
predictably. When the marketplace matures, a "compatibility mode" can be
added that adapts to existing repos — but not in v1.

---

## Boundary Definition

This standard governs **the GitHub repository configuration** that the
marketplace's branching, CI, and deployment workflows require. It does
NOT govern:

- The contents of branches, commits, or releases — that is GIT-01..GIT-10.
- The semantics of the executor loop (OODA, Five Whys, scope-guard) —
  that is EL-01..EL-08.
- The contents of the CI scripts themselves (lint commands, test
  commands, build commands) — those are project-specific and supplied by
  the project's own toolchain.
- The cloud-side deployment plumbing beyond the GitHub-side hook — the
  Sulis platform SDK owns the deploy target itself.
- Source-control providers other than GitHub. GitLab, Bitbucket, Gitea
  are out of scope for v1; the contract may generalise later.

---

## Severity Convention

| Severity | Meaning |
|---|---|
| **MUST** | Non-negotiable. Agents refuse to operate on a repo missing any MUST rule. |
| **SHOULD** | Default. Repo without it operates with a journal warning, not a refusal. |
| **MAY** | Permitted option; agent does not check. |

---

## RC-01: Branching Model (MUST)

The repo has exactly two long-lived branches, named verbatim:

- `dev` — integration branch. Default branch. Receives all feature merges.
  Deploys automatically to staging.
- `main` — production marker. Promoted from `dev` only via the
  promotion workflow. Tags + deploys to production.

Feature branches follow the pattern `feat/wp-NNN-<slug>` per GIT-02. They
exist only for the duration of one Work Package and are auto-deleted on
merge to `dev`.

Forbidden branches:
- `master` (use `main`)
- `develop` (use `dev`)
- `release/*`, `hotfix/*`, `feature/*` (GitFlow ceremony — not used here)
- Any branch on the default repo that is neither `dev`, `main`, nor a
  `feat/wp-*` feature branch.

**Check:**
```bash
gh api repos/{owner}/{repo} --jq '.default_branch' | grep -qx dev || echo "FAIL: default branch must be dev"
gh api repos/{owner}/{repo}/branches/dev --silent || echo "FAIL: dev branch missing"
gh api repos/{owner}/{repo}/branches/main --silent || echo "FAIL: main branch missing"
```

---

## RC-02: Branch Protections (MUST)

### `main` protections

- **Required status checks:** none from CI (main only receives merges from
  the dev→main promotion workflow which has already passed full CI on
  `dev`); the promotion workflow's own check IS the gate.
- **Require pull request before merging:** NO. The promotion workflow
  pushes directly via signed commit. PRs on `main` are unsupported.
- **Linear history required:** YES.
- **Restrict pushes:** YES, to the promotion workflow's GitHub App
  identity only.
- **Force pushes:** disallowed (no admin override).
- **Branch deletion:** disallowed.
- **Required signatures:** YES (signed commits enforced).

### `dev` protections

- **Required status checks:**
  - `branch-ci` — the per-PR lint + unit + smoke job (RC-04).
  - `merge-queue-ci` — the speculative-merge integration job (RC-04).
- **Require branches to be up to date before merging:** YES (via merge queue;
  the queue handles rebasing internally).
- **Require merge queue:** YES (see RC-03).
- **Require pull request before merging:** YES (technical mechanism — the
  merge queue requires PRs to function; this is NOT human-review ceremony,
  it is the queue's entry interface).
- **Required approving reviews:** 0 (consistent with GIT-05 no-PR-ceremony;
  CI is the gate, not human review).
- **Dismiss stale reviews:** YES.
- **Linear history required:** YES.
- **Force pushes:** disallowed.
- **Branch deletion:** disallowed.

### Feature branches (`feat/wp-*`)

- No protections.
- Auto-delete on PR merge to `dev` (RC-07).

**Check:**
```bash
gh api repos/{owner}/{repo}/branches/main/protection --silent || echo "FAIL: main has no protection"
gh api repos/{owner}/{repo}/branches/dev/protection --silent || echo "FAIL: dev has no protection"
gh api repos/{owner}/{repo}/branches/dev/protection \
  --jq '.required_status_checks.contexts' | grep -q branch-ci || echo "FAIL: branch-ci not required on dev"
gh api repos/{owner}/{repo}/branches/dev/protection \
  --jq '.required_status_checks.contexts' | grep -q merge-queue-ci || echo "FAIL: merge-queue-ci not required on dev"
```

---

## RC-03: Merge Queue Configuration on `dev` (MUST)

The `dev` branch has GitHub Merge Queue enabled with the following config:

| Setting | Value | Source |
|---|---|---|
| Maximum group size | 5 | GitHub default; conservative starting point per debugg.ai 2025 guide |
| Minimum group size | 1 | Single-WP batches must succeed |
| Maximum entries to build | 3 concurrent | Shopify pattern |
| Status check timeout | 60 min | GitHub default |
| Merge method | Squash | Aligns with GIT-04 |
| Build concurrency | 5 max waiting | One-deep buffer beyond active |

Failure handling: the merge queue ejects a PR after 3 consecutive failed
batch attempts (Shopify failure-tolerance pattern; covers up to 25 %
flake rate).

**Check:**
```bash
gh api graphql -f query='{
  repository(owner: "{owner}", name: "{repo}") {
    mergeQueue { mergingStrategy maxEntriesToMerge mergeMethod }
  }
}' --jq '.data.repository.mergeQueue' || echo "FAIL: merge queue not configured on dev"
```

---

## RC-04: Required Workflows (MUST)

The repo contains exactly these GitHub Actions workflows at the listed
paths, with the listed event triggers. The workflow file *names* are
fixed (the executor reads them by name in the arrival check); the
*contents* are project-specific but must conform to the contract.

| Workflow path | Trigger events | Purpose |
|---|---|---|
| `.github/workflows/branch-ci.yml` | `pull_request` (any branch → `dev`), `push` (on `feat/wp-*`) | Per-WP fast checks: lint + type-check + unit tests + smoke. ≤15 min target. Required check for queue entry. |
| `.github/workflows/merge-queue-ci.yml` | `merge_group` | Speculative-merge integration test. Runs full integration + e2e suite on the synthetic merged ref. Required check before merge to `dev`. |
| `.github/workflows/deploy-staging.yml` | `push` on `dev` | Deploys the merged batch to the `staging` environment. Triggers health-check + smoke downstream. |
| `.github/workflows/health-and-smoke.yml` | `workflow_run` (after `deploy-staging` success) | Polls `/health` until ready; runs smoke test command. Reports status check `staging-health`. |
| `.github/workflows/promote-dev-to-main.yml` | `workflow_dispatch` (manual) | The dev→main promotion ceremony per GIT-06. Cuts a release tag (SemVer) and pushes to `main`. |
| `.github/workflows/release-prod.yml` | `push` on `main` | Deploys `main` to `production` environment. May require manual approval per RC-05. |

**Workflow event details:**

- `branch-ci` must fire on `pull_request` events whose `base_ref` is `dev`
  AND on `push` events to `feat/wp-*` branches. The first gives PR-level
  signal; the second lets the executor short-circuit before opening a PR.
- `merge-queue-ci` must fire ONLY on `merge_group` (not `pull_request` or
  `push`). It runs against the speculative merge ref GitHub creates inside
  the queue.
- `deploy-staging` must NOT fire on `pull_request` — only on `push` to
  `dev` (i.e., after the queue has merged a batch).
- `release-prod` must NOT fire on `push` to `dev` — only on `push` to
  `main`.

**Check:**
```bash
for wf in branch-ci merge-queue-ci deploy-staging health-and-smoke promote-dev-to-main release-prod; do
  test -f ".github/workflows/${wf}.yml" || echo "FAIL: ${wf}.yml missing"
done
```

(The executor's arrival check parses each workflow's `on:` block to
verify the trigger events. Reference YAML in RC-13.)

---

## RC-05: Environments (MUST)

The repo has exactly two GitHub environments:

### `staging`
- **Deploy source:** `dev` branch
- **Protection rules:** none (auto-deploy on push to `dev`)
- **Required reviewers:** none
- **Wait timer:** 0
- **Secrets:** `SULIS_DEPLOY_TOKEN_STAGING`, `HEALTH_URL_STAGING`
- **Variables:** `SMOKE_CMD` (the smoke-test command, e.g. `curl -sf https://staging.example.com/api/ping`)

### `production`
- **Deploy source:** `main` branch
- **Protection rules:** SHOULD require manual approval for v1 (founder
  authorises each promotion). MAY be relaxed to auto-deploy in future.
- **Required reviewers:** at least one (repo owner per CODEOWNERS, RC-10)
- **Wait timer:** 0 (or project-specific cooldown)
- **Secrets:** `SULIS_DEPLOY_TOKEN_PROD`, `HEALTH_URL_PROD`
- **Variables:** `SMOKE_CMD_PROD` (often identical to staging's `SMOKE_CMD`
  but pointed at the production URL)

**Check:**
```bash
gh api repos/{owner}/{repo}/environments --jq '.environments[].name' | sort > /tmp/envs.txt
diff <(echo -e "production\nstaging") /tmp/envs.txt || echo "FAIL: environments must be exactly {staging, production}"
```

---

## RC-06: Required Secrets and Variables (MUST)

### Repository secrets (visible to all workflows)

None required at the repo level. All deploy tokens are scoped per
environment per RC-05.

### Environment secrets (per RC-05)

| Environment | Secret | Format | Purpose |
|---|---|---|---|
| `staging` | `SULIS_DEPLOY_TOKEN_STAGING` | opaque bearer | Authenticates Sulis SDK deploy call |
| `staging` | `HEALTH_URL_STAGING` | https URL | The health endpoint `health-and-smoke` polls |
| `production` | `SULIS_DEPLOY_TOKEN_PROD` | opaque bearer | Authenticates production deploy |
| `production` | `HEALTH_URL_PROD` | https URL | Production health endpoint |

### Repository variables (visible to all workflows, non-sensitive)

| Variable | Format | Purpose |
|---|---|---|
| `SMOKE_CMD` | shell command | The smoke-test command for staging. Auto-detect ready: must include the health URL as a substring for `wpx-pipeline`'s health-path detection. |
| `SMOKE_CMD_PROD` | shell command | The smoke-test command for production. |

**Check:**
```bash
gh secret list --env staging --json name --jq '.[].name' | grep -qx SULIS_DEPLOY_TOKEN_STAGING || echo "FAIL: SULIS_DEPLOY_TOKEN_STAGING missing on staging env"
gh secret list --env staging --json name --jq '.[].name' | grep -qx HEALTH_URL_STAGING || echo "FAIL: HEALTH_URL_STAGING missing on staging env"
gh secret list --env production --json name --jq '.[].name' | grep -qx SULIS_DEPLOY_TOKEN_PROD || echo "FAIL: SULIS_DEPLOY_TOKEN_PROD missing on production env"
gh variable list --json name --jq '.[].name' | grep -qx SMOKE_CMD || echo "FAIL: SMOKE_CMD variable missing"
```

---

## RC-07: Repository Settings (MUST)

| Setting | Required value | API path |
|---|---|---|
| Default branch | `dev` | `default_branch` |
| Allow squash merging | `true` | `allow_squash_merge` |
| Allow merge commits | `false` | `allow_merge_commit` |
| Allow rebase merging | `false` | `allow_rebase_merge` |
| Allow auto-merge | `true` | `allow_auto_merge` |
| Delete head branches on merge | `true` | `delete_branch_on_merge` |
| Allow update branch | `true` | `allow_update_branch` |
| Squash merge commit title | `PR_TITLE` | `squash_merge_commit_title` |
| Squash merge commit message | `PR_BODY` | `squash_merge_commit_message` |
| Web commit signoff | `true` | `web_commit_signoff_required` |

The squash-merge settings ensure GIT-04's Conventional-Commits-on-the-merge
holds: the PR title becomes the merge commit, and the body is preserved.

**Check:**
```bash
gh api repos/{owner}/{repo} --jq \
  '{default_branch, allow_squash_merge, allow_merge_commit, allow_rebase_merge, delete_branch_on_merge}'
# Manual diff against the table above.
```

---

## RC-08: Tag and Release Protection (MUST)

- Tag pattern `v*.*.*` is protected (SemVer tags from the dev→main
  promotion).
- Only the promotion workflow's GitHub App identity may push these tags.
- Existing tags cannot be moved or deleted via the API (no force-push of
  tags).

**Check:**
```bash
gh api repos/{owner}/{repo}/tags/protection --jq '.[] | select(.pattern == "v*")' --silent \
  || echo "FAIL: v* tag protection missing"
```

---

## RC-09: Token Scopes (MUST)

The executor authenticates to GitHub via **either** a fine-grained PAT
**or** a GitHub App installation. Either way, the credential must hold
exactly these scopes; broader scopes are rejected.

### Required scopes (GitHub App permissions or fine-grained PAT)

| Scope | Level | Why |
|---|---|---|
| Contents | Read & write | Branch creation, commit, push, branch deletion |
| Pull requests | Read & write | PR creation (queue entry), PR update, PR labels |
| Merge queue | Read & write | Queue entry, queue status polling |
| Actions | Read & write | Workflow run trigger, status check polling, workflow rerun |
| Checks | Read & write | Status check creation by the executor itself (rare; for adaptive checks) |
| Metadata | Read | Repo metadata (default branch, settings) for arrival check |
| Environments | Read | Environment + secret existence checks (NOT secret values) |
| Workflows | Read & write | Workflow file updates (when sea:decompose adds a new check) |

### Forbidden scopes

- Administration (admin:repo, admin:org) — out of scope; manual setup
  only.
- Secrets (write) — secret rotation is a human task.
- Packages — out of scope for v1.
- Issues — the executor does not write issues.

**Check:**
```bash
gh api user --jq '.login' --silent  # establishes the auth identity works
# Scope verification happens at workflow-run time (GitHub returns insufficient_scope
# on the failing API call; the executor surfaces it as a BLOCKER).
```

---

## RC-10: CODEOWNERS (SHOULD)

The repo has a `.github/CODEOWNERS` file naming at least one owner for the
root path. This owner is the required reviewer for `production`
environment promotions (RC-05).

**Minimal CODEOWNERS:**
```
* @{repo-owner-github-handle}
```

**Check:**
```bash
test -f .github/CODEOWNERS || echo "WARN: CODEOWNERS missing (SHOULD); production promotions cannot route reviewers"
```

CODEOWNERS is SHOULD, not MUST. A repo without it can still operate, but
production promotion review will fall back to any user with write access.

---

## RC-11: Agent Arrival Check (MUST)

Before the executor (or any agent) touches a branch on a repo, it runs
the **arrival check**: a single bash script that verifies every MUST rule
above and emits a PASS/FAIL line per rule. The check is fast (≤30 s) and
read-only.

The arrival check lives at
`plugins/sulis-execution/scripts/wpx-arrival-check` and is invoked by the
executor as Step 0 (before Step 1 worktree creation).

**Contract:**

- Returns exit code 0 if all MUST rules pass.
- Returns exit code 2 if any MUST rule fails.
- Returns exit code 1 on a tooling error (no `gh` on PATH, no auth, etc.).
- Emits JSON to stdout shaped like:
  ```json
  {
    "ok": true|false,
    "errors": [
      {"rule": "RC-01", "check": "default branch is dev", "actual": "main", "expected": "dev"}
    ],
    "warnings": [
      {"rule": "RC-10", "check": "CODEOWNERS present", "actual": "missing", "expected": "present"}
    ]
  }
  ```

Non-zero exit blocks the executor. The orchestrator surfaces the JSON to
the concierge, which translates it to founder English per FE-08.

---

## RC-12: Strict-Mode Refusal Contract (MUST)

When the arrival check returns exit code 2 (any MUST rule failed), agents
refuse to operate on the repo and surface a refusal message.

### Refusal shape (executor → orchestrator → concierge → founder)

The executor returns a structured refusal. The concierge translates it to
founder English using FE-08 patterns.

**Internal (executor → orchestrator):**
```json
{
  "refused": true,
  "reason": "repository-contract-failed",
  "rules_failed": ["RC-01", "RC-02", "RC-04"],
  "delta": [
    {"rule": "RC-01", "expected": "default branch dev", "actual": "default branch main"},
    {"rule": "RC-02", "expected": "branch-ci required check on dev", "actual": "no protection on dev"},
    {"rule": "RC-04", "expected": "merge-queue-ci.yml present", "actual": "missing"}
  ]
}
```

**Founder-facing (concierge):**
> *"This repo isn't set up the way the marketplace expects yet. Three things
> need fixing before I can start building:*
>
> *1. The default branch is `main`, but I need it to be `dev`. (`main` becomes
> the production marker; `dev` is where work lands.)*
>
> *2. The `dev` branch has no protection rules, so I'd risk overwriting your
> teammates' work. I need it protected with the standard CI checks.*
>
> *3. The merge-queue workflow file is missing — that's the one that runs
> integration tests across batched changes.*
>
> *I can fix all three for you in about a minute. Want me to?"*

If the founder says yes, the concierge dispatches the **bootstrap
workflow** (RC-13). If the founder says no, the session ends and the
agent records the refusal in JOURNEY.md.

### What strict mode does NOT do

- It does not modify the repo without explicit founder authorisation.
- It does not partially conform (e.g., apply RC-01 + RC-02 but skip
  RC-04). Either the repo passes the full check or it doesn't.
- It does not retry — one arrival check per session start.
- It does not warn-and-proceed for MUST failures. Warnings (SHOULD
  failures) journal-record and proceed.

---

## RC-13: Reference Workflow Templates (MUST conform)

The reference workflow YAML files below are the canonical shape. Project-
specific commands (test runners, lint commands, deploy invocations) vary;
the structural shape does not.

### `.github/workflows/branch-ci.yml`
```yaml
name: branch-ci
on:
  pull_request:
    branches: [dev]
  push:
    branches: ['feat/wp-*']
concurrency:
  group: branch-ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  branch-ci:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: lint
        run: <project-specific lint command>
      - name: type-check
        run: <project-specific type-check command>
      - name: unit tests
        run: <project-specific unit test command>
      - name: smoke
        run: <project-specific smoke command (no network deps)>
```

### `.github/workflows/merge-queue-ci.yml`
```yaml
name: merge-queue-ci
on:
  merge_group:
jobs:
  merge-queue-ci:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - name: full unit tests
        run: <project-specific full unit test command>
      - name: integration tests
        run: <project-specific integration test command>
      - name: e2e tests
        run: <project-specific e2e test command>
```

### `.github/workflows/deploy-staging.yml`
```yaml
name: deploy-staging
on:
  push:
    branches: [dev]
concurrency:
  group: deploy-staging
  cancel-in-progress: false
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: deploy
        env:
          SULIS_DEPLOY_TOKEN: ${{ secrets.SULIS_DEPLOY_TOKEN_STAGING }}
        run: <project-specific Sulis SDK deploy command>
```

### `.github/workflows/health-and-smoke.yml`
```yaml
name: health-and-smoke
on:
  workflow_run:
    workflows: [deploy-staging]
    types: [completed]
jobs:
  health-and-smoke:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    environment: staging
    timeout-minutes: 20
    steps:
      - name: health poll
        run: |
          for i in {1..10}; do
            curl -sf "${{ secrets.HEALTH_URL_STAGING }}" && break
            sleep 30
          done
      - name: smoke
        run: ${{ vars.SMOKE_CMD }}
```

### `.github/workflows/promote-dev-to-main.yml`
```yaml
name: promote-dev-to-main
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'SemVer release tag (e.g. v1.2.3)'
        required: true
jobs:
  promote:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          ref: dev
          fetch-depth: 0
      - name: fast-forward main
        run: |
          git fetch origin main
          git checkout main
          git merge --ff-only origin/dev
          git tag -s "${{ inputs.version }}" -m "Release ${{ inputs.version }}"
          git push origin main --tags
```

### `.github/workflows/release-prod.yml`
```yaml
name: release-prod
on:
  push:
    branches: [main]
    tags: ['v*.*.*']
concurrency:
  group: release-prod
  cancel-in-progress: false
jobs:
  release-prod:
    runs-on: ubuntu-latest
    environment: production
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: deploy
        env:
          SULIS_DEPLOY_TOKEN: ${{ secrets.SULIS_DEPLOY_TOKEN_PROD }}
        run: <project-specific Sulis SDK production deploy command>
```

---

## Bootstrap Workflow

When the arrival check fails and the founder authorises remediation, the
concierge runs the bootstrap workflow via the Sulis SDK or a `gh` script.
The bootstrap is **all-or-nothing**: every MUST rule must apply
successfully or the script rolls back.

Bootstrap operations (in order):
1. Rename `master` → `main` if needed.
2. Create `dev` branch from `main` if missing.
3. Set `dev` as default branch.
4. Apply repository settings (RC-07).
5. Apply branch protections on `dev` and `main` (RC-02).
6. Enable merge queue on `dev` with RC-03 config.
7. Write the six reference workflow files (RC-13). Project-specific
   commands are filled in from `.sulis/repo-contract.yml` if present, else
   left as `# TODO project-specific` placeholders.
8. Create `staging` and `production` environments (RC-05).
9. Surface the unset secrets to the founder ("you need to paste your
   deploy tokens into these environment secrets").
10. Re-run the arrival check; bootstrap is complete when it returns exit 0.

The bootstrap script lives at
`plugins/sulis-execution/scripts/wpx-bootstrap-repo` (companion to
`wpx-arrival-check`).

---

## Out of Scope (v1)

The following are deliberately excluded from RC-01..RC-13 for v1. They
may be added in future revisions.

- **Multi-environment ladder beyond staging + production.** Some teams
  use dev → integration → staging → preprod → prod. RC v1 supports only
  staging + production. Teams needing additional environments are
  unsupported in v1.
- **Per-tenant or multi-region deploys.** Single-region single-tenant
  only.
- **Self-hosted GitHub Actions runners.** GitHub-hosted runners only in
  v1.
- **GitHub Enterprise Server (self-hosted GitHub).** github.com only in
  v1.
- **Source-control providers other than GitHub.** GitLab, Bitbucket,
  Gitea, Azure DevOps are unsupported.
- **Custom CODEOWNERS routing rules.** Single root-level owner only.
- **Required reviewers beyond CODEOWNERS.** Org-level review policies
  may interfere with the no-PR-ceremony model; out of scope.
- **Bypass actors on protected branches.** Strict enforcement only; no
  admin bypass list.
- **Custom merge queue settings.** RC-03 values are fixed in v1.
- **Branch-name patterns other than `feat/wp-*`.** No support for
  `fix/`, `chore/`, `refactor/` branches as separate patterns —
  Conventional Commits (GIT-04) handles those at the commit-message
  level, not the branch level.

When a repo needs any of the above, the strict-mode refusal kicks in.
That is the v1 contract.

---

## Composition with Other Standards

| Standard | Composition |
|---|---|
| **GIT-01..GIT-10** (`git-workflow-standard.md`) | RC-01..RC-08 operationalise GIT-01..GIT-10 on GitHub. RC defines the configuration; GIT defines the behaviour. |
| **EL-01..EL-08** (`executor-loop-standard.md`) | RC-11 is the new Step 0 in the executor lifecycle (arrival check). Steps 1-12 assume RC compliance. |
| **CP-01..CP-05** (`convention-preference-standard.md`) | RC-04 conforms to the merge-queue convention (CP-01 priority 2: dominant industry pattern — GitHub Merge Queue). RC-13 uses Conventional Commits + SemVer (CP-01 priority 1: IETF / industry standard). |
| **AAF-01..AAF-09** (`audience-adapted-framing-standard.md`) | RC-12's strict-mode refusal surfaces in founder English via the concierge. The internal JSON is for agents; the founder sees plain English per FE-08. |
| **FE-01..FE-11** (`founder-english.md`) | RC-12 refusal messages pass the FE-06 five-point check before the concierge surfaces them. |
| **`cicd-batching-analysis.md`** | RC-03 + RC-04 codify the merge-queue + per-batch deploy recommendation from that analysis. The analysis is the *why*; this standard is the *what*. |

---

## Version History

- **v0.1.0** (2026-05-19) — Initial release. RC-01..RC-13. Strict mode
  only. GitHub.com only. Reference workflow templates inline. Bootstrap
  workflow specified but not yet implemented (companion scripts
  `wpx-arrival-check` and `wpx-bootstrap-repo` are scheduled for the
  next sulis-execution release).
