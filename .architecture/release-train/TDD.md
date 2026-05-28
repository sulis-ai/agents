---
id: TDD-release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
status: decomposed
sourced_from: .changes/release-train.SPEC.md
tier: M
founder_facing: false
---

# Technical Design — changeset-based release-train (Option B)

> **The spec is authoritative.** This TDD formalises the spec's already-decided
> decomposition with rigorous, test-first contracts. It does **not** re-litigate
> the approach — the founder chose Option B (`dev→main` PR + release-on-merge
> GHA) and wrote `.changes/release-train.SPEC.md`. Where this document and the
> spec disagree, the spec wins; any such disagreement is a bug in this TDD.

## Conclusion (lead with the answer)

`/sulis:change ship` today couples **integration** (land on `dev`) with
**release** (bump versions + assemble CHANGELOG + tag), and leaves the release
half to agent discipline. The result: features ship to `dev` unlabelled (#52,
#59, #53) and two changes targeting the same next-version collide (#64 vs #52).

The fix **decouples the two halves**:

1. Each change writes a **changeset** — a small YAML file (`.changesets/*.yaml`)
   recording *intent and tier*, never a version number. The tier is derived
   deterministically from the change's primitive.
2. Changes accumulate on `dev`, each carrying its own changeset.
3. `/sulis:release-train` reads the accumulated changesets and opens a reviewed
   `dev→main` PR with the computed cumulative version and an assembled CHANGELOG
   preview.
4. On merge to `main`, a single bot-driven GitHub Action (`release-on-merge.yml`)
   is the **one authority** that computes the cumulative tier, bumps all three
   version values, assembles the CHANGELOG entry, deletes the consumed
   changesets, commits as `github-actions[bot]`, tags `v<marketplace-version>`,
   and pushes.

The deterministic core is `_changeset.py` (WP-001) — the keystone. Its
companion `.changesets/README.md` is the **producer/consumer contract**: the
ship flow (WP-002) writes the YAML; the GHA (WP-003) and the release-train
skill (WP-004) read it. Everything else depends on that contract landing first
(CONTRACT_FIRST).

---

## MECE-3 pillar coverage

### Form — Structural Integrity

The work has one structural seam: the **changeset YAML**, a producer/consumer
contract between three readers/writers.

| Component | Role | New / modified | Owns the interface? |
|---|---|---|---|
| `_changeset.py` | Deterministic core — the data model + every pure function | NEW (WP-001) | Yes — the contract is its public surface |
| `.changesets/README.md` | The written YAML contract (the seam) | NEW (WP-001) | — (it *is* the contract) |
| `/sulis:change ship` step (sibling of 4.6) | **Producer** — writes one changeset before the merge | MODIFIED (WP-002) | No — consumes `_changeset.write_changeset` |
| `release-on-merge.yml` | **Consumer** — the bump authority on push to `main` | NEW (WP-003) | No — reads `.changesets/*.yaml` per the contract |
| `/sulis:release-train` skill | **Consumer** — drafts the `dev→main` PR (read-only) | NEW (WP-004) | No — reads `.changesets/*.yaml` per the contract |
| `version-check.yml` | **Guard** — asserts plugin diffs carry a changeset | NEW (WP-005) | No — reads `.changesets/*.yaml` count |
| `main` branch protection | Config that lets the bot push the bump | CONFIG (WP-006) | — |
| `git-workflow-standard.md` + ship docs | The documented ceremony | MODIFIED (WP-007) | — |

**Dependency direction.** `_changeset.py` is a leaf module — it imports nothing
from the rest of the toolchain and lives alongside `_wpxlib.py` in
`plugins/sulis/scripts/`. The GHA and skill shell out to it (or re-implement the
identical computation in bash, mirroring honest's workflow — see ADR-004 on the
duplication trade-off). The contract (`.changesets/README.md`) is the single
source of truth both directions point at.

**This is `EXPAND-Create`, not `SUBSTITUTE-Wrap`.** `_changeset.py` is a new
module; the GHA, the version-check guard, and the release-train skill are all
net-new. The one `MODIFIED` of internal code (the ship flow, WP-002) is a
genuine edit to the SKILL.md body — it adds a step and **removes** nothing of
the manual-bump kind (the ship-to-dev flow never had a bump step; see the
"Ambiguity resolved" note below). No wrappers are introduced. No subject in the
codebase is wrapped. The Wrap audit in the WP INDEX is empty.

### Armor — Operational Hardening

The blast radius is **release machinery**, so "hardening" here means *guards on
the bump authority* and *self-lockout avoidance*, not network resiliency
(there are no hot-path external calls to circuit-break).

| Guard | Where | What it prevents |
|---|---|---|
| **VERSION_DRIFT abort** | GHA (WP-003) + release-train skill (WP-004) | Bumping when `plugin.json` ≠ marketplace sulis-entry version before the bump — a partial prior bump would otherwise compound. |
| **Post-bump verification** | GHA (WP-003) | Re-reads all three version values after the `jq` edits; fails the workflow if any did not move. A silent half-bump never reaches a tag. |
| **Loop-guard** | GHA (WP-003) | The job's `if:` skips the bot's own release commit (`release: sulis v…`) so the push-back doesn't re-trigger the workflow. |
| **"Nothing to release" exit 0** | GHA (WP-003) | No pending changesets → the workflow exits cleanly (admin-only / docs-only release), never errors. |
| **Advisory-first version-check** | CI guard (WP-005) | Promoting to a required check *before* the writer is live + producing changesets would lock every in-flight `change/*` branch out of merging (self-lockout). WP-005 ships warn-only (exit 0) this cycle; promotion to required is a **separate, later, founder-gated** step. |
| **Founder-gated branch protection** | Config (WP-006) | `enforce_admins: false` so `github-actions[bot]` can push the bump commit + tag; the exact `gh api` config is shown to the founder and the bot's push is verified on a throwaway **before** the train is relied upon. |
| **Triple-key collision-proof filename** | `_changeset.py` (WP-001) | `{primitive}-{slug}-{datetimeZ}.yaml` — two parallel changes can never write the same changeset path (the #64-vs-#52 conflict class). |
| **Read-only release-train skill** | Skill (WP-004) | The skill never commits, edits the working tree, or bumps — its only side effect is `gh pr create`. The bump authority stays singular (the GHA). |

**Observability** is light by design: the GHA emits step-level log lines
(`Computed tier: …`, `New: …`, the assembled CHANGELOG body, `Released sulis
v…`) that surface in the Actions run; no spans/metrics are warranted for a
once-per-release batch job. The version-check guard echoes its decision.

### Proof — Verification Protocol

| Subject | Test kind | Where |
|---|---|---|
| Every `_changeset.py` function | **Unit** (Red-Green-Blue) — the deterministic core | `plugins/sulis/scripts/tests/unit/test_changeset.py` (WP-001) |
| `tier_for_primitive` full mapping | Unit — table-driven over all 22 primitives + admin/docs-only → `None` | WP-001 |
| `cumulative_tier` (max precedence) | Unit — `[patch, minor] → minor`; `[patch, patch, major] → major`; `[] → None` | WP-001 |
| `next_version(current, tier)` dual-series | Unit — patch/minor/major over both the plugin (0.x.y) and marketplace (1.x.y) series; `tier=None → unchanged` | WP-001 |
| Filename builder collision-proofing | Unit — same primitive+slug at different `datetimeZ` → distinct paths; sanitisation of slug | WP-001 |
| `write_changeset` / `read_changesets` round-trip | Unit — write N, read N back; field fidelity; ignores non-`.yaml` | WP-001 |
| The contract examples in `.changesets/README.md` | Validated by `read_changesets` parsing them in a unit test (the contract's examples are executable) | WP-001 |
| Ship writes a valid changeset | The ship-flow change is a SKILL.md edit; its proof is that the **documented** step calls `write_changeset` and the WP-001 unit suite proves the function. The ship path itself is exercised by this change's own ship (manual, last time). | WP-002 |
| GHA bump end-to-end | **Verified on a real cut** (spec "How we'll know it's done") — the NEXT release after this change ships uses the train; the WP-003 acceptance criteria pin the post-bump verification + tag. Bash-level logic is covered by the post-bump verification step inside the workflow itself. | WP-003 |
| release-train skill `--dry-run` | The skill is markdown; its proof is the `--dry-run` default-first-pass producing the right cumulative version + CHANGELOG preview against `_changeset.py` (WP-001 functions) without side effects. | WP-004 |
| version-check advisory behaviour | The guard's proof is that a plugin-diff-without-changeset **warns and exits 0** this cycle (advisory) — asserted by reading the workflow's exit semantics. | WP-005 |
| Bot can push the bump | **Throwaway verification** (WP-006) before relying on the train — a real bot push to a protected branch on a scratch branch/repo. | WP-006 |

**No mocks in the unit core.** `_changeset.py` is pure (no I/O beyond
reading/writing files in a tmp dir), so its tests use `tmp_path` directly — no
mocking, matching the existing `test_change_store.py` convention.

---

## Key design decisions (one ADR each)

| ADR | Decision | Why it's an ADR |
|---|---|---|
| [ADR-001](adrs/ADR-001-decouple-integration-from-release.md) | Decouple integration from release via changesets | Affects every component; the root architectural move (#66). |
| [ADR-002](adrs/ADR-002-tier-from-primitive.md) | Tier derived from the change primitive, not hand-set | Locks the tier-mapping policy; overridable per-changeset for the rare exception. |
| [ADR-003](adrs/ADR-003-dual-version-bump-scheme.md) | The bump touches **three** version values at one tier; tag = `v<marketplace metadata.version>` | The single most error-prone detail; reconciled from real repo state. |
| [ADR-004](adrs/ADR-004-gha-bump-authority-not-local-script.md) | The GHA is the one bump authority (not a local script); bash duplicates `_changeset.py` logic | The founder-chosen Option B; documents the accepted bash/Python duplication. |
| [ADR-005](adrs/ADR-005-changeset-yaml-contract-keystone.md) | `.changesets/README.md` is the producer/consumer contract; WP-001 lands first | CONTRACT_FIRST seam — everything reads/writes this shape. |
| [ADR-006](adrs/ADR-006-version-check-advisory-first.md) | version-check ships advisory-only this cycle; required is a later founder-gated step | Self-lockout avoidance is the load-bearing reason; the promotion is deliberately deferred. |

No existing ADR registry was found at `.context/{project}/INDEX.md` (no context
index exists for this repo), so these six start at ADR-001 with no collision
risk. ADR count (6) is within the tier-M maximum.

---

## Ambiguity resolved (where the spec met repo reality)

The spec is self-sufficient on intent, but two details required reconciling
against the live repo. Both are recorded here and in the ADRs:

1. **"Remove the manual version bump from the ship flow" (WP-2 / WP-002).**
   The current `/sulis:change ship` flow (`plugins/sulis/skills/change/SKILL.md`)
   ships to **`dev` only** and explicitly defers promote-to-`main`; it has **no
   manual bump step** to remove. The manual bump actually lives in the
   **`dev→main` promotion ceremony** — `git-workflow-standard.md` GIT-06 + the
   `promote-dev-to-main.yml` workflow_dispatch that takes a hand-typed `version`
   input. **Resolution:** WP-002 *adds* the changeset-write step to the ship
   flow (there is nothing to remove there); WP-007 retires the manual bump from
   the **promotion ceremony** (GIT-06 + the `version` input expectation), which
   is where it genuinely lives. WP-002's "remove the manual bump" is honoured by
   making the ship flow write only a changeset and explicitly *not* bump. See
   ADR-004.

2. **The dual-version scheme (WP-3 / WP-003).** Repo state shows the bump moves
   **three** values in lockstep at one tier: `plugin.json .version` (sulis
   0.77.x), `marketplace.json .plugins[name==sulis].version` (0.77.x), and
   `marketplace.json .metadata.version` (the umbrella 1.122.x). The git **tag**
   is `v<metadata.version>` (e.g. `v1.122.0` — confirmed: there is no `v0.77.0`
   tag; the umbrella version is the one tagged). The **CHANGELOG header** uses
   the **plugin** version (`## v0.77.0 — <date>`). honest-claude bumps only one
   value; Sulis bumps three. **Resolution:** ADR-003 pins the exact mapping and
   WP-001's `next_version` + WP-003's bump step encode all three + the tag rule.

---

## Bootstrapping sequence (MUST — from the spec, avoids self-lockout)

1. **WP-001 + WP-002 + WP-003 ship first** — the changeset writer + the bump
   authority exist BEFORE any enforcement, so changes start producing changesets
   and the bump authority is live.
2. **WP-006 lands with WP-003** — `main` protection configured so the bot can
   push the bump; the bot push is verified on a throwaway before reliance.
3. **WP-004 ships** — releases can now be cut from changesets.
4. **WP-005 ships advisory (warn-only)** — in-flight `change/*` branches without
   changesets don't break. Promotion to a **required** check is a separate,
   later, founder-gated step (next cycle), once the flow is reliably producing
   changesets.
5. **This change itself ships through the OLD flow (manual bump, one last
   time)** — the train isn't live yet. The NEXT release uses the train.

---

## Sizing Report

> Cross-references the right-sizing computation. No `SIZING.md` was pre-computed
> for this change; the numbers below were derived from the spec during this run
> and the tier confirmed against the spec's own "tier-L" self-label (see note).

| Metric | Value |
|---|---|
| **sFPC** | ~12 (ILF 1 changeset collection + EIF 1 GitHub API + EI/EO/EQ ~10 functions/operations) |
| **ASR count** | ~10 (≈6 NFR-shaped guards: determinism, collision-proofing, VERSION_DRIFT, post-bump verification, advisory-first, self-lockout avoidance; ≈2 integrations: GitHub Actions + gh CLI; ≈2 cross-cutting: version-check guard + branch protection) |
| **Computed tier** | **M** (sFPC 11-30, ASR 6-15) |
| **Spec self-label** | "tier-L" (spec frontmatter). The spec's L reflects *coordination* complexity (7 pieces, bootstrapping order, founder gates) rather than functional point count. Taking the higher tier per the right-sizing tie-break would read **L**; the artifact depth below is sized for the higher reading. |
| **Tier used for depth** | L-leaning M — full Form/Armor/Proof, 6 ADRs, 7 WPs. |
| **TDD length** | ~ within target for the chosen depth; no "why is this big?" circuit breaker triggered. |
| **ADRs produced** | 6 (within tier max; each clears the "affects >1 component OR locks a tech choice OR rejects a viable alternative" bar). |
| **Authoritative sources referenced (not restated)** | `WORK_PACKAGE_STANDARD.md` (WP shape), `git-workflow-standard.md` (GIT-06 ceremony, the false-green guardrail), the honest-claude inspiration sources, `_wpxlib.py` canonical INDEX header. |
| **Circuit breakers triggered** | None. |

---

## See also

- `.changes/release-train.SPEC.md` — the authoritative blueprint.
- `work-packages/INDEX.md` — the 7-WP dependency graph + build order.
- `work-packages/DECOMPOSE_VALIDATION.md` — proof of coverage of all 7 spec
  pieces + the bootstrapping order.
- honest-claude `.claude/skills/release-train/SKILL.md`, `.changesets/README.md`,
  `.github/workflows/{release-on-merge,version-check}.yml` — the inspiration.
