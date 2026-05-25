# Repository Contract Standard (RC-01..RC-13)

<!-- summary -->
The marketplace-wide specification of what a GitHub repository must look
like before any Sulis agent operates on it. Defines the branching model
operationalised on GitHub (composes with GIT-01..GIT-10), the merge queue
configuration, the required Actions workflows, the environment ladder, the
secrets and tokens, the repository settings, the tag protection, and the
arrival-check protocol the executor runs before touching any branch.
**Repo profiles (v0.3.0):** a repo declares a `profile` (one of
`deployable-web-app`, `published-artifact`, `internal-tool`) — or, for a
monorepo that ships more than one release artifact, an `artifacts:` list —
plus an orthogonal `contribution_model` (`team`/`solo`). The profile drives
which deploy-shaped rules apply; the contribution model drives the merge
queue. Profiles are **additive specialisation** — they never weaken the
strict `deployable-web-app` contract. **Strict mode:** if the repo does not
conform to every MUST rule *for its profile*, agents refuse to operate and
surface a delta list. No support for repos that maintain their own process.
<!-- /summary -->

> **Version:** 0.3.0
> **Status:** Active — Calibration Period (90 days from 2026-05-19)
> **v0.3.0 amendment** (repo-profiles model, 2026-05-25): introduces the
> **repo profile model** — three single-artifact profiles
> (`deployable-web-app`, `published-artifact`, `internal-tool`) on the
> deployability axis (ADR-001), an orthogonal `contribution_model`
> (`team`/`solo`) governing the merge queue (ADR-002), first-class
> **multi-artifact composition** via an `artifacts:` list with **union**
> semantics (ADR-004), and the **RC-02 deadlock fix** — `merge-queue-ci`
> is the queue's internal `merge_group` gate, never a classic required
> status check (ADR-003). Profiles are additive: the `deployable-web-app`
> column is byte-for-byte the v0.2.0 strict contract. See the Repo Profiles
> section and the Rule Applicability Matrix below.
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

For profile-specific rules, an additional intermediate action is used by
the arrival check:

| Action | Meaning |
|---|---|
| **error** | The rule is a MUST for this profile; failure blocks the executor (exit 2). |
| **warn** | The rule degrades to advisory for this profile; failure journals a warning and proceeds. |
| **skip** | The rule is N/A for this profile; the check does not run. |

---

## Repo Profiles (v0.3.0)

> **Provenance.** RC v0.1.0–v0.2.0 assumed exactly one repo shape: a
> deployable web product with a URL, a staging server, and a production
> server. Four MUST rules (RC-04 deploy/health/release workflows, RC-05
> environments, RC-06 deploy secrets, RC-08 signed tags) — and the merge
> queue (RC-03) — assume a deploy target exists. A plugin marketplace, an
> npm/PyPI library, a CLI tool, or a single-maintainer repo has no URL to
> health-check, no staging server, no deploy token, and no concurrent merge
> pressure to serialise. The marketplace repo itself (`sulis-ai/agents`) hit
> this: it could not run its own executor pipeline (no deploy target) and the
> merge queue actively blocked a validated green PR (`AWAITING_CHECKS`). The
> profile model formalises the previously-hard-coded `deploy_target: none`
> hack into a principled, MECE taxonomy that **adds** non-deployable shapes
> without weakening the deployable one.

### The two orthogonal axes

A repo's RC obligations are driven by **two independent properties**, kept
as separate declared fields (ADR-001, ADR-002):

| Axis | Question | Field | Drives |
|---|---|---|---|
| **Deployability** | Does a release produce a running service at a URL, an installable versioned package, or nothing published? | `profile` (or `artifacts:`) | RC-04 deploy/health/release workflows, RC-05 environments, RC-06 deploy secrets, RC-08 signed tags |
| **Contribution volume** | One maintainer / low PR rate, or a multi-developer team merging concurrently? | `contribution_model` | RC-03 merge queue |

These are orthogonal: a deployable web app can be single-maintainer (a solo
founder's SaaS); a library can be high-volume (popular OSS, many
contributors). The profile names deployability only; volume rides a
separate field.

### The three single-artifact profiles (the partition)

The profile partition is MECE on a single discriminator — *"what does a
release artifact look like?"*:

| Profile | Release artifact | Deploy target | Health surface | Examples |
|---|---|---|---|---|
| **`deployable-web-app`** | A running service | A server/URL (staging + prod) | HTTP `/health` endpoint | SaaS API, web app, backend service |
| **`published-artifact`** | A versioned package consumers install | A registry (npm, PyPI, crates.io, a marketplace consumers point at) | Artifact validity (manifest parses, package imports, version is monotonic) | npm/PyPI library, CLI tool, Claude Code plugin marketplace |
| **`internal-tool`** | Source on `main` (no published artifact, no server) | None — the repo *is* the deliverable | Build + test green | Scripts repo, infra-as-code, docs site source, internal helpers |

- **Mutually exclusive** — a single release artifact is exactly one of: a
  running service, an installable versioned package, or nothing published.
- **Collectively exhaustive** — every repo the marketplace operates on
  produces one of the three; there is no fourth kind of release artifact.

`published-artifact` is **one** profile, not three (`marketplace` /
`library` / `cli`): those differ in *what* the package is, but are identical
with respect to every RC clause (none deploys to a server, all release by
publishing, all health-check by validating the artifact). Package-type
variation lives in the per-project command slots
(`.sulis/repo-contract.yml` `commands:`), not in the taxonomy. ADR-001
records this.

### The contribution-volume axis

`contribution_model` is a separate field governing **only** the merge queue
(RC-03):

| `contribution_model` | Merge queue (RC-03) | Merge mechanism | Rationale |
|---|---|---|---|
| **`team`** (default) | **MUST** — enabled, RC-03 config | PRs enter the queue; `merge_group` runs `merge-queue-ci` | Concurrent merges race; the queue serialises + speculatively batches (RC-03's value) |
| **`solo`** | **MUST NOT** — queue disabled | Direct squash-merge to `dev` on `branch-ci` green (the GIT-05 no-PR direct-merge path) | No concurrent merge pressure; the queue is ceremony and a live failure surface |

Disabling the queue on a low-volume repo is the dominant industry pattern
(GitHub positions merge queues for busy repos with frequent concurrent
merges) and is already the canonical GIT-05 solo flow — the boring,
conventional choice (CP-04). ADR-002 records the orthogonal-axis decision.

### Declaration in `.sulis/repo-contract.yml`

The repo declares both axes in its existing manifest (CP-01 priority-0:
build on internal prior art — `package.json`, `pyproject.toml`,
`Cargo.toml`, `.github/` all do this):

```yaml
# .sulis/repo-contract.yml — single-artifact
repo: sulis-ai/agents
owner: iainn

profile: published-artifact      # deployability axis — one of the three
contribution_model: solo         # volume axis — team | solo

commands:
  # marketplace-specific validate/publish commands live here, unchanged
```

- `profile` ∈ `{ deployable-web-app, published-artifact, internal-tool }`
  for a **single-artifact** repo.
- **OR** `artifacts:` — a list of N typed artifacts for a **multi-artifact**
  repo (see Multi-Artifact Composition below). `profile:` and `artifacts:`
  are **mutually exclusive**; the arrival check errors if both are present.
- `contribution_model` ∈ `{ team, solo }`. **Default when absent: `team`**
  (preserves v0.2.0 behaviour). **Repo-wide** — never per-artifact (one
  `dev`, one queue or none).
- `deploy_target` is retained as a back-compat alias (`none` ⟺ a
  non-deployable single profile) so existing checker code and external
  scripts keep reading; but `profile` / `artifacts` is authoritative.

### Rule Applicability Matrix (the heart of the contract)

Every RC rule is classified **profile-invariant** (same MUST for all
profiles) or **profile-specific** (varies). The profile columns ARE the
per-artifact types reused by multi-artifact composition.

Legend: **M** = MUST (error), **W** = WARN/advisory, **S** = SHOULD,
**N/A** = does not apply (skip), **—** = unchanged from invariant.

| Rule | Topic | Class | `deployable-web-app` | `published-artifact` | `internal-tool` | Notes |
|---|---|---|---|---|---|---|
| **RC-01** | dev/main branch model | **Invariant** | M | M | M | Branching is identical regardless of what ships. |
| **RC-02** | Branch protections | **Invariant** (with the deadlock fix) | M | M | M | Classic required checks = `branch-ci` only; `merge-queue-ci` is the queue's gate, never a classic check (ADR-003). |
| **RC-03** | Merge queue on `dev` | **Volume-specific** | M if `team`, MUST-NOT if `solo` | M if `team`, MUST-NOT if `solo` | M if `team`, MUST-NOT if `solo` | Driven by `contribution_model`, NOT by profile (ADR-002). |
| **RC-04** | Workflow files | **Split** | All six, M | `branch-ci` + (`merge-queue-ci` if `team`) M; deploy/health/release **repurposed** to validate/publish, M | `branch-ci` (+ queue if `team`) M; deploy/health/release **N/A** | See RC-04 per-workflow split. Multi-artifact: one shared `branch-ci`/`merge-queue-ci`/`promote`; per-artifact namespaced deploy/health/release/publish. |
| **RC-05** | Environments | **Profile-specific** | M (real deploy targets) | W (formality so `environment:` resolves; no deploy) | N/A (no environments) | The `deploy_target: none` hack, formalised. Multi-artifact: union, named per artifact. |
| **RC-06** | Deploy-token secrets | **Profile-specific** | M | N/A (no deploy → meaningless) | N/A | Multi-artifact: union, namespaced per deployable artifact. |
| **RC-07** | Repo settings (squash-only) | **Invariant** | M | M | M | Deploy-agnostic. Repo-wide in multi-artifact. |
| **RC-08** | Signed `v*` tags | **Profile-specific** | M (signed) | S (signed if a GPG key is in CI; else annotated + GitHub-verified) | S | Signing needs a provisioned key; degrade to SHOULD where none, never to silent. Multi-artifact: one shared tag, strongest-wins. |
| **RC-09** | Token scopes | **Invariant** | M | M | M | The executor needs the same GitHub capabilities regardless of profile. |
| **RC-10** | CODEOWNERS | **Invariant** | S | S | S | Already SHOULD; harmless and useful everywhere. |
| **RC-11** | Arrival check protocol | **Invariant** | M | M | M | The *protocol* is invariant; *which rules it enforces* is profile-driven. |
| **RC-12** | Strict-mode refusal | **Invariant** | M | M | M | Refusal fires on the *profile's* MUST set, not a universal one. |
| **RC-13** | Reference workflow YAML | **Split** | All six templates | Deploy/health/release templates' *command slots* run validate/publish | Deploy/health/release templates N/A | Structural shape stays; command slots vary (already true via `commands:`). |

**Seven profile-invariant** (RC-01, RC-02, RC-07, RC-09, RC-10, RC-11,
RC-12), **one volume-specific** (RC-03), **four profile-specific or split**
(RC-04, RC-05, RC-06, RC-08; RC-04 and RC-13 are "split" — part invariant,
part profile-specific). **The `deployable-web-app` column is identical to
the v0.2.0 contract in every row.**

### Non-Weakening Guarantee (`deployable-web-app` is byte-for-byte v0.2.0)

> Adopting profiles changes **nothing** for a deployable web product. Its
> full MUST set after v0.3.0 — RC-01 branch model, RC-02 protections (the
> only change being the deadlock fix, which makes the queue *work*, not
> weaker), RC-03 merge queue (it is a `team` deployable repo), RC-04 all six
> workflows including real deploy/health/release, RC-05 staging + production
> with real targets, RC-06 deploy-token secrets, RC-07 squash-only settings,
> RC-08 signed `v*` tags, RC-09 token scopes, RC-11/12 arrival check + strict
> refusal — is **MUST, unchanged**.

The relaxations (RC-05 → W, RC-06 → N/A, RC-08 → S, deploy workflows →
repurposed/absent, queue → off) apply **only** to the non-deployable / solo
profiles, **only** where the rule is physically meaningless or
negative-value, and **never** to `deployable-web-app`. This is the founder's
load-bearing constraint, satisfied by construction: profiles are additive
specialisation; they relax a MUST only where it carries no safety value for
that profile.

**And never to a `deployable-web-app` artifact inside a multi-artifact
repo** — see Multi-Artifact Composition: because the repo requirement is the
*union* (not the intersection), adding a library or internal-tool artifact
alongside a deployable one can only **add** requirements; it can never
subtract the deployable artifact's strict set.

### Multi-Artifact Composition (first-class in v0.3.0)

A repo is **exactly one of two shapes**: single-artifact (declares one
`profile:`) or multi-artifact (declares an `artifacts:` list). A monorepo
that ships **both** a deployable service **and** a published library needs
**both validated as first-class**, each with its own correct MUST set.
v0.3.0 supports this directly (ADR-004) — it is no longer
declare-dominant-or-split.

**Declaration** — an `artifacts:` list, each entry a `name` (used to
namespace its workflows) + a `type` (one of the three profiles) +
per-artifact config:

```yaml
# .sulis/repo-contract.yml — multi-artifact
repo: acme/widget
owner: acme
contribution_model: team          # volume axis is repo-wide, NOT per-artifact

artifacts:
  - name: api
    type: deployable-web-app       # gets the FULL strict deploy/health/secrets/signed-tag set
    environments:
      staging:    { deploy_token_secret: SULIS_DEPLOY_TOKEN_API_STAGING, health_url_secret: HEALTH_URL_API_STAGING }
      production: { deploy_token_secret: SULIS_DEPLOY_TOKEN_API_PROD,    health_url_secret: HEALTH_URL_API_PROD }
    commands:
      deploy_staging: <sulis sdk deploy --env staging>
      deploy_prod:    <sulis sdk deploy --env production>

  - name: sdk
    type: published-artifact       # publish-validate; no server, no health poll
    registry: npm
    commands:
      publish_validate: npm pack --dry-run && npm publish --dry-run
      publish:          npm publish
```

The three profiles are reused as the **per-artifact types**. Multi-artifact
is a **composition layer over** the partition, not a fourth profile — the
partition stays MECE *per artifact*, and the repo is the union of its
artifacts. This is the dominant monorepo convention (Nx/Turborepo/Bazel
targets, Cargo workspace members, npm workspaces — a list of typed build
targets, CP-01 priority 2). ADR-004 records it.

**The composition rule (stated once):** *for each contract rule, the repo's
requirement is the **union** of the per-artifact requirements — a rule
applies, at the strongest severity any artifact demands, if **any** artifact
requires it; a per-artifact resource (a deploy workflow, an environment, a
deploy secret) is required iff that specific artifact's type requires it.*

**Union, not intersection** — because intersection would let a lax artifact
(the library, which needs no deploy) **cancel** the strict artifact's deploy
MUSTs, exactly the weakening the founder forbids. Union can only **add**
requirements; it can never subtract the deployable artifact's strict set.

#### RC-04 workflow files — repo-wide shared + per-artifact namespaced

| Workflow | Single-artifact | Multi-artifact |
|---|---|---|
| `branch-ci.yml` | one | **one, repo-wide, shared** — runs the union of all artifacts' lint/test/smoke |
| `merge-queue-ci.yml` | one (if `team`) | **one, repo-wide, shared** (if `team`) — integration across all artifacts on the merge_group ref |
| deploy-staging | `deploy-staging.yml` | **`deploy-<name>-staging.yml` per deployable-web-app artifact** |
| health-and-smoke | `health-and-smoke.yml` | **`health-<name>-staging.yml` per deployable-web-app artifact** |
| release-prod | `release-prod.yml` | **`release-<name>-prod.yml` per deployable artifact**; **`publish-<name>.yml` per published artifact** |
| promote-dev-to-main | `promote-dev-to-main.yml` | **one, repo-wide** — one promotion ceremony tags the whole repo |

`branch-ci` and `merge-queue-ci` stay **exactly one each, repo-wide** — the
queue gates the whole repo's integration, not per artifact. This keeps RC-03
and the RC-02 deadlock fix byte-for-byte identical to single-artifact. Each
deployable artifact gets its own deploy ladder; each published artifact gets
its own publish workflow; internal-tool artifacts contribute no
deploy/health/release/publish workflow. One promotion ceremony (one `dev`,
one `main` — the RC-01 invariant) cuts one tag that each per-artifact
release/publish workflow then acts on.

#### RC-05 / RC-06 / RC-08 — union composition

| Rule | Composition |
|---|---|
| **RC-05** environments | Union, named per artifact (`api-staging`, `api-production`). Each `deployable-web-app` artifact → its own staging+production with real targets (MUST). `published-artifact` → optional formality env (WARN). `internal-tool` → none. |
| **RC-06** deploy secrets | Union, namespaced (`SULIS_DEPLOY_TOKEN_<NAME>_STAGING`, `HEALTH_URL_<NAME>_*`). Required iff that artifact is deployable. If **any** artifact is deployable, its deploy secrets are MUST. |
| **RC-08** signed tags | **Strongest-wins** — one shared SemVer tag. If **any** artifact is `deployable-web-app`, the tag MUST be signed. All-published/internal → signing degrades to SHOULD. |

#### Worked example — the founder's repo (`api` deployable + `sdk` published, `team`)

| Rule | `api` | `sdk` | Repo (union) |
|---|---|---|---|
| RC-04 `branch-ci`, `merge-queue-ci` | M | M | M (one shared each) |
| RC-04 `deploy-api-staging.yml`, `health-api-*`, `release-api-prod.yml` | M | n/a | M (api only) |
| RC-04 `publish-sdk.yml` | n/a | M | M (sdk only) |
| RC-04 `promote-dev-to-main.yml` | M | M | M (one shared) |
| RC-05 `api-staging` / `api-production` (real targets) | M | n/a | M (api only) |
| RC-05 `sdk` formality env | n/a | W | W (sdk only) |
| RC-06 `SULIS_DEPLOY_TOKEN_API_*` / `HEALTH_URL_API_*` | M | n/a | M (api only) |
| RC-08 signed `v*` tag | M (signed) | W | **M** (strongest wins) |
| RC-01/02/03/07/09/10/11/12 (invariant) | M | M | M (repo-wide) |

The `api` artifact carries the **full strict deployable contract** — the
non-compromise guarantee holds inside the monorepo. The `sdk` artifact adds
its publish-validate requirement on top. Nothing the `sdk` declares can
subtract from `api`'s strict set (union, not intersection).

#### Honest limitation — fixed versioning only

v0.3.0 uses **one repo version, one SemVer tag, many published outputs**
(the Lerna/Changesets fixed-versioning default — the boring, older
convention, CP-04). A repo that needs **independently-versioned** artifacts
(`api-v1.2.0` and `sdk-v3.0.0` cut on separate cadences) is **not** supported
in v0.3.0 — that needs per-artifact tag protection + per-artifact promotion,
which would break the RC-01 "one `dev`, one `main`, one promotion ceremony"
invariant. Independent versioning is a future revision if a real repo needs
it; flagged here as the one genuine limitation of the multi-artifact model
(ADR-004).

### Companion tooling (the arrival check + bootstrap read the profile)

RC-11's arrival check (`wpx-arrival-check`) and the bootstrap script
(`wpx-bootstrap-repo`) read `profile` / `artifacts` + `contribution_model`
and apply this matrix: the scattered `deploy_target == "none"` special-cases
are replaced by a single profile-applicability lookup, plus a union step for
multi-artifact repos. Those tooling updates are companion work landing
alongside this standard; the standard text below is authoritative for what
they must enforce.

### Backward Compatibility & Migration

**A repo conformant to RC v0.2.0 stays conformant after v0.3.0, with no
config change.** The mechanism is defaults:

- **No `profile:` field** → inferred from `deploy_target` for the
  back-compat bridge: `deploy_target: none` (or any non-deployable signal) →
  `published-artifact`; `deploy_target` absent or a real target →
  **`deployable-web-app`**.
- **No `contribution_model:` field** → **`team`**.
- **Multi-artifact is opt-in** — a repo becomes multi-artifact only by
  explicitly declaring `artifacts:`. No existing repo gains an `artifacts:`
  list by default.

A v0.2.0 deployable repo has no `profile:` and no `deploy_target: none`, so
it defaults to `deployable-web-app` + `team` = **the full strict v0.2.0
contract, unchanged**. Nothing breaks.

**The RC-02 deadlock fix is a strict improvement, not a relaxation.** It
removes `merge-queue-ci` from classic required checks for every
queue-enabled repo (including existing `deployable-web-app` `team` repos),
making any silently-deadlock-prone repo correctly deadlock-free. No safety
property weakens; the queue still gates every merge. Existing `team` repos
should re-run bootstrap (or apply the one-line protection change) to pick it
up — safe and mechanical.

**No silent profile changes.** A profile is declared, never
inferred-and-applied silently beyond the v0.2.0 back-compat bridge. If a repo
has no `profile:` and an ambiguous `deploy_target`, the arrival check emits a
**warning** naming the inferred profile and recommending the owner declare it
explicitly — so a repo never slides from strict to relaxed enforcement
unnoticed.

**Marketplace repo migration** (`sulis-ai/agents`):
`profile: plugin-marketplace` → `profile: published-artifact`; add
`contribution_model: solo`; the `deviations:` block (RC-05/06/08) is no longer
needed — those become the **defined behaviour** of `published-artifact` +
`solo`; `commands:` unchanged. After this the arrival check passes on the
profile's MUST set with the queue disabled, and the live `AWAITING_CHECKS`
block is gone (no queue; direct merge on `branch-ci` green).

---

## RC-01: Branching Model (MUST)

**Applies to all profiles** (profile-invariant). Branching is identical
regardless of what the repo ships or how many artifacts it has — one `dev`,
one `main`, one promotion ceremony.

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

**Applies to all profiles** (profile-invariant). Protections carry the same
safety value regardless of what ships. The one v0.3.0 change is the
**deadlock fix** below, which makes the queue *work*, not weaker — it applies
to every queue-enabled repo, including `deployable-web-app` (ADR-003).

> **The deadlock fix (ADR-003, load-bearing).** `dev`'s classic
> branch-protection required status checks are **`branch-ci` only**.
> `merge-queue-ci` is the merge queue's own internal gate — it runs on the
> `merge_group` event for the synthetic merged ref GitHub creates *inside*
> the queue, and **MUST NOT** appear in
> `required_status_checks.contexts`. Listing it as a classic required check
> deadlocks: a classic check must be green *before* a PR can enter the queue,
> but `merge-queue-ci` cannot run *until* the PR is in the queue → the PR
> waits forever on `AWAITING_CHECKS`. The fix removes it from classic checks
> while losing no safety — `merge-queue-ci` still gates every merge to `dev`
> as the queue's gate, where it can actually run. This shipped live to
> `sulis-ai/agents` via PR #2 (verified 2026-05-25).

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

- **Required status checks (classic):**
  - `branch-ci` — the per-PR lint + unit + smoke job (RC-04). **This is the
    only classic required status check on `dev`.**
  - `merge-queue-ci` is **NOT** a classic required status check. It runs as
    the merge queue's internal `merge_group` gate (ADR-003 deadlock fix).
    On a `solo` repo there is no queue and `merge-queue-ci.yml` may be
    absent entirely.
- **Require branches to be up to date before merging:** YES (under `team`,
  via the merge queue, which handles rebasing internally).
- **Require merge queue:** YES **if `contribution_model: team`** (see RC-03);
  **NOT set if `solo`** (no queue; direct squash-merge on `branch-ci` green
  per GIT-05).
- **Require pull request before merging:** YES **if `team`** (technical
  mechanism — the merge queue requires PRs to function; this is NOT
  human-review ceremony, it is the queue's entry interface). **`solo`** uses
  the GIT-05 no-PR direct-merge path.
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
# merge-queue-ci MUST NOT be a classic required check (ADR-003 deadlock fix):
gh api repos/{owner}/{repo}/branches/dev/protection \
  --jq '.required_status_checks.contexts' | grep -q merge-queue-ci \
  && echo "FAIL: merge-queue-ci must NOT be a classic required check (it is the queue's merge_group gate)"
```

---

## RC-03: Merge Queue Configuration on `dev` (volume-specific)

**Keyed on `contribution_model`, NOT on profile** (ADR-002):

| `contribution_model` | RC-03 |
|---|---|
| **`team`** (default) | **MUST** — the merge queue is enabled on `dev` with the config below. |
| **`solo`** | **MUST NOT** — the queue is **absent**. Merges go direct to `dev` via squash on `branch-ci` green (the GIT-05 no-PR direct-merge path). `merge-queue-ci.yml` and `require_merge_queue` are not present. |

The merge queue's value — amortising CI cost and serialising merges under
concurrent merge pressure (the Shopify/debugg.ai speculative-batch patterns)
— is a function of contribution volume, not of what the repo ships. At one
maintainer with a low PR rate there is no race to serialise; the queue is
ceremony and, as observed live on `sulis-ai/agents`, a failure surface (it
blocked a validated green PR on `AWAITING_CHECKS`). Disabling it for `solo`
is the dominant industry pattern and the canonical GIT-05 solo flow (CP-04).

**The remainder of RC-03 applies only when `contribution_model: team`.** The
`dev` branch then has GitHub Merge Queue enabled with the following config:

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

**Check (when `contribution_model: team`):**
```bash
gh api graphql -f query='{
  repository(owner: "{owner}", name: "{repo}") {
    mergeQueue { mergingStrategy maxEntriesToMerge mergeMethod }
  }
}' --jq '.data.repository.mergeQueue' || echo "FAIL: merge queue not configured on dev (team repo)"
```

**Check (when `contribution_model: solo`):** verify the queue is **absent** —
`require_merge_queue` is not set on `dev` protection and no `merge_group`
workflow is required. A present queue on a `solo` repo is a FAIL.

---

## RC-04: Required Workflows (split — part invariant, part profile-specific)

**Applicability by profile.** `branch-ci` (and `merge-queue-ci` when
`team`) are MUST for all profiles. The deploy/health/release workflows are
profile-specific — see the per-workflow split below. The base contract
(single-artifact `deployable-web-app`, `team`) is the six workflows below,
unchanged from v0.2.0.

The repo contains exactly these GitHub Actions workflows at the listed
paths, with the listed event triggers. The workflow file *names* are
fixed (the executor reads them by name in the arrival check); the
*contents* are project-specific but must conform to the contract.

| Workflow path | Trigger events | Purpose |
|---|---|---|
| `.github/workflows/branch-ci.yml` | `pull_request` (any branch → `dev`), `push` (on `feat/wp-*` and `change/*`) | Per-WP fast checks: lint + type-check + unit tests + smoke. ≤15 min target. Required check for queue entry. Per CW-04, `feat/wp-*` branches live INSIDE a `change/*` branch worktree; the `push` trigger fires on both layers so per-WP CI runs whether the WP is being shipped per-change or directly to `dev` via the trivial-change carve-out. |
| `.github/workflows/merge-queue-ci.yml` | `merge_group` | Speculative-merge integration test. Runs full integration + e2e suite on the synthetic merged ref. **Present only when `contribution_model: team`.** It is the merge queue's **internal `merge_group` gate** for merging the batch — NOT a classic required status check on `dev` (RC-02 deadlock fix, ADR-003). It still gates every merge to `dev`, as the queue's gate. **Merge-queue source = `change/*` branches** (per CW-04 — the change branch is the integration point that reaches the queue; individual `feat/wp-*` branches DO NOT enter the queue directly, they merge into their parent change branch first via wpx-train). The trivial-change carve-out (CW-05) is the only case where `feat/*` may target `dev` directly; even then the per-change merge model is preferred. |
| `.github/workflows/deploy-staging.yml` | `push` on `dev` | Deploys the merged batch to the `staging` environment. Triggers health-check + smoke downstream. |
| `.github/workflows/health-and-smoke.yml` | `workflow_run` (after `deploy-staging` success) | Polls `/health` until ready; runs smoke test command. Reports status check `staging-health`. |
| `.github/workflows/promote-dev-to-main.yml` | `workflow_dispatch` (manual) | The dev→main promotion ceremony per GIT-06. Cuts a release tag (SemVer) and pushes to `main`. |
| `.github/workflows/release-prod.yml` | `push` on `main` | Deploys `main` to `production` environment. May require manual approval per RC-05. |

**Workflow event details:**

- `branch-ci` must fire on `pull_request` events whose `base_ref` is `dev`
  AND on `push` events to `feat/wp-*` AND `change/*` branches. The first
  gives PR-level signal; the second lets the executor short-circuit before
  opening a PR; the `change/*` trigger gives the change branch CI signal
  before the change merges to `dev` (per CW-04).
- `merge-queue-ci` must fire ONLY on `merge_group` (not `pull_request` or
  `push`). It runs against the speculative merge ref GitHub creates inside
  the queue. **The merge group's source MUST be `change/*` branches**
  (PRs from change branches → `dev`); `feat/wp-*` branches do not enter
  the queue directly per CW-04. The only exception is the trivial-change
  carve-out (CW-05) where a `feat/*` may merge directly without a parent
  change branch.
- `deploy-staging` must NOT fire on `pull_request` — only on `push` to
  `dev` (i.e., after the queue has merged a batch).
- `release-prod` must NOT fire on `push` to `dev` — only on `push` to
  `main`.

**Check (single-artifact `deployable-web-app`, `team` — the base contract):**
```bash
for wf in branch-ci merge-queue-ci deploy-staging health-and-smoke promote-dev-to-main release-prod; do
  test -f ".github/workflows/${wf}.yml" || echo "FAIL: ${wf}.yml missing"
done
```

(The executor's arrival check parses each workflow's `on:` block to
verify the trigger events. Reference YAML in RC-13. The set of required
workflows narrows per the per-workflow split below.)

### RC-04 per-workflow split (single-artifact)

| Workflow | `deployable-web-app` | `published-artifact` | `internal-tool` |
|---|---|---|---|
| `branch-ci.yml` | M | M | M |
| `merge-queue-ci.yml` | M if `team` | M if `team` | M if `team` |
| `deploy-staging.yml` | M (deploys to staging) | **Repurposed** M — the command slot validates the installable artifact (e.g. marketplace manifest validation); still triggered on push to `dev` | **N/A** — file absent |
| `health-and-smoke.yml` | M (polls `/health`) | **Repurposed** M — the command slot runs artifact integration checks (manifests parse, plugins load); no URL poll | **N/A** — file absent |
| `promote-dev-to-main.yml` | M | M (cuts the SemVer release tag) | M (tags the source release) |
| `release-prod.yml` | M (deploys to prod) | **Repurposed** M — the command slot publishes the GitHub Release / pushes to the registry from the tag | **N/A** — file absent |

`published-artifact` keeps all six workflows **structurally** (right names,
right triggers — the executor reads them by name) but the command slots in
three of them do validate/publish work instead of deploy. This is exactly
what `.sulis/repo-contract.yml` `commands:` already encodes; v0.3.0
formalises it as the profile's defined shape rather than a per-repo
deviation. `internal-tool` legitimately omits the three deploy workflows;
the arrival check does not require their presence for that profile.

### RC-04 multi-artifact (per-artifact namespaced workflows)

For a multi-artifact repo (ADR-004), `branch-ci` and `merge-queue-ci` stay
**exactly one each, repo-wide and shared** (running the union of all
artifacts' checks), and `promote-dev-to-main` stays **one, repo-wide** (one
promotion ceremony tags the whole repo). The deploy/health/release/publish
workflows are **namespaced per artifact**:

| Workflow | Multi-artifact form |
|---|---|
| `branch-ci.yml` | one, repo-wide, shared |
| `merge-queue-ci.yml` | one, repo-wide, shared (if `team`) |
| deploy-staging | `deploy-<name>-staging.yml` per `deployable-web-app` artifact |
| health-and-smoke | `health-<name>-staging.yml` per `deployable-web-app` artifact |
| release-prod | `release-<name>-prod.yml` per deployable artifact |
| publish | `publish-<name>.yml` per `published-artifact` artifact |
| promote-dev-to-main | one, repo-wide |

The per-artifact workflows fire off the single repo-wide promotion (one
SemVer tag, many published outputs — fixed versioning, CP-04). Keeping
`branch-ci`/`merge-queue-ci` repo-wide makes RC-03 and the ADR-003 RC-02 fix
byte-for-byte identical to single-artifact. The arrival check verifies each
artifact's namespaced files exist iff its type requires them
(`deploy-api-staging.yml` MUST exist because `api` is deployable;
`publish-sdk.yml` MUST exist because `sdk` is published; no `deploy-sdk-*.yml`
is required).

---

## RC-05: Environments (profile-specific)

**Applicability by profile:**

| Profile | RC-05 |
|---|---|
| **`deployable-web-app`** | **MUST** — `staging` + `production` with real deploy targets, exactly as below. |
| **`published-artifact`** | **WARN** — environments exist as a formality so a workflow's `environment:` clause resolves; they carry no real deploy target and no deploy secrets. A missing formality env journals a warning, not a refusal. |
| **`internal-tool`** | **N/A** — no environments. |

**Multi-artifact:** union, named per artifact. Each `deployable-web-app`
artifact contributes `<name>-staging` + `<name>-production` with real
targets (MUST). A `published-artifact` artifact contributes an optional
formality env (WARN). The repo requirement is the union of all artifacts'
environments.

The strict-profile (`deployable-web-app`) contract below is **unchanged from
v0.2.0**. The repo has exactly two GitHub environments:

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

**Check (`deployable-web-app`):**
```bash
gh api repos/{owner}/{repo}/environments --jq '.environments[].name' | sort > /tmp/envs.txt
diff <(echo -e "production\nstaging") /tmp/envs.txt || echo "FAIL: environments must be exactly {staging, production}"
```
For `published-artifact` the absence of environments is a WARN; for
`internal-tool` the check is skipped. For multi-artifact, the check verifies
each deployable artifact's `<name>-staging`/`<name>-production` envs exist.

---

## RC-06: Required Secrets and Variables (profile-specific)

**Applicability by profile:**

| Profile | RC-06 |
|---|---|
| **`deployable-web-app`** | **MUST** — the deploy-token + health-URL secrets below. |
| **`published-artifact`** | **N/A** — no deploy → deploy tokens are meaningless. (Publish credentials, if any, live in the registry's own auth, not in these RC-06 deploy secrets.) |
| **`internal-tool`** | **N/A**. |

**Multi-artifact:** union, namespaced. Each deployable artifact requires its
own `SULIS_DEPLOY_TOKEN_<NAME>_STAGING` / `_PROD` and `HEALTH_URL_<NAME>_*`
(named in the artifact's `environments:` block). If **any** artifact is
`deployable-web-app`, its deploy secrets are MUST. Published/internal
artifacts require none.

The strict-profile contract below is **unchanged from v0.2.0**.

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

**Check (`deployable-web-app` only; skipped for `published-artifact` /
`internal-tool`; namespaced per deployable artifact for multi-artifact):**
```bash
gh secret list --env staging --json name --jq '.[].name' | grep -qx SULIS_DEPLOY_TOKEN_STAGING || echo "FAIL: SULIS_DEPLOY_TOKEN_STAGING missing on staging env"
gh secret list --env staging --json name --jq '.[].name' | grep -qx HEALTH_URL_STAGING || echo "FAIL: HEALTH_URL_STAGING missing on staging env"
gh secret list --env production --json name --jq '.[].name' | grep -qx SULIS_DEPLOY_TOKEN_PROD || echo "FAIL: SULIS_DEPLOY_TOKEN_PROD missing on production env"
gh variable list --json name --jq '.[].name' | grep -qx SMOKE_CMD || echo "FAIL: SMOKE_CMD variable missing"
```

---

## RC-07: Repository Settings (MUST)

**Applies to all profiles** (profile-invariant). Squash-only, linear
history, and delete-on-merge are deploy-agnostic; repo-wide in multi-artifact.

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

## RC-08: Tag and Release Protection (profile-specific)

**Applicability by profile:**

| Profile | RC-08 signing |
|---|---|
| **`deployable-web-app`** | **MUST** — signed `v*` tags. |
| **`published-artifact`** | **SHOULD** — signed if a GPG key is provisioned in CI; else annotated tags + GitHub-verified bot commits. Signing requires a provisioned key; degrade to SHOULD where none exists, never to silent. |
| **`internal-tool`** | **SHOULD** (same rationale). |

Tag *protection* (the pattern is protected; only the promotion identity may
push; no force-push of tags) applies to **all** profiles — it is the signing
requirement that varies.

**Multi-artifact:** **strongest-wins** over one shared SemVer tag (one
promotion ceremony, RC-01 invariant). If **any** artifact is
`deployable-web-app`, the tag MUST be signed. All-published/internal →
signing degrades to SHOULD.

The strict-profile contract below is **unchanged from v0.2.0**.

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

**Applies to all profiles** (profile-invariant). The executor needs the same
GitHub capabilities regardless of what the repo ships.

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

**Applies to all profiles** (profile-invariant, already SHOULD). The
production-promotion reviewer routing only matters where a prod env exists,
but the file itself is harmless and useful everywhere.

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

**Applies to all profiles** (profile-invariant *protocol*). The protocol is
invariant — read-only, ≤30 s, emits the JSON contract below, exits 0/1/2.
What varies is **which rules it enforces as MUST**: the check reads
`profile` / `artifacts` + `contribution_model` from
`.sulis/repo-contract.yml` and consults the Rule Applicability Matrix to
decide, per rule, whether to enforce as `error` (MUST), emit as `warn`
(advisory), or `skip` (N/A). For a multi-artifact repo it computes the
**union** across artifacts — a rule is enforced at the strongest severity any
single artifact requires, and a per-artifact resource is verified iff that
artifact's type requires it (ADR-004). This replaces the previous hard-coded
`deploy_target == "none"` special-cases with one principled lookup. The
companion tooling update (`wpx-arrival-check`) implements this; the matrix in
the Repo Profiles section above is authoritative for what it enforces.

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

**Applies to all profiles** (profile-invariant). Refusal still fires — but on
the *profile's* MUST set (or, for multi-artifact, the union MUST set), not a
universal one. A `published-artifact` repo is never refused for a missing
deploy token (that rule is N/A for it); a `deployable-web-app` repo still is.

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

## RC-13: Reference Workflow Templates (split — MUST conform where required)

The reference workflow YAML files below are the canonical shape. Project-
specific commands (test runners, lint commands, deploy invocations) vary;
the structural shape does not.

**Applicability by profile** (mirrors the RC-04 split):

- **`deployable-web-app`** — all six templates apply, with real deploy
  command slots.
- **`published-artifact`** — `branch-ci`, `merge-queue-ci`, and
  `promote-dev-to-main` apply unchanged; the `deploy-staging`,
  `health-and-smoke`, and `release-prod` templates apply *structurally* but
  their command slots run validate/publish work (e.g.
  `deploy-staging` → validate the installable artifact;
  `health-and-smoke` → manifests parse / package imports;
  `release-prod` → publish the GitHub Release / push to the registry).
- **`internal-tool`** — the three deploy templates do not apply (files
  absent); the rest apply unchanged.

**Multi-artifact naming.** `branch-ci.yml`, `merge-queue-ci.yml`, and
`promote-dev-to-main.yml` remain single, repo-wide files (shared). The
deploy/health/release/publish templates are instantiated **per artifact**
with the artifact name in the file name and the matching namespaced
secrets/environment:

- `deploy-<name>-staging.yml` (per `deployable-web-app` artifact) — uses
  `secrets.SULIS_DEPLOY_TOKEN_<NAME>_STAGING`, `environment: <name>-staging`.
- `health-<name>-staging.yml` (per `deployable-web-app` artifact) — polls
  `secrets.HEALTH_URL_<NAME>_STAGING`, triggered on `deploy-<name>-staging`.
- `release-<name>-prod.yml` (per deployable artifact) — uses
  `secrets.SULIS_DEPLOY_TOKEN_<NAME>_PROD`, `environment: <name>-production`.
- `publish-<name>.yml` (per `published-artifact` artifact) — runs the
  artifact's publish command on the shared promotion's tag.

The templates below are the single-artifact canonical shape; multi-artifact
copies each deploy-shaped template per artifact with the substitutions above.

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
The bootstrap reads `profile` / `artifacts` + `contribution_model` and is
**all-or-nothing within the profile's (or union) MUST set**: every MUST rule
that applies to the declared profile must apply successfully or the script
rolls back. The companion tooling update (`wpx-bootstrap-repo`) implements
the conditional steps below.

Bootstrap operations (in order):
1. Rename `master` → `main` if needed. *(all profiles)*
2. Create `dev` branch from `main` if missing. *(all profiles)*
3. Set `dev` as default branch. *(all profiles)*
4. Apply repository settings (RC-07). *(all profiles)*
5. Apply branch protections on `dev` and `main` (RC-02). **`dev` classic
   required status checks = `["branch-ci"]` only** (the ADR-003 deadlock
   fix); set `require_merge_queue` only when `contribution_model: team`.
   *(all profiles)*
6. Enable merge queue on `dev` with RC-03 config **only if
   `contribution_model: team`**. For `solo`, skip this step entirely and
   leave `dev` protection with `branch-ci` as the only required check and no
   `require_merge_queue` (the GIT-05 direct-merge flow).
7. Write the reference workflow files (RC-13). Project-specific commands are
   filled in from `.sulis/repo-contract.yml` if present, else left as
   `# TODO project-specific` placeholders.
   - **`deployable-web-app`** — all six, with deploy command slots.
   - **`published-artifact`** — all six; the three deploy-shaped files get
     validate/publish command slots.
   - **`internal-tool`** — write `branch-ci`, `merge-queue-ci` (if `team`),
     and `promote-dev-to-main` only; omit the three deploy workflows.
   - **Multi-artifact** — write one shared `branch-ci` / `merge-queue-ci` /
     `promote-dev-to-main`, then iterate `artifacts:`: a deploy ladder
     (`deploy-<name>-staging.yml`, `health-<name>-*.yml`,
     `release-<name>-prod.yml`) per `deployable-web-app` artifact and a
     `publish-<name>.yml` per `published-artifact` artifact.
8. Create environments (RC-05) **for deployable artifacts only**:
   `staging` + `production` for a single-artifact `deployable-web-app`;
   namespaced `<name>-staging` / `<name>-production` per deployable artifact
   for multi-artifact; create formality envs (WARN) for `published-artifact`;
   skip for `internal-tool`.
9. Surface the unset deploy secrets to the founder, **per deployable
   artifact, namespaced** ("you need to paste your deploy tokens into these
   environment secrets"). Skip for non-deployable profiles.
10. Apply tag protection (RC-08) for all profiles; configure signing for
    `deployable-web-app` (and for any multi-artifact repo containing a
    deployable artifact — strongest-wins).
11. Re-run the arrival check; bootstrap is complete when it returns exit 0.

The bootstrap script lives at
`plugins/sulis-execution/scripts/wpx-bootstrap-repo` (companion to
`wpx-arrival-check`).

---

## Now In Scope (v0.3.0 — formerly refused)

The profile model brings three repo shapes that v0.1.0/v0.2.0 refused into
first-class support:

- **Non-deployable repos** — `published-artifact` (npm/PyPI library, CLI
  tool, plugin marketplace) and `internal-tool` (scripts, infra-as-code,
  docs source) no longer refuse for missing deploy targets. The deploy-shaped
  rules (RC-04 deploy workflows, RC-05, RC-06, RC-08 signing) are
  profile-conditional.
- **Single-maintainer repos** — `contribution_model: solo` disables the
  merge queue and uses the GIT-05 direct-merge-to-`dev` flow instead of
  refusing.
- **Monorepos shipping more than one release artifact** — the `artifacts:`
  list with union composition (ADR-004), with one deploy ladder per
  deployable artifact and one publish workflow per published artifact.

## Out of Scope

The following are deliberately excluded from RC-01..RC-13. They may be added
in future revisions.

- **Independent per-artifact versioning.** v0.3.0 multi-artifact uses
  **fixed versioning** — one repo version, one SemVer tag, many published
  outputs (the Lerna/Changesets default, CP-04). A repo needing
  independently-cut artifact versions (`api-v1.2.0` and `sdk-v3.0.0` on
  separate cadences) is unsupported — it would need per-artifact tag
  protection + per-artifact promotion, breaking the RC-01 "one `dev`, one
  `main`, one promotion ceremony" invariant. This is the one genuine
  limitation of the multi-artifact model (ADR-004).
- **Per-artifact `branch-ci` path scoping.** v0.3.0 runs one repo-wide
  `branch-ci` executing the union of all artifacts' checks. Path-filtered
  per-artifact CI (run `sdk` tests only when `sdk/` changed) is a
  CI-optimisation, not a contract requirement; deferred.
- **Multi-environment ladder beyond staging + production.** Some teams
  use dev → integration → staging → preprod → prod. RC supports only
  staging + production per deployable artifact. Teams needing additional
  environments are unsupported.
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

When a repo needs any of the above out-of-scope items, the strict-mode
refusal kicks in. That is the v0.3.0 contract.

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
| **ADR-001..004** (`.architecture/repo-profiles/adrs/`) | The repo-profile model's decision records: ADR-001 profile taxonomy (three profiles, MECE on the release-artifact discriminator); ADR-002 merge queue governed by the orthogonal `contribution_model`; ADR-003 the RC-02 `merge-queue-ci` deadlock fix; ADR-004 multi-artifact composition (union semantics). |

---

## Version History

- **v0.3.0** (2026-05-25) — **Repo profiles model.** Introduces the two
  orthogonal axes — a `profile` (deployability) and a `contribution_model`
  (volume) — plus first-class multi-artifact composition. Summary of changes:
  - **Profile taxonomy (ADR-001):** three single-artifact profiles
    (`deployable-web-app`, `published-artifact`, `internal-tool`), MECE on
    the discriminator *"what does a release artifact look like?"*. Adds a
    Repo Profiles section + the Rule Applicability Matrix classifying every
    RC rule as profile-invariant (RC-01, RC-02, RC-07, RC-09, RC-10, RC-11,
    RC-12), volume-specific (RC-03), or profile-specific/split (RC-04, RC-05,
    RC-06, RC-08, RC-13). The `deployable-web-app` column is byte-for-byte
    the v0.2.0 strict contract — the founder's non-compromise constraint,
    satisfied by construction.
  - **Volume axis (ADR-002):** RC-03 merge queue keyed on
    `contribution_model` — MUST when `team`, MUST-NOT when `solo` (direct
    squash-merge to `dev` on `branch-ci` green per GIT-05). Orthogonal to
    profile; default `team` for v0.2.0 compatibility.
  - **RC-02 deadlock fix (ADR-003, profile-invariant):** `dev` classic
    required status checks are now **`branch-ci` only**. `merge-queue-ci` is
    the merge queue's internal `merge_group` gate, never a classic required
    check — listing it as one deadlocks (a classic check must be green
    before queue entry, but `merge-queue-ci` only runs inside the queue).
    Shipped live to `sulis-ai/agents` via PR #2; the standard text now
    matches. RC-02's `Check:` block updated to assert `merge-queue-ci` is
    absent from classic checks. Strict improvement for every queue-enabled
    repo; no safety property weakens.
  - **Multi-artifact composition (ADR-004):** a repo declares either a
    single `profile:` or an `artifacts:` list (mutually exclusive). Rules
    compose by **union** — a rule applies at the strongest severity any
    artifact demands; a per-artifact resource is required iff that
    artifact's type requires it. `branch-ci`/`merge-queue-ci`/`promote` stay
    one each, repo-wide; deploy/health/release/publish workflows are
    namespaced per artifact (`deploy-<name>-staging.yml`, `publish-<name>.yml`);
    environments and deploy secrets are namespaced per deployable artifact.
    Union (not intersection) guarantees a deployable artifact inside a
    monorepo keeps the full strict deployable contract.
  - **Fixed versioning only (honest deferral):** one repo version, one
    SemVer tag, many published outputs. Independent per-artifact versioning
    is out of scope (it would break the RC-01 one-dev/one-main/one-promotion
    invariant); recorded in Out of Scope and ADR-004.
  - **Backward-compatible by default:** no `profile:` and no
    `contribution_model:` ⇒ `deployable-web-app` + `team` = the unchanged
    strict v0.2.0 contract. Multi-artifact is opt-in. Migration of the
    marketplace repo: `profile: plugin-marketplace` → `published-artifact`,
    add `contribution_model: solo`, retire the `deviations:` block.
  - **Companion tooling** (`wpx-arrival-check`, `wpx-bootstrap-repo`,
    `.sulis/repo-contract.yml`) updated alongside to read the profile/
    artifacts + contribution_model and apply this matrix; not part of this
    standard's text.
- **v0.1.0** (2026-05-19) — Initial release. RC-01..RC-13. Strict mode
  only. GitHub.com only. Reference workflow templates inline. Bootstrap
  workflow specified but not yet implemented (companion scripts
  `wpx-arrival-check` and `wpx-bootstrap-repo` are scheduled for the
  next sulis-execution release).
- **v0.2.0** (2026-05-25) — **RC-04 amended (additive).** Merge-queue
  source explicitly named as `change/*` branches (per CW-04 — change
  branch is the integration point reaching the queue; individual
  `feat/wp-*` branches go through `wpx-train` into their parent change
  first, not directly into the queue). The `branch-ci.yml` push trigger
  extended to fire on both `feat/wp-*` AND `change/*` so the change
  branch itself gets CI signal before merging to `dev`. Composes with
  CW-04's two-level worktree hierarchy + CW-05's trivial-change
  carve-out (the only exception to the per-change merge model). Phase
  4 of the change-as-primitive build; pairs with WORK_PACKAGE_STANDARD
  v1.1.0 `change_id:` field + change-work-standard v0.2.0 CW-04 auto
  back-integration + lifecycle.md Step 0 + Step 12.5.
