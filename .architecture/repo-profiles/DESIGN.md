# Repo Profiles — Design Proposal (RC v0.3.0 candidate)

> **Status:** Proposal for review (revision 2). Not yet a standard rewrite.
> **Date:** 2026-05-25
> **Author:** Senior Engineering Architect (SEA)
> **Subject standard:** `plugins/sulis/references/repository-contract-standard.md` (RC-01..RC-13, v0.2.0)
> **Companion ADRs:** ADR-001 (profile taxonomy), ADR-002 (merge-queue volume dimension), ADR-003 (RC-02 deadlock fix — **shipped live**), ADR-004 (**multi-artifact composition — new**)
> **Founder constraint (load-bearing):** *"We don't want to compromise what we've built elsewhere."* Profiles **add** specialisation; they never weaken the strict `deployable-web-app` profile — and neither does multi-artifact.
>
> **Revision 2 changes (this version):**
> - **Multi-artifact is now first-class** (§3.5, §4a applicability, §7.4 arrival-check union, §7.5 bootstrap) — was deferred in revision 1. A repo may declare N typed artifacts; RC-04/05/06/08 compose by **union**. ADR-004 records the decision.
> - **`internal-tool` is confirmed in scope** as a full first-class single-artifact profile (founder confirmed; was a recommendation).
> - **The RC-02 deadlock fix (§5, ADR-003) has shipped live** to this repo on `dev` via PR #2; the standard + arrival-check + bootstrap edits are still pending (noted inline). The `dev-merge-queue` ruleset for this repo was deleted (solo repo, ADR-002).

---

## 1. Problem statement

The Repository Contract (RC-01..RC-13) was written for one repo shape: a
deployable web product with a URL, a staging server, and a production
server. Four MUST rules — and one MUST primitive inside a fifth — assume
a deploy target exists:

| Rule | Assumes |
|---|---|
| RC-04 | `deploy-staging.yml`, `health-and-smoke.yml`, `release-prod.yml` workflows deploy to a server and poll a health URL |
| RC-05 | `staging` + `production` environments map to real deploy surfaces |
| RC-06 | `SULIS_DEPLOY_TOKEN_*` / `HEALTH_URL_*` secrets authenticate a deploy + name a poll target |
| RC-08 | Signed `v*` tags cut by a promotion workflow with a GPG key in CI |
| RC-03 | GitHub Merge Queue runs speculative batches — built for high-volume multi-developer flow |

For a plugin marketplace, an npm/PyPI library, or a CLI tool there is **no
URL to health-check, no staging server, no deploy token**. We hit this
on the Sulis marketplace repo itself (`sulis-ai/agents`): it cannot run
its own executor pipeline because it has no deploy target. We unblocked a
dogfood test with three documented `deploy_target: none` deviations
(RC-05, RC-06, RC-08) recorded in `.sulis/repo-contract.yml`, and the
arrival check (`wpx-arrival-check`) hard-codes a hack: it downgrades
RC-05/06/08 to WARN when `deploy_target: none`.

A second rule then bit us: **the merge queue (RC-03)**. On a
single-maintainer marketplace repo the queue is speculative-batch
machinery built for high-volume multi-developer teams. It added pure
ceremony and then actively **blocked a validated green PR** — the
`merge_group` workflow wouldn't trigger and the queue stuck on
`AWAITING_CHECKS`.

And while investigating the queue, we found a **profile-invariant bug**
(it bites even the deployable profile): RC-02 lists `merge-queue-ci` as a
*classic branch-protection required status check* on `dev`. But
`merge-queue-ci` only runs on the `merge_group` event — inside the queue.
That is a deadlock: a PR can't enter the queue until required checks pass,
and `merge-queue-ci` can't run until the PR is in the queue.

This proposal solves all three:
1. **Profiles** — formalise the `deploy_target: none` hack into a
   principled profile model that adds non-deployable profiles without
   weakening the deployable one.
2. **Merge-queue as profile-specific** — the queue is off for the
   single-maintainer profiles; the deployable multi-developer profile
   keeps it strict.
3. **RC-02 deadlock fix** — a profile-invariant correction applied to all
   profiles.

---

## 2. Design constraint, made operational

The founder's constraint is the design's acceptance test:

> **The `deployable-web-app` profile must be byte-for-byte the v0.2.0
> strict contract.** Every RC rule that is MUST today stays MUST for that
> profile. A repo that conforms to RC v0.2.0 today must still conform,
> unchanged, after this amendment ships — see §6 backward-compat.

Profiles are **additive specialisation**: they relax MUSTs *only* for
profiles where the relaxed rule is physically meaningless (no deploy
target → deploy secrets are meaningless) or is ceremony with negative
value (single maintainer → speculative-batch queue blocks more than it
protects). They never relax a MUST that carries the same safety value
across profiles (branch model, branch protection, squash settings, token
scopes, CODEOWNERS).

This is the **CP-01 priority-0 move**: the strict contract is the
system's existing, shipping reality. We specialise around it, we don't
duplicate or fork it.

---

## 3. Profile taxonomy (the partition)

### 3.1 The two axes

The deviations we hit are driven by **two independent properties of a
repo**, not one:

| Axis | Question | Drives |
|---|---|---|
| **Deployability** | Does merging produce a running service at a URL? | RC-04 deploy/health/smoke workflows, RC-05 environments, RC-06 deploy secrets, RC-08 signed tags |
| **Contribution volume** | One maintainer / low PR rate, or a multi-developer team merging concurrently? | RC-03 merge queue (speculative batching only pays off under concurrent merge pressure) |

These are **orthogonal**. A deployable web app can be single-maintainer
(a solo founder's SaaS). A library can be high-volume (a popular OSS
package with many contributors). Collapsing them into one "profile" axis
would mis-classify both. ADR-002 records the decision to keep them
orthogonal.

### 3.2 The partition (MECE)

The **profile** names the deployability axis. The **volume** is a separate
declared field, not a profile. This keeps the profile set small and
MECE on a single discriminator (the deploy target), with volume handled
as an orthogonal modifier (§4).

**Discriminator for the profile partition:** *"What does a release
artifact look like?"*

| Profile | Release artifact | Deploy target | Health surface | Examples |
|---|---|---|---|---|
| **`deployable-web-app`** | A running service | A server/URL (staging + prod) | HTTP `/health` endpoint | SaaS API, web app, backend service |
| **`published-artifact`** | A versioned package consumers install | A registry (npm, PyPI, crates.io, **a marketplace consumers point at**) | Artifact validity (manifest parses, package imports, version is monotonic) | npm/PyPI library, CLI tool, **Claude Code plugin marketplace** |
| **`internal-tool`** | Source on `main` (no published artifact, no server) | None — the repo *is* the deliverable | Build + test green | Scripts repo, infra-as-code, docs site source, mono-repo of internal helpers |

**Why these three are MECE on the discriminator:**

- **Mutually exclusive** — a single release **artifact** is exactly one of:
  a running service (deployable-web-app), an installable versioned package
  (published-artifact), or nothing published at all (internal-tool). The
  partition is on the *artifact*. A repo that genuinely ships *both* a
  service and a library has **two artifacts**, each landing cleanly in
  exactly one cell of the partition — it declares them as a list rather than
  picking one profile (§3.5 multi-artifact composition). The partition stays
  MECE per artifact; the multi-artifact repo is the union of its artifacts.
- **Collectively exhaustive** — every repo the marketplace operates on
  produces one of the three. There is no fourth category of "release
  artifact" that isn't a service, a package, or nothing.

**Why `published-artifact` is ONE profile, not three (`marketplace` /
`library` / `cli`):** marketplace, library, and CLI differ in *what*
the package is, but they are **identical with respect to the RC contract** —
none deploys to a server, all release by publishing a versioned artifact,
all health-check by validating the artifact rather than polling a URL.
Splitting them would create three profiles that share every contract
clause: a MECE violation (the partition would not be on a contract-relevant
discriminator). The marketplace-specific bits (validate `marketplace.json`,
check plugin manifests) live in the **project-specific command slots**
(`.sulis/repo-contract.yml` `commands:`), exactly as they do today — that is
where per-project variation belongs, not in the profile taxonomy. ADR-001
records this.

### 3.3 The marketplace repo's classification

`sulis-ai/agents` is a `published-artifact` repo. Its `repo-contract.yml`
already says `profile: plugin-marketplace`; under this proposal that
becomes `profile: published-artifact` (with the marketplace-specific
validation living in `commands:`, where it already lives). The `dev`
branch is the installable surface (consumers point
`extraKnownMarketplaces` at it); a SemVer tag on `main` is the production
release (consumers install from it). That maps cleanly:
"deploy to staging" = validate the installable marketplace;
"deploy to prod" = publish a GitHub Release from the tag.

### 3.4 Single-artifact vs multi-artifact: the two repo shapes

A repo is **exactly one of two shapes**:

| Shape | Declares | When |
|---|---|---|
| **Single-artifact** | one `profile:` (one of the three above) | The common case. Everything RC v0.2.0 assumed. The marketplace repo is here (`published-artifact`). |
| **Multi-artifact** | an `artifacts:` list of N typed artifacts | A monorepo that ships more than one release artifact — e.g. a deployable service AND a published library from one codebase. |

This is itself a clean partition (a repo declares `profile:` XOR
`artifacts:` — never both; the arrival check errors if both are present).
The three profiles are reused as the **per-artifact types** inside the
`artifacts:` list. §3.5 gives the composition model.

### 3.5 Multi-artifact composition (first-class in v0.3.0)

**This is new in revision 2.** Revision 1 deferred multi-artifact
(declare-dominant-or-split). The founder has a real repo today that ships
**both** a deployable service **and** a published library from one
codebase, and needs **both validated as first-class** — each with its own
correct MUST set. So v0.3.0 supports a repo declaring **multiple
artifacts**, each carrying its own RC-04/05/06/08 applicability.

**Declaration** — an `artifacts:` list, each entry a `name` + a `type` (one
of the three profiles) + per-artifact config:

```yaml
# .sulis/repo-contract.yml — multi-artifact
repo: acme/widget
owner: acme
contribution_model: team          # volume axis (§4) is repo-wide, NOT per-artifact

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

**The composition rule (one sentence):** *for each contract rule, the
repo's requirement is the **union** of the per-artifact requirements — a
rule applies, at the strongest severity any artifact demands, if **any**
artifact requires it; a per-artifact resource (a deploy workflow, an
environment, a deploy secret) is required iff that specific artifact's type
requires it.*

Why **union, not intersection**: intersection would let a lax artifact (the
library, which needs no deploy) **cancel** the strict artifact's deploy
MUSTs — exactly the weakening the founder forbids. Union can only **add**
requirements; it can never subtract the deployable artifact's strict set.
ADR-004 records this; §4a gives the per-rule composition.

**Why this does not weaken anything** (the founder's load-bearing
constraint, restated for multi-artifact):

- A `deployable-web-app` artifact **inside** a multi-artifact repo gets the
  **identical** strict MUST set it would get as a single-artifact deployable
  repo — its own deploy/health/release workflows, its own staging+production
  environments with real targets, its own deploy-token secrets, signed tags.
  Sharing a repo with a library relaxes **none** of these.
- The invariant rules (RC-01/02/03/07/09/10/11/12) are **repo-wide and
  unchanged**. Multi-artifact touches only the four artifact-shaped rules
  (RC-04/05/06/08).
- Single-artifact repos run the unchanged §3-§9 path; the composition layer
  is inert for them.

**Honest limitation carried forward — fixed versioning only.** v0.3.0 uses
**one repo version, one SemVer tag, many published outputs** (the
Lerna/Changesets fixed-versioning default — the boring, older convention,
CP-04). A repo that needs **independently-versioned** artifacts
(`api-v1.2.0` and `sdk-v3.0.0` cut separately) is **not** supported in
v0.3.0 — that needs per-artifact tag protection + per-artifact promotion,
which breaks the RC-01 "one `dev`, one `main`, one promotion ceremony"
invariant. Flagged in §9a open questions. This is the single genuine
limitation of the multi-artifact model; everything else is first-class.

---

## 4. The volume dimension (orthogonal to profile)

The merge queue (RC-03) does not vary with deployability — it varies with
**concurrent merge pressure**. GitHub Merge Queue exists to serialise and
speculatively batch merges when multiple developers race to merge against
a moving `dev`. Its entire value proposition (the Shopify/debugg.ai
batching patterns RC-03 cites) is amortising CI cost across a batch under
*high merge volume*. At one maintainer with a low PR rate there is no race
to serialise; the queue is ceremony, and — as we hit live — a failure
surface.

So volume is a **separate declared field**, not a profile:

```yaml
# .sulis/repo-contract.yml
profile: published-artifact     # deployability axis
contribution_model: solo        # volume axis: solo | team
```

| `contribution_model` | Merge queue (RC-03) | Merge mechanism | Rationale |
|---|---|---|---|
| **`team`** (default for v0.2.0 compat) | **MUST** — enabled, RC-03 config | PRs enter queue; `merge_group` runs `merge-queue-ci` | Concurrent merges race; queue serialises + batches (RC-03 value holds) |
| **`solo`** | **MUST NOT** — queue disabled | Direct squash-merge to `dev` on `branch-ci` green (the GIT-05 no-PR direct-merge path) | No concurrent merge pressure; queue is ceremony + a live failure surface |

This is **convention-aligned, not bespoke** (CP-04): GitHub's own
guidance and the dominant industry pattern is that merge queues are for
busy repos with frequent concurrent merges. Disabling the queue for a
solo repo is the boring, conventional choice — GIT-05's no-PR
direct-merge-to-dev path already describes exactly this flow (it is what
Netflix/Etsy-style trunk-based solo flow looks like). ADR-002 records the
orthogonal-dimension decision over the alternative of folding volume into
the profile.

**Interaction with the RC-02 deadlock fix (§5):** when
`contribution_model: solo`, `merge-queue-ci` is not just demoted from
classic required checks (the §5 fix) — the whole `merge_group` workflow
and queue are absent. The `solo` repo's `dev` protection requires
`branch-ci` only.

---

## 4a. Multi-artifact rule composition (how RC-04/05/06/08 combine)

For a multi-artifact repo, each artifact's per-rule applicability is taken
from §6 (each artifact type has the same rule set it would have as a
single-artifact repo). The **repo-level** requirement is the union. The
queue (RC-03) keys on the **repo-wide** `contribution_model` (one `dev`,
one queue or none — §4 unchanged; not per-artifact). The four
artifact-shaped rules compose as follows.

### 4a.1 RC-04 workflow files — repo-wide shared + per-artifact namespaced

| Workflow | Single-artifact | Multi-artifact |
|---|---|---|
| `branch-ci.yml` | one | **one, repo-wide, shared** — runs the union of all artifacts' lint/test/smoke |
| `merge-queue-ci.yml` | one (if `team`) | **one, repo-wide, shared** (if `team`) — integration across all artifacts on the merge_group ref |
| deploy-staging | `deploy-staging.yml` | **`deploy-<name>-staging.yml` per deployable-web-app artifact** |
| health-and-smoke | `health-and-smoke.yml` | **`health-<name>-staging.yml` per deployable-web-app artifact** |
| release-prod | `release-prod.yml` | **`release-<name>-prod.yml` per deployable artifact**; **`publish-<name>.yml` per published artifact** |
| promote-dev-to-main | `promote-dev-to-main.yml` | **one, repo-wide** — one promotion ceremony tags the whole repo |

`branch-ci` and `merge-queue-ci` stay **exactly one each**, repo-wide. This
keeps RC-03 and the ADR-003 RC-02 fix **byte-for-byte identical** to
single-artifact — the queue gates the whole repo's integration, not per
artifact. Each deployable artifact gets its own deploy ladder; each
published artifact gets its own publish workflow; internal-tool artifacts
contribute no deploy/health/release/publish workflow. One promotion
ceremony (one `dev`, one `main`, RC-01 invariant) cuts one tag that each
per-artifact release/publish workflow then acts on.

### 4a.2 RC-05 / RC-06 / RC-08 — union

| Rule | Composition |
|---|---|
| **RC-05** environments | Union, named per artifact (`api-staging`, `api-production`). Each `deployable-web-app` artifact → its own staging+production with real targets (MUST). `published-artifact` → optional formality env (WARN). `internal-tool` → none. |
| **RC-06** deploy secrets | Union, namespaced (`SULIS_DEPLOY_TOKEN_<NAME>_STAGING`, `HEALTH_URL_<NAME>_*`). Required iff that artifact is deployable. If **any** artifact is deployable, its deploy secrets are MUST. |
| **RC-08** signed tags | **Strongest-wins** — one shared SemVer tag. If **any** artifact is `deployable-web-app`, the tag MUST be signed (the deployable MUST). All-published/internal → signing degrades to SHOULD. |

### 4a.3 Worked example — the founder's repo (`api` deployable + `sdk` published, `team`)

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

---

## 5. The RC-02 deadlock fix (profile-invariant) — SHIPPED LIVE

**This is a genuine bug, independent of profiles. It must be fixed in the
standard regardless of the profile work — it bites the deployable profile
too.**

> **Status update (revision 2):** this fix has **shipped live** to this repo.
> `sulis-ai/agents`'s `dev` classic required status checks are now
> `["branch-ci"]` only (verified 2026-05-25), merged via **PR #2**. This
> repo's `dev-merge-queue` ruleset was **deleted** — it is a solo repo
> (ADR-002), so it runs no queue at all. **The standard text, the
> `wpx-arrival-check` code, and the bootstrap script still encode the old
> two-check contract** and must be edited in the v0.3.0 rewrite (§5.4,
> ADR-003 Status). Concretely: `wpx-arrival-check` still loops
> `("branch-ci", "merge-queue-ci")` — run against this repo today it would
> spuriously FAIL RC-02, because the live config (correctly) has only
> `branch-ci`. That mismatch is the proof the code still carries the bug.

### 5.1 The deadlock

RC-02 `dev` protection today lists **two** classic required status checks:

```
required_status_checks.contexts = ["branch-ci", "merge-queue-ci"]
```

- `branch-ci` fires on `pull_request` / `push` → runs on the PR's head ref.
  A PR can satisfy it. Correct.
- `merge-queue-ci` fires **only** on `merge_group` (RC-04, RC-13). It runs
  on the synthetic merged ref **GitHub creates after a PR enters the
  queue**. A PR sitting *outside* the queue can never produce a
  `merge-queue-ci` run.

A classic required status check must be green **before the PR can be
added to the queue**. But `merge-queue-ci` only exists **after** the PR is
in the queue. The PR waits for a check that cannot run until the PR stops
waiting → `AWAITING_CHECKS` forever. This is the live symptom we observed.

### 5.2 The fix

`merge-queue-ci` is the **queue's own internal gate**, not a classic
branch-protection required status check. GitHub Merge Queue runs the
`merge_group` workflow as the gate for *merging the batch* — that is its
designed role. It must NOT also appear in
`required_status_checks.contexts`.

**Corrected RC-02 `dev` protection (for any profile that runs a queue):**

```
required_status_checks.contexts = ["branch-ci"]     # ONLY branch-ci
require_merge_queue = true                            # the queue runs merge-queue-ci as its internal gate
```

The flow becomes deadlock-free:
1. PR opened → `branch-ci` runs on the head ref → green.
2. `branch-ci` is the only classic required check → satisfied → PR is
   eligible to enter the queue.
3. PR enters the queue → GitHub creates the `merge_group` ref →
   `merge-queue-ci` runs on it → green → batch merges to `dev`.

`merge-queue-ci` still gates every merge to `dev` — but as the queue's
gate (where it can actually run), not as a classic check (where it
deadlocks). Validated live: with only `branch-ci` in classic required
checks, the queue ran `merge-queue-ci` and merged the green PR.

### 5.3 Profile applicability

| | `merge-queue-ci` in classic required checks? | `merge-queue-ci` runs as queue gate? |
|---|---|---|
| Queue-enabled repo (`contribution_model: team`, any profile) | **NO** (the fix) | **YES** |
| Queue-disabled repo (`contribution_model: solo`) | NO (no queue at all) | N/A — no queue; `merge-queue-ci.yml` may be absent |

The fix is **profile-invariant**: it corrects the contract for every repo
that runs a queue, including `deployable-web-app`. ADR-003 records it. The
arrival check and bootstrap both change (§5.4) regardless of profile work
landing.

### 5.4 What changes in code for the fix alone

- **`wpx-arrival-check`** `_check_rc02_protections` — stop requiring
  `merge-queue-ci` in `contexts`; require only `branch-ci`. When a queue
  is expected (team model), additionally verify the queue is enabled
  (this is RC-03's check, already present). Drop `merge-queue-ci` from the
  `for required in (...)` loop.
- **`bootstrap-repo-contract.sh`** RC-02 block — change the dev-protection
  JSON `"contexts": ["branch-ci", "merge-queue-ci"]` to
  `"contexts": ["branch-ci"]`.

---

## 6. Rule classification table (the heart of the design)

Every RC rule classified as **profile-invariant** (same MUST for all
profiles) or **profile-specific** (varies). The profile-specific column
shows the value per profile. `team`/`solo` modifies only RC-03.

Legend: **M** = MUST, **W** = WARN/advisory (rule's check downgrades to a
warning), **S** = SHOULD, **N/A** = rule does not apply, **—** = unchanged
from invariant.

| Rule | Topic | Class | `deployable-web-app` | `published-artifact` | `internal-tool` | Notes |
|---|---|---|---|---|---|---|
| **RC-01** | dev/main branch model | **Invariant** | M | M | M | Branching is identical regardless of what ships. |
| **RC-02** | Branch protections | **Invariant** (with §5 fix) | M | M | M | Protections apply to all. **Fix:** classic required checks = `branch-ci` only; `merge-queue-ci` is the queue's gate, never a classic check. |
| **RC-03** | Merge queue on dev | **Profile-specific** (volume axis) | M if `team`, MUST-NOT if `solo` | M if `team`, MUST-NOT if `solo` | M if `team`, MUST-NOT if `solo` | Driven by `contribution_model`, NOT by profile. See §4. |
| **RC-04** | Six workflow files | **Split** | All six, M | `branch-ci` + `merge-queue-ci`† M; deploy/health/release **repurposed** (validate/publish), M-conform | `branch-ci` (+ queue† ) M; deploy/health/release **N/A** | See §6.1 per-workflow split. †queue workflow only if `team`. **Multi-artifact:** one shared `branch-ci`/`merge-queue-ci`/`promote`; per-artifact namespaced deploy/health/release/publish (§4a.1). |
| **RC-05** | Environments | **Profile-specific** | M (real deploy targets) | W (exist as formality so `environment:` resolves; no deploy) | N/A (no environments) | The `deploy_target: none` deviation, formalised. **Multi-artifact:** union, named per artifact (§4a.2). |
| **RC-06** | Deploy-token secrets | **Profile-specific** | M | N/A (no deploy → meaningless) | N/A | The current hard-coded hack, formalised. **Multi-artifact:** union, namespaced per deployable artifact (§4a.2). |
| **RC-07** | Repo settings (squash-only) | **Invariant** | M | M | M | Squash/linear-history/delete-on-merge are deploy-agnostic. Repo-wide in multi-artifact. |
| **RC-08** | Signed `v*` tags | **Profile-specific** | M (signed) | S (signed if GPG key in CI; else annotated + GitHub-verified bot commits) | S | Signing requires a provisioned key; degrade to SHOULD where none, never to silent. **Multi-artifact:** one shared tag, strongest-wins — signed-MUST if any artifact is deployable (§4a.2). |
| **RC-09** | Token scopes | **Invariant** | M | M | M | The executor needs the same GitHub capabilities regardless of profile. |
| **RC-10** | CODEOWNERS | **Invariant** | S (already SHOULD) | S | S | Already SHOULD; production-promotion reviewer routing only matters when a prod env exists, but the file itself is harmless and useful everywhere. |
| **RC-11** | Arrival check protocol | **Invariant** | M | M | M | The *protocol* is invariant; *which rules it enforces* is profile-driven (that is the whole point — §6.2). |
| **RC-12** | Strict-mode refusal | **Invariant** | M | M | M | Refusal still fires — but on the *profile's* MUST set, not the universal one. |
| **RC-13** | Reference workflow YAML | **Split** | All six templates apply | Deploy/health/release templates' *command slots* run validate/publish work | Deploy/health/release templates N/A | The structural shape stays; the command slots vary (already true via `commands:`). |

**Headline: 7 profile-invariant (RC-01, RC-02, RC-07, RC-09, RC-10,
RC-11, RC-12) + 1 volume-specific (RC-03) + 4 profile-specific or split
(RC-04, RC-05, RC-06, RC-08, RC-13 — RC-04 and RC-13 are "split": part
invariant, part profile-specific).**

The invariant set is exactly the founder's "don't compromise" core: the
branch model, the protections, the squash settings, the token scopes, the
arrival-check protocol, and the refusal contract. None of these is
touched by adding profiles. **The deployable profile column is identical
to the v0.2.0 contract in every row** — that is the acceptance test from
§2, satisfied by construction.

**Multi-artifact reads the same table per artifact, then unions.** The
three profile columns above ARE the per-artifact types. For a
multi-artifact repo, each artifact picks its column; the repo requirement
for each rule is the union across artifacts (§4a). The invariant rows
(RC-01/02/03/07/09/10/11/12) are repo-wide and identical regardless of how
many artifacts the repo has — so multi-artifact, like single-artifact,
leaves the founder's "don't compromise" core untouched. Only the four
artifact-shaped rows (RC-04/05/06/08) compose.

### 6.1 RC-04 per-workflow split

| Workflow | `deployable-web-app` | `published-artifact` | `internal-tool` |
|---|---|---|---|
| `branch-ci.yml` | M | M | M |
| `merge-queue-ci.yml` | M if `team` | M if `team` | M if `team` |
| `deploy-staging.yml` | M (deploys to staging) | **Repurposed** M — command slot validates the installable artifact (e.g. marketplace manifest validation), still triggered on push to `dev` | **N/A** — file absent |
| `health-and-smoke.yml` | M (polls `/health`) | **Repurposed** M — command slot runs artifact integration checks (manifests parse, plugins load), no URL poll | **N/A** — file absent |
| `promote-dev-to-main.yml` | M | M (cuts the SemVer release tag) | M (tags source release) |
| `release-prod.yml` | M (deploys to prod) | **Repurposed** M — command slot publishes the GitHub Release / pushes to registry from the tag | **N/A** — file absent |

`published-artifact` keeps all six **structurally** (right names, right
triggers — the executor reads them by name in the arrival check) but the
command slots in three of them do validate/publish work instead of deploy.
This is exactly what `.sulis/repo-contract.yml` `commands:` already
encodes today; the proposal formalises it as the profile's defined shape
rather than a per-repo deviation. `internal-tool` legitimately omits the
three deploy workflows — the arrival check does not require their presence
for that profile.

### 6.2 What "the arrival check enforces the profile's MUST set" means

RC-11's *protocol* is invariant (read-only, ≤30s, emits the RC-11 JSON
contract, exit 0/1/2). What varies is **the rule set it treats as MUST**.
The check looks up the profile, then for each rule consults a
**profile applicability matrix** (this table, encoded as data) to decide:
enforce as error (M), emit as warning (W), or skip (N/A). This replaces
the current `if deploy_target == "none"` branches scattered through the
checker with one principled lookup. See §7 mechanism.

---

## 7. Mechanism

### 7.1 Declaration — build on `.sulis/repo-contract.yml`

The repo already declares its shape in `.sulis/repo-contract.yml`. We
build on it (CP-01 priority-0: internal prior art). Two fields become
authoritative:

```yaml
# .sulis/repo-contract.yml
repo: sulis-ai/agents
owner: iainn

profile: published-artifact      # deployability axis (§3) — was `plugin-marketplace`
contribution_model: solo         # volume axis (§4) — NEW field

# deploy_target stays as a derived convenience / back-compat alias, but the
# PROFILE is now authoritative. (deploy_target: none ⟺ profile != deployable-web-app)

commands:
  # ... unchanged: marketplace-specific validate/publish commands live here ...
```

- `profile` ∈ `{ deployable-web-app, published-artifact, internal-tool }`
  for a **single-artifact** repo. The marketplace's existing
  `plugin-marketplace` value maps to `published-artifact` (migration §8).
- **OR** `artifacts:` — a list of N typed artifacts for a **multi-artifact**
  repo (§3.5). `profile:` and `artifacts:` are mutually exclusive; the
  arrival check errors if both are present.
- `contribution_model` ∈ `{ team, solo }`. **Default when absent: `team`**
  (preserves v0.2.0 behaviour — see §8). **Repo-wide** — not per-artifact
  (one `dev`, one queue or none; ADR-002 / ADR-004).
- `deploy_target` is retained as a back-compat alias (`none` ⟺ non-deployable
  single profile) so the existing checker code and any external scripts keep
  reading; but `profile` / `artifacts` is authoritative going forward.

This is the conventional, boring mechanism: a single declarative config
file the repo owns, read by the tooling — exactly the
"convention-over-configuration via a checked-in manifest" pattern
(`.github/`, `package.json`, `pyproject.toml`, `Cargo.toml` all do this).
No new mechanism invented.

### 7.2 `wpx-arrival-check` — profile lookup replaces the hack

Replace the scattered `if deploy_target == "none"` special-cases with a
single **profile applicability matrix** driving every check.

```python
# Replaces _read_deploy_target with a richer reader (stdlib-only, same style):
def _read_profile(repo_root) -> tuple[str, str]:
    """Return (profile, contribution_model) from .sulis/repo-contract.yml.
    Defaults: profile inferred from deploy_target for back-compat
    (deploy_target: none -> published-artifact; else deployable-web-app),
    contribution_model -> 'team'."""
    # parse profile:, contribution_model:, deploy_target: (stdlib line scan)
    # back-compat: no profile field + deploy_target: none  -> published-artifact
    #              no profile field + deploy_target absent  -> deployable-web-app

# The matrix encodes §6's table as data. Each rule maps profile -> action.
APPLICABILITY = {
    "RC-05": {"deployable-web-app": "error",
              "published-artifact": "warn",
              "internal-tool": "skip"},
    "RC-06": {"deployable-web-app": "error",
              "published-artifact": "skip",
              "internal-tool": "skip"},
    "RC-08": {"deployable-web-app": "error",   # signed
              "published-artifact": "warn",    # SHOULD
              "internal-tool": "warn"},
    "RC-04-deploy-workflows": {"deployable-web-app": "error",
                               "published-artifact": "error",  # repurposed, still present
                               "internal-tool": "skip"},
    # RC-01/02/07/09/11/12 absent from matrix => always "error" (invariant).
}

def _action(rule, profile) -> str:        # "error" | "warn" | "skip"
    return APPLICABILITY.get(rule, {}).get(profile, "error")
```

Each `_check_rcNN_*` consults `_action(rule, profile)` and routes to
`rep.error` / `rep.warn` / no-op accordingly. RC-03's check additionally
keys on `contribution_model`: for `solo`, it verifies the queue is
**absent** (and that classic required checks are `branch-ci` only); for
`team`, it verifies the queue is **enabled** (current RC-03 check). The
RC-02 fix (§5) drops `merge-queue-ci` from the required-checks loop for
all profiles.

Net effect: the current three hard-coded `deploy_target == "none"`
branches become one matrix lookup, and the checker now correctly handles
three profiles × two volume models instead of one boolean special-case.
The RC-11 JSON contract shape is unchanged — only which rules land in
`errors` vs `warnings` changes.

### 7.3 `bootstrap-repo-contract.sh` — profile-conditional steps

The bootstrap reads `profile` + `contribution_model` and conditionalises:

| Step | `deployable-web-app` | `published-artifact` | `internal-tool` |
|---|---|---|---|
| RC-01 branches, RC-07 settings | always | always | always |
| RC-02 dev protection | `contexts:["branch-ci"]` (§5 fix); `require_merge_queue` if `team` | same | same |
| RC-03 enable queue | if `team` | if `team` | if `team` |
| RC-05 environments | create with deploy config | create empty (formality) | skip |
| RC-06 secrets prompt | prompt for deploy tokens | skip | skip |
| RC-08 tag protection | + signing setup | tag protection, signing optional | tag protection |
| RC-04 write workflows | all six (deploy slots) | all six (validate/publish slots from `commands:`) | four (omit deploy/health/release) |

The bootstrap stays all-or-nothing **within the profile's MUST set**.
The `solo` model skips the RC-03 queue-enable step entirely and sets
`dev` protection with `branch-ci` as the only required check and no
`require_merge_queue` — which is precisely the GIT-05 direct-merge flow.

### 7.4 `wpx-arrival-check` — multi-artifact union step

For a multi-artifact repo the check reads `artifacts:`, then layers the
union over the §7.2 applicability matrix:

```python
def _read_artifacts(repo_root) -> list[dict]:
    """Return [{name, type, ...}, ...] from .sulis/repo-contract.yml.
    If `artifacts:` absent, wrap the single `profile:` (or its back-compat
    inference) as a one-element list so the rest of the checker is uniform.
    Error if BOTH `profile:` and `artifacts:` are present."""

_STRENGTH = {"error": 2, "warn": 1, "skip": 0}

def _repo_action(rule, artifacts) -> str:
    """Union: the strongest action any artifact demands for this rule."""
    actions = [_action(rule, a["type"]) for a in artifacts]   # _action from §7.2
    return max(actions, key=_STRENGTH.__getitem__)            # error > warn > skip
```

- **Repo-wide rules** (RC-01/02/03/07/09/10/11/12) check once, unchanged —
  they do not iterate artifacts. RC-03 keys on the repo-wide
  `contribution_model` exactly as §4. The §5 RC-02 fix applies once.
- **Union rules** (RC-05 environments, RC-06 deploy secrets, RC-08 tag
  signing) use `_repo_action` to decide error/warn/skip, then verify the
  **per-artifact namespaced** resources: e.g. RC-06 requires
  `SULIS_DEPLOY_TOKEN_API_*` because `api` is deployable, and requires no
  `sdk` deploy secret because `sdk` is published.
- **Per-artifact workflow presence** (RC-04 deploy/health/release/publish):
  for each artifact, verify its namespaced files exist iff its type requires
  them (`deploy-api-staging.yml` MUST exist; `publish-sdk.yml` MUST exist;
  no `deploy-sdk-*.yml` is required). The shared `branch-ci`/
  `merge-queue-ci`/`promote-dev-to-main` are checked once, repo-wide.

**Union rule, stated once:** *a rule is enforced at the strongest severity
any single artifact requires; a per-artifact resource is required iff that
specific artifact's type requires it.*

The RC-11 JSON contract shape is **unchanged** — only which checks run
(namespaced, per artifact) and how severities combine (union) changes.
Single-artifact repos hit the one-element-list path and behave exactly as
§7.2.

### 7.5 `bootstrap-repo-contract.sh` — iterate artifacts

For a multi-artifact repo the bootstrap iterates `artifacts:`:

| Step | Single-artifact | Multi-artifact |
|---|---|---|
| RC-01 branches, RC-07 settings, RC-02 protection, RC-03 queue | once, repo-wide | once, repo-wide (identical; `contribution_model` repo-wide) |
| `branch-ci.yml`, `merge-queue-ci.yml`, `promote-dev-to-main.yml` | write once | write once (shared; command slots run the union of artifacts' commands) |
| Deploy ladder (`deploy-<name>-staging.yml`, `health-<name>-*.yml`, `release-<name>-prod.yml`) | one set | **one set per `deployable-web-app` artifact** |
| Publish workflow (`publish-<name>.yml`) | n/a | **one per `published-artifact` artifact** |
| Environments | one staging+prod | **one staging+prod per deployable artifact, namespaced** (`<name>-staging`, `<name>-production`) |
| Secrets prompt | deploy tokens | **prompt per deployable artifact, namespaced** |
| Tag protection / signing | once | once (one shared tag; signing setup if any artifact is deployable) |

The bootstrap stays all-or-nothing **within the union MUST set**. An
internal-tool artifact contributes no deploy/publish steps. A single deploy
ladder per deployable artifact gives the founder's `api` artifact its full
strict deploy machinery, while the `sdk` artifact gets only its
publish-validate workflow — both first-class.

---

## 8. Backward-compatibility + migration

### 8.1 The compatibility guarantee

**A repo conformant to RC v0.2.0 today stays conformant after v0.3.0, with
no config change.** Mechanism: defaults.

- **No `profile:` field** → default depends on `deploy_target` for the
  back-compat bridge:
  - `deploy_target: none` (or any non-deployable signal) → `published-artifact`
  - `deploy_target` absent or a real target → **`deployable-web-app`**
- **No `contribution_model:` field** → default **`team`**.

A v0.2.0 deployable repo has no `profile:` and no `deploy_target: none`,
so it defaults to `deployable-web-app` + `team` = **the full strict
v0.2.0 contract, unchanged**. Nothing breaks. This is the §2 acceptance
test discharged for existing repos: they get the identical rule set they
had.

**Multi-artifact is opt-in.** A repo only becomes multi-artifact by
explicitly declaring `artifacts:`. No existing repo gains an `artifacts:`
list by default, so no existing repo's enforcement changes because of the
composition layer. A repo with `profile:` (or the back-compat inference)
runs the unchanged single-artifact path.

### 8.2 The RC-02 fix is a strict improvement for existing repos — SHIPPED HERE

The §5 deadlock fix removes `merge-queue-ci` from classic required checks
for **every** queue-enabled repo, including existing `deployable-web-app`
`team` repos. Any such repo that was silently deadlock-prone (or that
worked only because no one had hit the race) becomes correctly
deadlock-free. This is a fix, not a relaxation — it does not weaken any
safety property; the queue still gates every merge.

**Done for this repo:** the fix shipped live to `sulis-ai/agents` via PR #2
(`dev` classic required checks now `["branch-ci"]` only; `dev-merge-queue`
ruleset deleted as this is a solo repo). **Pending for the standard +
tooling:** the standard text, `wpx-arrival-check`, and the bootstrap still
encode the old two-check contract and must be edited in the v0.3.0 rewrite
(§5.4, ADR-003). Until then `wpx-arrival-check` would spuriously FAIL RC-02
against this very repo. Existing team repos should re-run bootstrap (or
apply the one-line protection change) once the tooling edit lands; it is
safe and mechanical.

### 8.3 Migration path for the marketplace repo

`.sulis/repo-contract.yml` changes:
- `profile: plugin-marketplace` → `profile: published-artifact`
- add `contribution_model: solo`
- the `deviations:` block (RC-05/06/08) is no longer needed as *deviations*
  — they become the **defined behaviour** of `published-artifact` + `solo`.
  Keep a short note pointing at the profile, or drop the block.
- `commands:` unchanged (marketplace validate/publish logic stays).

After this, the arrival check passes on the profile's MUST set with the
queue disabled, and the live `AWAITING_CHECKS` block is gone (no queue;
direct merge on `branch-ci` green).

### 8.4 No silent profile changes

A repo's profile is declared, never inferred-and-applied silently beyond
the v0.2.0 back-compat bridge. If a repo has no `profile:` field and an
ambiguous `deploy_target`, the arrival check emits a **warning** naming
the inferred profile and recommending the owner declare it explicitly.
This avoids a repo silently sliding from strict to relaxed enforcement.

---

## 9. What stays strictly enforced in `deployable-web-app` (the non-compromise list)

For the founder, explicitly: adopting profiles changes **nothing** for a
deployable web product. Its MUST set after v0.3.0:

- RC-01 dev/main branch model — **MUST, unchanged**
- RC-02 branch protections — **MUST**; the only change is the §5 deadlock
  fix, which makes the queue *work*, not weaker
- RC-03 merge queue — **MUST** (it is a `team` deployable repo)
- RC-04 all six workflows including real deploy/health/release — **MUST,
  unchanged**
- RC-05 staging + production environments with real targets — **MUST,
  unchanged**
- RC-06 deploy-token secrets — **MUST, unchanged**
- RC-07 squash-only settings — **MUST, unchanged**
- RC-08 signed `v*` tags — **MUST, unchanged**
- RC-09 token scopes — **MUST, unchanged**
- RC-11 / RC-12 arrival check + strict refusal — **MUST, unchanged**

The relaxations (RC-05 → W, RC-06 → N/A, RC-08 → S, deploy workflows →
repurposed/absent, queue → off) apply **only** to the non-deployable /
solo profiles, **only** where the rule is physically meaningless or
negative-value, and **never** to `deployable-web-app`.

**And never to a `deployable-web-app` artifact inside a multi-artifact
repo.** Because the repo requirement is the *union* (§4a), adding a library
or internal-tool artifact alongside a deployable one can only **add**
requirements — it can never subtract the deployable artifact's strict set.
The founder's `api` artifact, sharing a repo with the `sdk` library, gets
the byte-for-byte strict deployable contract above. The non-compromise
guarantee holds in both the single-artifact and multi-artifact shapes.

---

## 9a. Open questions / honest limitations

1. **Independent per-artifact versioning is NOT supported in v0.3.0.** The
   multi-artifact model uses **fixed versioning** — one repo version, one
   SemVer tag, many published outputs (Lerna/Changesets fixed mode; the
   boring, older convention, CP-04). A repo that needs to cut `api-v1.2.0`
   and `sdk-v3.0.0` on independent cadences would need per-artifact tag
   protection + per-artifact promotion, which breaks the RC-01 "one `dev`,
   one `main`, one promotion ceremony" invariant. Deferred to a future
   revision; flagged here because it is the one genuine limitation of the
   multi-artifact model (ADR-004). **Founder input wanted:** does the real
   multi-artifact repo need independent versioning, or is one-tag-versions-
   everything acceptable for v0.3.0?
2. **Per-artifact `branch-ci` scoping is out of scope.** v0.3.0 runs one
   repo-wide `branch-ci` that executes the union of all artifacts' checks.
   A large monorepo might want path-filtered per-artifact CI (only run the
   `sdk` tests when `sdk/` changed). That is a CI-optimisation, not a
   contract requirement, and is deferred.

---

## 10. Summary of changes this proposal would drive (the follow-on rewrite)

| Artifact | Change |
|---|---|
| `repository-contract-standard.md` | Add a "Repo Profiles" section + the §6 classification table; add `profile` / `contribution_model` **and the `artifacts:` multi-artifact declaration** to the declaration; rewrite RC-02 (§5 fix — text still has both checks), RC-03 (volume-conditional), RC-05/06/08 (profile-conditional **+ union composition**), RC-04/13 (per-workflow split **+ per-artifact namespacing**). Bump to v0.3.0. |
| `wpx-arrival-check` | Replace `_read_deploy_target` + scattered `deploy_target == "none"` branches with `_read_profile` + the applicability matrix (§7.2). **Add `_read_artifacts` + the union step (§7.4).** Apply §5 RC-02 fix (still loops both checks today — line 124). Add RC-03 volume keying. |
| `bootstrap-repo-contract.sh` / `wpx-bootstrap-repo` | Profile-conditional steps (§7.3) + **iterate `artifacts:` (§7.5)**. Apply §5 RC-02 fix (`contexts:["branch-ci"]`). |
| `.sulis/repo-contract.yml` (marketplace) | `profile: published-artifact`, `contribution_model: solo`; retire the `deviations:` block (§8.3). (Single-artifact; not affected by the multi-artifact layer.) |

The §5 RC-02 deadlock fix is **shipped live** to this repo (PR #2) — but the
standard + `wpx-arrival-check` + bootstrap edits for it are **still pending**
and ride the v0.3.0 rewrite (or can ship sooner; they are independent of the
profile/multi-artifact work). The multi-artifact composition (ADR-004) is
the significant new design in this revision.
