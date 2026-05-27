---
id: ADR-004
title: Multi-artifact repos — a composition layer over the three profiles (first-class in v0.3.0)
status: implemented in repository-contract-standard.md v0.3.0
date: 2026-05-25
author: SEA
relates_to: repository-contract-standard.md RC-04, RC-05, RC-06, RC-08, RC-11, RC-13; ADR-001 (taxonomy); ADR-002 (volume axis); ADR-003 (RC-02 fix)
supersedes: none
extends: ADR-001
---

# ADR-004 — Multi-artifact composition

## Decision

A repository declares **either** a single `profile:` (ADR-001's three
profiles, the common case) **or** an `artifacts:` list of N **typed
artifacts**. The two are mutually exclusive. Multi-artifact support is
**first-class in v0.3.0** — not deferred, not declare-dominant-or-split.

Each artifact in the list carries:

- a `name` (stable identifier, used to namespace its workflow files),
- a `type` ∈ {`deployable-web-app`, `published-artifact`, `internal-tool`}
  (the same three profiles from ADR-001, now reused as **per-artifact
  types**),
- per-artifact config (deploy environments / health URL for a deployable;
  registry / publish command for a published artifact; nothing extra for an
  internal-tool),
- optional `commands:` slots scoped to that artifact.

```yaml
# .sulis/repo-contract.yml — multi-artifact shape
repo: acme/widget
owner: acme
contribution_model: team        # volume axis (ADR-002) is repo-wide, NOT per-artifact

artifacts:
  - name: api                   # the deployable service
    type: deployable-web-app
    environments:               # this artifact's deploy ladder
      staging:   { health_url_secret: HEALTH_URL_API_STAGING, deploy_token_secret: SULIS_DEPLOY_TOKEN_API_STAGING }
      production:{ health_url_secret: HEALTH_URL_API_PROD,    deploy_token_secret: SULIS_DEPLOY_TOKEN_API_PROD }
    commands:
      deploy_staging: <sulis sdk deploy --env staging>
      deploy_prod:    <sulis sdk deploy --env production>

  - name: sdk                   # the published library shipped from the same repo
    type: published-artifact
    registry: npm
    commands:
      publish_validate: npm pack --dry-run && npm publish --dry-run
      publish:          npm publish
```

**The composition rule (the heart of this ADR):** for each contract rule,
the repo's MUST set is the **union** of the per-artifact requirements — a
rule applies (at its strongest applicable severity) if **any** artifact
requires it.

## Why a composition layer, not a fourth profile

A fourth profile (`multi-artifact`) would break ADR-001's MECE partition.
The partition's discriminator is *"what does a release artifact look
like?"* — and a multi-artifact repo's release is, by definition, **not a
single artifact**. It cannot sit in the same partition as the three
single-artifact profiles without making the partition non-mutually-
exclusive. Composition sidesteps this: the partition stays MECE *per
artifact*, and the repo is modelled as the set union of its artifacts. This
is the conventional move (CP) — it is how monorepo tooling
(Nx/Turborepo/Bazel "targets", Cargo workspace "members", npm workspaces)
already models multi-output repos: a list of typed build targets, not a
single repo-wide type.

## How RC-04 / RC-05 / RC-06 / RC-08 compose

Per-artifact applicability is taken from ADR-001 + DESIGN §6 (each artifact
type has the same rule set it would have as a single-artifact repo). The
**repo-level** requirement is the union.

### RC-04 workflow files — per-artifact, name-namespaced

The single-artifact contract has fixed workflow file names. Multi-artifact
**namespaces the per-artifact workflows by artifact name** so two
deployable artifacts don't collide:

| Workflow | Single-artifact | Multi-artifact |
|---|---|---|
| `branch-ci.yml` | one | **one, repo-wide** (lints/tests the whole repo; shared) |
| `merge-queue-ci.yml` | one (if `team`) | **one, repo-wide** (if `team`) — integration across all artifacts |
| deploy-staging | `deploy-staging.yml` | **`deploy-<name>-staging.yml` per deployable artifact** |
| health-and-smoke | `health-and-smoke.yml` | **`health-<name>-staging.yml` per deployable artifact** |
| release-prod | `release-prod.yml` | **`release-<name>-prod.yml` per deployable artifact**; **`publish-<name>.yml` per published artifact** |
| promote-dev-to-main | `promote-dev-to-main.yml` | **one, repo-wide** (one promotion ceremony tags the whole repo) |

Rules:
- **`branch-ci` and `merge-queue-ci` are repo-wide and shared.** They run the
  union of all artifacts' lint/test/integration commands. There is exactly
  one of each regardless of artifact count. This keeps the queue (RC-03) and
  the RC-02 deadlock fix (ADR-003) **identical to single-artifact** — the
  queue gates the whole repo's integration, not per-artifact.
- **One deploy ladder per deployable artifact.** Each `deployable-web-app`
  artifact gets its own `deploy-<name>-staging.yml`, `health-<name>-*.yml`,
  `release-<name>-prod.yml`. A published artifact gets a `publish-<name>.yml`
  (no server deploy, no health poll — artifact validity is the gate). An
  internal-tool artifact contributes no deploy/health/release/publish
  workflow.
- **One promotion ceremony, repo-wide.** `promote-dev-to-main.yml` is shared:
  one SemVer tag promotes the whole repo. The per-artifact release/publish
  workflows fire off that single promotion (on `push` to `main` / the new
  tag). Rationale: the repo has one `dev` and one `main` (RC-01 invariant);
  versioning the repo once and letting each artifact's release workflow act
  on that tag is the boring monorepo convention (one version, many published
  outputs — the Lerna/Changesets "fixed/locked versioning" default).

### RC-05 environments — union, named per artifact

Each `deployable-web-app` artifact contributes a `staging` + `production`
environment **named for the artifact** (`api-staging`, `api-production`) so
two deployables don't share one ladder. A `published-artifact` contributes
no real deploy environment (it may declare a formality environment so a
`publish-<name>.yml` `environment:` resolves, per the single-artifact
`published-artifact` rule — WARN, not MUST). An `internal-tool` contributes
none. **Repo requirement = the union of all artifacts' environments.**

### RC-06 deploy secrets — union, namespaced per artifact

Each deployable artifact requires its own `SULIS_DEPLOY_TOKEN_<NAME>_STAGING`
/ `_PROD` and `HEALTH_URL_<NAME>_*` secrets (named in the artifact's
`environments:` block). Published / internal artifacts require none. **Repo
requirement = the union** — if any artifact is `deployable-web-app`, its
deploy secrets are MUST.

### RC-08 signed tags — strongest-wins (MUST if any deployable)

A single SemVer tag versions the repo (one promotion ceremony). Its signing
requirement is the **strongest** any artifact demands: if **any** artifact
is `deployable-web-app`, the tag MUST be signed (the deployable profile's
MUST). If the repo is all published/internal, signing degrades to SHOULD
(per those profiles). Union with strongest-wins, because there is one shared
tag and it must satisfy the most stringent artifact.

## The non-weakening guarantee (the founder's load-bearing constraint)

Multi-artifact **must not** weaken the single-artifact profiles or the strict
deployable guarantee. It does not, by construction:

1. **A deployable artifact inside a multi-artifact repo gets the identical
   strict MUST set** it would get as a single-artifact `deployable-web-app`:
   its own deploy-staging + health + release workflows (MUST), its own
   staging+production environments with real targets (RC-05 MUST), its own
   deploy-token secrets (RC-06 MUST), signed tags (RC-08 MUST). Nothing about
   sharing a repo with a library relaxes any of these for the deployable
   artifact.
2. **Union, not intersection.** Because the repo requirement is the *union*,
   adding a lax artifact (a library) to a repo can only **add** requirements,
   never remove the strict deployable artifact's requirements. A
   library-next-to-a-service cannot subtract the service's deploy MUSTs.
3. **The invariant rules stay invariant.** RC-01 (branch model), RC-02
   (protections, with the ADR-003 fix), RC-03 (queue, keyed on the repo-wide
   `contribution_model`), RC-07 (settings), RC-09 (scopes), RC-10
   (CODEOWNERS), RC-11/12 (arrival check + refusal) are repo-wide and
   unchanged. Multi-artifact touches only the four artifact-shaped rules
   (RC-04/05/06/08).
4. **Single-artifact is untouched.** A repo that declares `profile:` (not
   `artifacts:`) runs exactly the ADR-001 path. The composition layer is
   inert for it.

## Arrival-check union semantics (RC-11)

The arrival check's *protocol* is invariant (read-only, ≤30s, RC-11 JSON
contract). For a multi-artifact repo it:

1. reads `artifacts:` (or falls back to single `profile:`),
2. for each rule, computes the **per-artifact action** via the ADR-001
   applicability matrix for that artifact's type,
3. takes the **union**: the repo-level action for a rule is the **strongest**
   action any artifact demands (`error` > `warn` > `skip`),
4. for the **per-artifact** checks (deploy workflows, environments, deploy
   secrets), verifies the **namespaced** resources exist **for each artifact
   that requires them** — e.g. `deploy-api-staging.yml` exists because the
   `api` artifact is deployable; no `deploy-sdk-staging.yml` is required
   because `sdk` is published.

**Union rule, stated once:** *a rule is enforced at the strongest severity
any single artifact requires; a per-artifact resource is required iff that
specific artifact's type requires it.*

Worked example (the founder's repo: `api` deployable + `sdk` published,
`team`):

| Rule | `api` action | `sdk` action | Repo (union) |
|---|---|---|---|
| RC-04 `branch-ci`, `merge-queue-ci` | error | error | error (one shared each) |
| RC-04 `deploy-api-staging.yml` | error | n/a | error (api only) |
| RC-04 `publish-sdk.yml` | error | error | error (sdk only) |
| RC-05 `api-staging`/`api-production` | error | n/a | error (api only) |
| RC-05 `sdk` formality env | n/a | warn | warn (sdk only) |
| RC-06 `SULIS_DEPLOY_TOKEN_API_*` | error | n/a | error (api only) |
| RC-08 signed `v*` tag | error (signed) | warn | **error** (strongest wins) |

## Alternatives considered

### Rejected: a fourth `multi-artifact` profile

Breaks ADR-001's MECE partition (a multi-artifact release is not a single
release artifact; it cannot be mutually exclusive with the three). Also
would need its own full rule set duplicating the three — a fork, not a
specialisation. Composition reuses the three profiles unchanged.

### Rejected: declare-dominant-artifact (the prior proposal's deferral)

The v0.2.0-candidate stance: declare the dominant artifact, handle the
secondary in command slots. Reversed here. It fails the founder's real
case: a repo that ships a service AND a library needs **both validated as
first-class** — both must get their correct MUST set. Forcing the library
into "command slots of the service profile" would leave the library's
publish-validate unenforced and the service's deploy MUSTs incorrectly
applied to the library. The founder explicitly requires first-class
multi-artifact; dominant-declaration cannot provide it. Retained only as an
owner-chosen fallback, never required.

### Rejected: intersection semantics (a rule applies only if ALL artifacts need it)

Would let a library (no deploy) **cancel** the service's deploy MUSTs — the
exact weakening the founder forbids. Union is the only composition that
preserves the strict deployable guarantee. Intersection is unsafe; rejected.

### Rejected: per-artifact `contribution_model` / per-artifact merge queue

The merge queue (RC-03) serialises merges to **`dev`** — and the repo has
exactly one `dev` (RC-01 invariant). Concurrent merge pressure is a property
of the repo's contributor count, not of any one artifact. So
`contribution_model` stays **repo-wide** (ADR-002 unchanged); there is one
queue (or none) for the whole repo, gating the union of all artifacts'
integration. Per-artifact queues would need per-artifact integration
branches — out of scope and against RC-01.

### Rejected: per-artifact version tags

Independent SemVer per artifact (`api-v1.2.0`, `sdk-v3.0.0`) is the
"independent versioning" monorepo mode (Changesets independent mode). It
needs per-artifact tag protection, per-artifact promotion, and breaks the
RC-01 "one `dev`, one `main`, one promotion ceremony" invariant. v0.3.0 uses
**fixed/locked versioning** — one repo version, one tag, many published
outputs (the Lerna/Changesets default, the boring choice). Independent
versioning is a future revision if a real repo needs it; flagged as the one
honest limitation of this model (DESIGN §3.5).

## Convention alignment (CP)

- The `artifacts:`-list-of-typed-targets shape is the dominant monorepo
  convention (Nx/Turborepo/Bazel targets, Cargo workspace members, npm
  workspaces). CP-01 priority 2 (dominant industry pattern). Not bespoke.
- Fixed/locked versioning (one tag, many outputs) is the Lerna/Changesets
  default — the boring, older, more widely-adopted of the two monorepo
  versioning modes (CP-04: prefer the more boring convention).
- Built on the existing `.sulis/repo-contract.yml` manifest — CP-01
  priority 0 (internal prior art); no new mechanism invented.

## Consequences

- `.sulis/repo-contract.yml` gains an `artifacts:` list as an alternative to
  `profile:`. The two are mutually exclusive (arrival check errors if both
  present).
- `wpx-arrival-check` gains a union step over `artifacts:` (DESIGN §7.4),
  layered on the ADR-001 applicability matrix. The RC-11 JSON contract shape
  is unchanged — only which checks run (namespaced, per artifact) changes.
- `bootstrap-repo-contract.sh` iterates artifacts: one deploy ladder per
  deployable artifact, one publish workflow per published artifact, one
  shared branch-ci/merge-queue-ci/promote, namespaced environments and
  secrets (DESIGN §7.5).
- The deployable-web-app strict guarantee and the team/solo axis are
  unchanged (this ADR touches only RC-04/05/06/08, all as union additions).
- One honest limitation carried forward: **fixed versioning only** — a repo
  needing independently-versioned artifacts is unsupported in v0.3.0
  (DESIGN §3.5, §7 open questions).
