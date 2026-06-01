# SRD — Discover Project (mint a consumer-owned Project entity)

**Change:** CH-01KT1W · `change/create-discover-project` · primitive: create
**Date:** 2026-06-01
**Status:** draft v1 (autonomous SRD dispatch — open questions deferred to founder)
**Depends on:** CH-01KSZ4 `release-train-as-entities` (canonical Project + Workflow shape, Configuration Vocabulary section, blocking drift detector)
**Structural template:** `.specifications/release-train-as-entities/` — identical Path A pattern (canonical Workflow + Steps + Triggers + FailureModes + Tools + thin skill imperative + drift detector compliance)
**Execution path:** Path A — canonical-as-spec, imperative-as-implementation, drift-detector as the bridge

## Intent

Give fork-consumers (anyone cloning the marketplace template into their own repo) a way to mint their own Project entity automatically. Today this is hand-authored work: the consumer reads the Configuration Vocabulary section of the release-train SRD and writes a `.sulis/projects/<slug>.jsonld` by hand. This change replaces that friction with a canonical **discover-project Workflow** plus a thin skill that runs it.

The change is also the **n=2 dogfood of Path A**. Discovery itself is encoded as a canonical Workflow (Steps + Triggers + FailureModes + Tools); the skill prose is the imperative side; the (now-blocking) drift detector catches divergence at PR time. If Path A holds for a second non-trivial workflow, it holds.

**The one outcome:** *a consumer can run one command, answer at most a handful of questions, and have a working Project entity that the release-train Workflow can bind to — without reading the SRD.*

- **Deterministic phases** (Detect, Mint, Verify) consume zero LLM tokens.
- **Probabilistic Inference** is the only LLM-driven phase, bounded by NFR-002.
- **Human-Ask** surfaces only the genuinely ambiguous fields (Open Question 2 below — recommend fail-fast on missing entity rather than auto-routing).

## Why this is now

Three factors converged:

1. **release-train-as-entities shipped.** The Project entity schema, the Configuration Vocabulary, and the canonical Workflow shape are all stable on dev.
2. **The drift detector is blocking** (`7d666df extend: tighten-drift-gate`). Any discovery output that diverges from the canonical Workflow definition fails branch-CI. This is the safety rail the n=2 dogfood needs.
3. **Cross-WP identifier canonicalisation is enforced** (`f59fc36 extend: canonicalise-cross-wp-ids`). The P8 rubric check will catch any ULID-minting drift in the discovery Workflow's design.

There is no second consumer hitting the friction yet — but the marketplace itself is the consumer that exercises the path most often when adopting new plugins or moving plugins between repos.

---

## Stakeholders

- **Fork-consumer (the human running discovery)** — clones the marketplace, installs Sulis, runs the discover-project skill, answers questions, gets a working Project entity.
- **Founder (Iain)** — owns the discover-project Workflow definition + the skill prose; reviews changes via the drift detector.
- **Marketplace itself** — its own 4 Projects (sulis, sulis-brain, plugin-builder, investor-coach) stay at `plugins/sulis/instances/release-train/projects.jsonld` (marketplace-owned). Consumer Projects go to `.sulis/projects/<slug>.jsonld` (consumer-owned). Two ownership models; two paths.
- **release-train Workflow** — downstream consumer of the Project entity that discovery mints. The two Workflows are decoupled at the entity boundary.

---

## Use Cases

### UC-001 — First-time setup (greenfield consumer)

A consumer has just cloned a marketplace fork into their repo. They run `/sulis:discover-project` (or `/sulis:setup` — see Open Question 1). The skill:

1. Reads the repo root, primary branch, package manifests, existing CI workflows, and `.sulis/repo-contract.yml` if present (Detect phase, deterministic).
2. Proposes values for the Configuration Vocabulary fields (Infer phase, probabilistic, bounded by NFR-002).
3. Asks the consumer for the ambiguous fields — Project `name`, brand-scope decisions, anything the repo doesn't reveal (Ask phase, human).
4. Writes the Project entity at `.sulis/projects/<slug>.jsonld` (Mint phase, deterministic).
5. Runs the canonical drift detector on the new entity — confirms cross-references resolve (Verify phase, deterministic).

Outcome: a valid Project entity sits at `.sulis/projects/<slug>.jsonld`. The consumer can immediately invoke `/sulis:release-train` and have it bind to this Project.

### UC-002 — Re-discovery on an evolved repo

The consumer ran discovery six months ago. Since then their repo has gained a new sub-package, switched branch model, or added a deploy target. They run `/sulis:discover-project --update` (recommended re-discovery flag — see Open Question 5).

The skill detects the existing `.sulis/projects/<slug>.jsonld`, re-runs Detect + Infer, produces a **per-field diff** showing proposed changes. The consumer approves changes per-field; only approved fields are written back. Unapproved fields preserve their existing values.

### UC-003 — Monorepo with multiple Projects

The consumer has a monorepo with three distinct release units (e.g., a backend, a CLI, and a docs site). Running discovery once produces one Project. To mint a second, the consumer runs `/sulis:discover-project --path apps/cli` (or similar — the skill accepts a sub-path argument that scopes Detect to that directory and produces a sibling Project entity at `.sulis/projects/<sub-slug>.jsonld`).

The Detect phase respects the sub-path — it reads only manifests and CI under that path, never overwriting a sibling Project entity (covered by MUC-007 below).

### UC-004 — Non-git directory error

The consumer runs discovery in a directory that has no `.git/` and no git remote. Discovery cannot infer `source.repo` and cannot write a meaningful Project. The skill **fails fast** with a clear error: *"This directory is not a git repository. discover-project requires a git remote to mint a Project. Run `git init` and add a remote first, or specify `--source-repo <org/name>` explicitly."*

### UC-005 — Founder cancels mid-flow

The consumer starts discovery, gets to the Ask phase, decides they're not ready to commit (e.g., they want to think about the branch model first). They cancel (Ctrl-C or similar). The skill performs **partial state cleanup**: no `.sulis/projects/<slug>.jsonld` is written, no half-formed entity sits on disk. The skill exits cleanly with an idempotency guarantee — re-running the skill produces the same outcome as the cancelled run did (none).

### UC-006 — LLM-inference correction

The Infer phase proposes `deploy_target: github-release` but the consumer's project deploys to npm. In the Ask phase, the skill surfaces the inferred values and asks the consumer to confirm or override each one. The consumer overrides `deploy_target` to `npm-publish`. The override is recorded as the canonical value before Mint writes the entity. **No inferred value is written without explicit consumer confirmation.**

---

## Functional Requirements

### FR-001 — discover-project Workflow envelope

The change MUST author a canonical Workflow entity at `plugins/sulis/instances/discover-project/workflow.jsonld`. The Workflow has a deterministic ULID (proposed: `dna:workflow:01KT1WDSCVRWFW0000000000A` — exact ULID set by the TDD per the P8 cross-WP-id canonicalisation rubric). The Workflow binds to the marketplace tenant ULID `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` (same as release-train per ADR-001 of release-train-as-entities).

### FR-002 — Five canonical phases as Steps

The Workflow MUST contain Steps corresponding to the five phases:

| Phase | Mechanism | Steps (proposed names) |
|---|---|---|
| Detect | `deterministic` | `read-repo-root`, `read-package-manifests`, `read-ci-workflows`, `read-repo-contract` |
| Infer | `probabilistic` | `propose-configuration-values` |
| Ask | `human` | `confirm-or-override-inferences`, `gather-ambiguous-fields` |
| Mint | `deterministic` | `write-project-entity` |
| Verify | `deterministic` | `run-drift-detector-on-mint` |

Exact Step names, ULIDs, and ordering are the TDD's responsibility. The constraint here is the phase shape — 4 deterministic phases bracketing 1 probabilistic phase, with the human gate between Infer and Mint.

### FR-003 — Triggers

The Workflow MUST declare at least one Trigger:

- **Founder-invoked** — operator runs `/sulis:discover-project` (or `/sulis:setup` — Open Question 1). Default mode: first-time discovery.
- **Founder-invoked with --update** — re-discovery mode (UC-002). Skill detects existing entity and runs the diff flow.

Optional (deferred to v2): an `auto-suggest` Trigger that fires when any Sulis command runs in a consumer repo with no `.sulis/projects/<slug>.jsonld` — produces a clear error pointing at `/sulis:discover-project`. **Recommended: fail-fast with clear error, do NOT auto-route** (see Open Question 2).

### FR-004 — FailureModes

The Workflow MUST declare FailureModes covering at least:

- `non-git-directory` (UC-004): Detect phase fails because no git remote exists. Recovery: surface clear error + suggested fix.
- `partial-write` (UC-005): consumer cancels mid-flow. Recovery: ensure no partial entity persists.
- `entity-already-exists` (MUC-003): consumer runs discovery in a repo that already has the Project entity. Recovery: refuse to overwrite without `--update` flag.
- `inferred-value-rejected` (UC-006): consumer overrides an inferred value. Recovery: record the override before mint.
- `drift-verify-fails` (FR-008 below): the minted entity fails the post-mint drift check. Recovery: roll back the mint, surface the diff.
- `token-budget-exceeded` (MUC-008): probabilistic step exceeds NFR-002. Recovery: fall back to asking the consumer for all fields (no inferences).

### FR-005 — Tools

The Workflow MUST bind to typed deterministic Tools for:

- Git remote read (`git remote get-url origin` equivalent).
- File-system read (manifests, CI workflows, repo-contract).
- JSON-LD write (the entity-emitter — likely reusable from existing entity-emitter skill).
- Drift detector invocation (the existing tool from release-train, scoped to the newly-minted entity).

Tool ULIDs follow the same canonical-ULID rubric as release-train Tools (P8 rubric).

### FR-006 — Skill imperative

The change MUST author a skill (likely at `plugins/sulis/skills/discover-project/SKILL.md` or `plugins/sulis/skills/setup/SKILL.md` per Open Question 1). The skill is the imperative side that conforms to the canonical Workflow. Skill prose follows the existing convention (front matter + sections).

### FR-007 — Output location and path safety

The skill MUST write Project entities only to `.sulis/projects/<slug>.jsonld` in the consuming repo. It MUST create the `.sulis/projects/` directory if missing. It MUST NOT write to any other location — including no writes to `plugins/sulis/instances/release-train/projects.jsonld` (which is marketplace-owned per ADR-004 of release-train-as-entities).

### FR-008 — Post-mint drift verification

After the Mint phase writes the Project entity, the Verify phase MUST invoke the canonical drift detector on the new entity. The drift check confirms:

- `release_workflow_ref` points to an existing Workflow ULID (the marketplace's release-train Workflow).
- `belongs_to_tenant` resolves to a known tenant (the consumer's own tenant per Open Question 4, or the marketplace tenant if shared).
- All Configuration Vocabulary fields are populated to schema.

If the drift check fails, the mint is rolled back and the consumer sees the specific failure.

### FR-009 — Re-discovery diff flow

`--update` mode MUST produce a per-field diff between the existing entity and the proposed re-discovery output. For each field that would change, the consumer sees old value, proposed new value, and approves or rejects the change. Only approved fields are written. Unapproved fields retain existing values.

### FR-010 — Monorepo sub-path support

The skill MUST accept an optional `--path <sub-path>` argument that scopes Detect to that sub-directory and writes the resulting Project entity to a slug derived from the sub-path. If a Project with the derived slug already exists, FR-008-style refusal applies (MUC-007).

### FR-011 — Confirmation gate

The Mint phase MUST be preceded by an explicit consumer confirmation step. The consumer sees the full proposed Project entity in human-readable form and explicitly approves before any write occurs. No inferred value is persisted without confirmation.

### FR-012 — Idempotent failure

If discovery fails at any step (consumer cancels, non-git directory, token budget exceeded, drift verify fails), the on-disk state MUST be identical to what it was before discovery ran. No partial entities, no half-formed directories beyond the `.sulis/projects/` directory itself (which is harmless if empty).

---

## Non-Functional Requirements

### NFR-001 — Wall-time budget

A first-time discovery run on a typical repo (single Project, GitHub remote, standard package manifest) MUST complete in ≤5 minutes of wall-clock time including all consumer prompts. The probabilistic Infer phase alone MUST complete in ≤90 seconds.

### NFR-002 — Token budget

The probabilistic Infer phase MUST consume ≤10,000 tokens per discovery run (input + output combined). Exceeding this triggers the `token-budget-exceeded` FailureMode (MUC-008) which falls back to asking the consumer for all fields. *Note: the 10k figure is a starting estimate from release-train; pin via dogfood — see Open Question 3.*

### NFR-003 — Deterministic re-run

Running discovery twice on an unchanged repo MUST produce byte-identical Project entities. The probabilistic phase introduces no non-determinism that survives to the written entity — all probabilistic outputs are either confirmed by the consumer (becoming canonical) or rejected (excluded from the entity).

### NFR-004 — Safety: never write outside the entity path

Discovery MUST NOT write to any path other than `.sulis/projects/<slug>.jsonld` (and `mkdir -p .sulis/projects/` if missing) without explicit consumer confirmation. Specifically: no writes to `.git/`, no writes to `package.json`, no writes to `.sulis/repo-contract.yml`, no writes to the marketplace's own `plugins/sulis/instances/release-train/projects.jsonld`.

### NFR-005 — Drift visibility

The Project entity produced by discovery MUST pass the existing blocking drift gate. If the canonical discover-project Workflow definition diverges from the skill's imperative prose, the drift detector blocks the PR. This is the n=2 dogfood: the same drift detector that guards release-train guards discover-project.

### NFR-006 — Graceful degradation under no LLM

If the LLM is unavailable (network issue, rate limit, configuration error), discovery MUST fall back to the all-human-ask flow (skip the Infer phase entirely, ask the consumer for all Configuration Vocabulary fields). The consumer can still mint a valid Project, just with more typing.

---

## Misuse Cases

See `MISUSE_CASES.md` for the full list. Summary:

| ID | Misuse case | System response (negative requirement) |
|---|---|---|
| MUC-001 | Run discovery in non-git directory | MUST fail-fast with explicit error; MUST NOT mint anything |
| MUC-002 | Founder cancels mid-flow | MUST clean up partial state; MUST be idempotent on re-run |
| MUC-003 | Entity already exists at target path | MUST refuse to overwrite without explicit `--update` flag |
| MUC-004 | LLM proposes incorrect deploy target | MUST require explicit consumer confirmation before mint |
| MUC-005 | Project references unknown Workflow ULID | Drift detector MUST catch and block at PR time |
| MUC-006 | Repo has no git remote | MUST fail-fast; MUST surface `--source-repo` override |
| MUC-007 | Monorepo collision — overwrites sibling Project | MUST refuse to overwrite without explicit `--update <slug>` |
| MUC-008 | Token budget exceeded on Infer phase | MUST fall back to all-human-ask; MUST surface why |

---

## Negative Requirements (per UC)

- **UC-001** — Discovery MUST NOT silently overwrite an existing `.sulis/projects/<slug>.jsonld`. MUST NOT mint a tenant ULID without explicit consumer confirmation or a documented derivation recipe. MUST NOT write any inferred value to disk without consumer approval.
- **UC-002** — `--update` MUST NOT bulk-replace the existing entity. MUST produce a per-field diff. MUST preserve unapproved fields.
- **UC-003** — Monorepo discovery MUST NOT touch sibling Project entities. The `--path` scope is a hard boundary.
- **UC-004** — Discovery MUST NOT proceed past Detect without a resolvable `source.repo`. No defaults, no guesses.
- **UC-005** — Cancellation MUST NOT leave any partial entity, lock file, or half-written directory beyond an empty `.sulis/projects/` directory.
- **UC-006** — Inferred values MUST NOT be treated as canonical until the consumer has seen and approved them in the Ask phase.

---

## Glossary

See `GLOSSARY.md` for the full locked vocabulary. Key terms:

- **Consuming repo** — A fork-consumer's own repository, distinct from the marketplace.
- **Discovery** — The act of running the discover-project Workflow.
- **Discovery run** — One execution of the Workflow.
- **Project entity** — The canonical output: `.sulis/projects/<slug>.jsonld`.
- **First-time setup** — Discovery in a repo with no existing Project entity.
- **Re-discovery** — Discovery in a repo with an existing Project entity (uses `--update`).
- **Monorepo Project** — One of multiple Projects in a single repo, scoped via `--path`.

---

## Open Questions

These are not resolved autonomously; the founder owns them. The TDD or the consuming session should pin them.

### OQ-1 — Skill name: `/sulis:setup` or `/sulis:discover-project`?

Both are plausible. `setup` is more discoverable for a first-time consumer who doesn't know the vocabulary. `discover-project` is more descriptive and matches the canonical Workflow name (the entity name should drive the skill name per Path A). **Recommendation: `/sulis:discover-project`** — Path A says canonical drives imperative; a generic `setup` blurs that. The TDD can alias `/sulis:setup` to it if discoverability matters.

### OQ-2 — Auto-prompt on missing entity?

When a founder runs any sulis command in a repo with no `.sulis/projects/<slug>.jsonld`, should we auto-route to discovery, or fail with a clear error pointing at discovery? **Recommendation: fail fast with clear error.** Auto-routing is magic; per the marketplace's "governance over mystification" principle (per release-train ADR-001), the founder should always know what's about to happen.

### OQ-3 — Probabilistic step token budget — 10k or a different number?

10k is a starting estimate from release-train (NFR-010 there). Worth pinning a specific number via dogfood once the skill exists. **Recommendation: ship at 10k, instrument, adjust at v1.1 with observed data.**

### OQ-4 — Tenant ULID derivation for consumer Projects

Should each consumer have its own deterministically-derived tenant ULID (e.g., `SHA256("tenant-name:" + <consumer-repo-org/name>)` → Crockford base32 → first 26 chars), or do all consumer Projects share the marketplace tenant `6XBZ93FSHN5TRX8MCS5R66FNCM`? Affects ownership model + drift detection semantics + cross-repo entity resolution.

**Recommendation: per-consumer derived tenant ULID.** The marketplace's 4 Projects share the marketplace tenant (they ARE the marketplace). Consumer Projects belong to a consumer tenant. The drift detector treats cross-tenant refs as boundaries (which is correct — a consumer's Project entity references the marketplace's Workflow ULID across a tenant boundary by design).

Proposed derivation recipe: `SHA256("tenant-name:" + <consumer-repo-org-slash-name>)` → take first 130 bits → Crockford base32 → 26 chars. This is **deterministic**, **collision-resistant**, and **publicly verifiable** (anyone with the repo URL can compute the same ULID).

### OQ-5 — Re-discovery semantics

`/sulis:discover-project --update` — does it overwrite, prompt per-field, or produce a diff for founder review? **Recommendation: per-field diff with explicit approval.** Matches "founder owns mints" governance and avoids silent drift between re-discovery runs.

---

## Out of Scope

- Multi-project discovery wizard (UI for picking which sub-project in a monorepo) — covered by `--path` argument; no wizard.
- Auto-detection of WHICH marketplace plugin should be installed (assume marketplace is already installed).
- Migration from hand-authored Project entities to discovery-generated ones — post-v1.
- Cross-tenant federation (consumer Projects from multiple marketplace tenants in one repo) — post-v1; requires ontology work in sulis-brain first.
- Env-init (sibling discovery family member) — separate SRD when triggered.

---

## Acceptance

This SRD is **accepted** when the founder pins the five Open Questions (OQ-1..OQ-5) and the TDD picks up. The five resolved values become inputs to the TDD; the SRD itself does not need to be re-litigated post-pinning.

A passing implementation MUST:

1. Author the canonical entities (`workflow.jsonld`, `steps.jsonld`, `triggers.jsonld`, `failuremodes.jsonld`, `tools.jsonld`) under `plugins/sulis/instances/discover-project/`.
2. Author the imperative skill at the resolved location (per OQ-1).
3. Pass the blocking drift detector at PR time.
4. Demonstrate a working first-time setup (UC-001) on at least one non-marketplace consumer repo (dogfood).
5. Demonstrate re-discovery (UC-002) on the dogfood repo after a deliberate change.
