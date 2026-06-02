# SRD — Encode release-train as canonical entities

**Change:** CH-01KSZ4 · `change/create-release-train-as-entities` · primitive: create
**Date:** 2026-06-01
**Status:** draft v2 (Path A reframe + configuration vocabulary)
**Depends on:** sulis-brain v0.9.0+ (foundation v0.6.0 — Project entity, Workflow.for_project, Tool.implementation_kind=workflow_dispatch, LifecycleRun v2.1.0, DerivedArtifact, execute-workflow agent)
**Structural template:** `sulis-brain/.specifications/business-dna/instances/sync-narrative-docs/` (closest precedent — 1 Workflow + 7 Steps + 3 Triggers + 6 FailureModes + 4 DerivedArtifacts composing existing foundation primitives)
**Execution path:** Path A — canonical-as-spec, imperative-as-implementation, drift-detector as the bridge

## Intent

Encode the marketplace's release pipeline (today: imperative
`release-on-merge.yml` + skill prose in `/sulis:release-train`) as
canonical **Workflow + Step + Trigger + FailureMode + Project + Tool**
entities in the brain. The canonical is the **specification of truth**
for what release-train does. The imperative `release-on-merge.yml`
remains the **implementation** that conforms. A **drift detector**
(canonical-vs-implementation) is the structural bridge that prevents
silent divergence.

**The one outcome:** *deterministic, cost-effective, reliable execution
of release workflows.*

- **Deterministic** because the imperative implementation runs the same
  way every time (it has always done so; the canonical formalises what
  "the same way" means).
- **Cost-effective** because the imperative path uses zero LLM tokens
  (CI bash, as today). The dry-run preview can optionally invoke
  `execute-workflow` to walk the canonical with the LLM — once per
  release decision, not per CI run.
- **Reliable** because the canonical surfaces missing FailureModes
  before the defect is hit, and the drift detector catches imperative
  divergence at PR time.

**The deliverable** is not a custom skill or runtime. Per L26/L27, it's
a **canonical Workflow instance + a thin wrapper that points at it**.
The brain ships the executor; we ship the encoding + the drift-detector
+ a small extension to the existing skill for the dry-run mode.

## Why this is now

Today (2026-06-01) we lived through three latent defects in one release
attempt — YAML parse error, loop-guard pattern collision, GH-token tag
push not triggering release-prod. Each, recast as a Workflow, maps to a
missing **FailureMode** entity. Declarative encoding makes the gap
structurally visible before the defect is hit. The drift detector
makes silent imperative divergence loud at CI time.

This is also the first dogfood of the brain's general workflow runner
**on a non-minting workflow**, even if (per Path A) only for the
dry-run preview.

---

## Stakeholders

- **Founder (Iain)** — invokes `/sulis:release-train`, reviews + merges
  release PRs, acts as human gate at confirmation steps.
- **Bot (`github-actions[bot]`)** — auto-runs `release-on-merge.yml` on
  merge to main; **unchanged** under Path A — same imperative pipeline
  as today, plus the new drift-detector CI step.
- **Downstream consumers** — install marketplace plugins; **unaffected**.
- **Future fork-and-adapt consumers** — read the Configuration
  Vocabulary section to populate their own Project entity by hand
  until the sibling discovery Workflow ships.

---

## Use Cases

### UC-001 — Founder cuts a release (dry-run preview, then ship)

The founder invokes `/sulis:release-train`. The skill (extended) runs in two modes:

- **Default — dry-run with canonical walk.** Invokes
  `/sulis-brain:execute-workflow plugins/sulis/instances/release-train/`
  scoped to the relevant Project. LLM walks the canonical Workflow,
  emits a per-Step preview, surfaces the structural verdict and the
  draft PR body + CHANGELOG. Token-budgeted (NFR-001).
- **Ship — operator confirms; imperative path runs.** Identical to
  today: the skill drafts + opens the release PR; `release-on-merge.yml`
  fires on merge; the imperative bash bumps + tags + publishes.

### UC-002 — Bot completes a release on PR merge

A founder-merged release PR lands on main. The release-on-merge
trigger fires; the workflow runs the imperative bash. **Unchanged from
today.** The drift detector runs as a CI step on the PR before merge.

### UC-003 — Gap analysis (read-only)

An agent (or the founder via `/sulis:dashboard` or a brain query)
inspects the `release-train` Workflow + its Steps + the catalogue of
FailureModes. "What could go wrong with this release path?" is
answered structurally: enumerate `Step.handles_failures`, surface any
Step that has no FailureMode coverage, flag Steps whose mechanism is
`probabilistic` without a deterministic fallback.

### UC-004 — Fork-and-adapt

A consumer forks the marketplace with a different branch policy. They
read the **Configuration Vocabulary** + the marketplace's worked-example
Project instances. They author their own Project instance with their
values. The Workflow definition is unchanged — Steps reference Project
fields via `for_project`. (Future sibling: `project-discovery`.)

### UC-005 — New FailureMode mint

A new release defect surfaces. It maps to a failure type not yet in the
catalogue. The founder mints a new FailureMode instance, links it to
the relevant Step's `handles_failures`. The drift detector flags the
YAML as missing a recovery path → YAML updated to conform.

### UC-006 — Drift catch at PR time

A developer modifies `release-on-merge.yml` without updating the
canonical. The drift detector runs at PR time and fails: "Step X in
the YAML doesn't match canonical workflow.jsonld. Either update the
canonical or revert the YAML." Conformance restored before merge.

---

## Functional Requirements

### Entity authoring

- **FR-001 — Project instances exist for each marketplace plugin.**
  Hand-authored at
  `plugins/sulis/instances/release-train/projects.jsonld`. Initially:
  `sulis`, `sulis-brain`, `plugin-builder`, `investor-coach`. Each has
  `source.path`, `version_files[]`, `branch_policy`,
  `belongs_to_product_ref="sulis-plugins-marketplace"`,
  `release_workflow_ref` pointing at the `release-train` Workflow.

- **FR-002 — One `release-train` Workflow instance exists** at
  `plugins/sulis/instances/release-train/workflow.jsonld`. Structural
  template: `sync-narrative-docs`. `for_project` is null on the
  definition; bound per-invocation. Cycle-tolerant per JT-7 (e.g.
  PR-conflicts → back-merge → retry-from-open-pr).

  **DEFERRED to v2:** A separate `marketplace-release` Workflow that
  composes per-Project release-trains via `Tool.workflow_dispatch`.
  Path A relies on `release-on-merge.yml`'s existing
  `marketplace.plugins[]` iteration. Composition via canonical
  Workflows requires a deterministic runner (Path C); out of scope.

### Steps in `release-train`

Each Step has `mechanism`, `input_artifacts`, `output_artifacts`,
`tool_ref` (where applicable), `handles_failures`.

| # | Name | Mechanism | Tool ref | Acceptance |
|---|---|---|---|---|
| 1 | detect-pending-changesets | deterministic | `_changeset.read_changesets` | Returns the list or empty (signaling skip). |
| 2 | preflight-version-drift | deterministic | `_changeset.compare_version_files` | Plugin.json == marketplace.json entry, else abort. |
| 3 | preflight-cross-branch-drift | deterministic | `git.compare_branch_versions` | Source vs target versions match, else abort with back-integration instructions. |
| 4 | compute-next-version | deterministic | `_changeset.cumulative_tier` + `next_version` | Tier in {patch, minor, major, null}; new versions computed. |
| 5 | draft-pr-body-and-changelog | mixed | LLM prose + `_changeset.summarise` | PR body + CHANGELOG entry drafted. Token-budgeted. |
| 6 | open-release-pr | side-effect | `gh-pr-create` | PR URL returned. |
| 7 | wait-for-checks-and-mergeability | deterministic | `gh-pr-checks-watch` + `gh-pr-mergeability` | All checks pass + mergeable=CLEAN, else abort/escalate. |
| 8 | gate-founder-confirmation | human | (agent prompts) | Founder explicit yes / no. |
| 9 | squash-merge | side-effect | `gh-pr-merge` (mode from `Project.branch_policy`) | PR merged; head commit on target_branch. |
| 10 | bump-version-files | side-effect | `update-version-file` (one call per `Project.version_files[]`) | All files written. |
| 11 | write-changelog-entry | side-effect | `prepend-changelog` | CHANGELOG.md has new section. |
| 12 | commit-bump-as-bot | side-effect | `git-commit` (author=github-actions[bot]) | Bot commit lands. |
| 13 | tag-and-push | side-effect | `git-tag` + `git-push-tag` | Tag pushed per branch_policy format. |
| 14 | publish-github-release | side-effect | `gh-release-create` | GitHub Release published. |
| 15 | emit-release-entity | side-effect | `sulis-emit-release` | Release entity persisted. |

- **FR-004 — Step granularity stays coarse.** Each Step is a coherent
  unit; agent latitude inside; no atomic "EXECUTE THIS NOW" steps.

### Tools

- **FR-005 — Tool instances exist for every Step's tool_ref**, authored
  at `plugins/sulis/instances/release-train/tools.jsonld`. Under Path A,
  Tools are **documentation entities** describing what the imperative
  bash does. Three purposes:
  1. Drift detector validates the YAML implements each Tool's contract.
  2. Dry-run preview reads them when LLM walks the canonical.
  3. Path C (future deterministic runner) calls them directly.

- **FR-006 — Each Tool declares typed inputs + outputs + error catalogue.**
  Implementation kind matches reality:
  - `gh-pr-*` / `git-*` → `subprocess`
  - `_changeset.*` → `python_import`
  - `update-version-file` / `prepend-changelog` → `python_import`
  - `sulis-emit-release` → `subprocess`

### Triggers + FailureModes

- **FR-007 — Trigger instances cover the entry points.**
  `manual-release-train-invocation` (founder runs `/sulis:release-train`),
  `pull-request-merged-to-main` (release-on-merge.yml fires).

- **FR-008 — FailureMode catalogue covers today's known defects** at
  `plugins/sulis/instances/release-train/failuremodes.jsonld`:
  - `release-pr-conflicts-with-target-at-merge` → escalate
  - `workflow-yaml-fails-to-parse` → abort + alert (CH-01KSYZ)
  - `loop-guard-matches-founder-pr` → abort + correct (CH-01KSZ1)
  - `bot-tag-doesnt-trigger-release-prod` → fallback
  - `pr-checks-fail` → abort + surface failure
  - `pr-open-but-mergeability-stuck` → escalate to founder
  - `no-changesets-pending` → terminate-success (admin/docs-only)

- **FR-009 — Each FailureMode's recovery_strategy is declarative.**
  Strategies in {retry, compensate, escalate, abort, manual-review,
  fallback}. Steps reference FailureModes via `handles_failures[]`.

### Invocation + drift-detector

- **FR-010 — DEFERRED to v2: composition via `workflow_dispatch`.**
  Path A's runtime composition lives in `release-on-merge.yml`. Lift
  when Path C lands.

- **FR-011 — `/sulis:release-train --dry-run` (default) walks the
  canonical.** Skill resolves the Project, invokes
  `/sulis-brain:execute-workflow plugins/sulis/instances/release-train/`
  with `for_project` bound, returns the preview. Non-dry-run continues
  to use the imperative path. Skill prose extension ≤ 30 lines added
  on top of today's ~440-line skill.

- **FR-012 — `release-on-merge.yml` is the canonical's implementation.**
  Stays imperative (~300 lines). MUST conform to the canonical (every
  Step has a corresponding action; every FailureMode has a recovery
  path). Conformance verified by FR-015.

- **FR-013 — DEFERRED to v2: LifecycleRun emission at imperative-Step
  boundaries.** Low-effort follow-up to add `sulis-emit-lifecyclerun`
  calls inside `release-on-merge.yml` at Step boundaries. Sibling change.

- **FR-014 — DEFERRED to v2: run-record artifact.** Awaits FR-013.

- **FR-015 — Canonical-vs-implementation drift detector** (load-bearing).
  Script at `plugins/sulis/scripts/check-canonical-drift.py` + CI step
  in `branch-ci.yml` that:
  1. Reads `plugins/sulis/instances/release-train/{workflow,steps,triggers,failuremodes,tools}.jsonld`.
  2. Parses `release-on-merge.yml` + relevant skill prose.
  3. Asserts: every Step in canonical has an action in the YAML (by
     annotation `# canonical:step:<step-name>`); every FailureMode in
     `Step.handles_failures` has a recovery code path (annotation-matched).
  4. Fails the build on drift; PR cannot merge.
  Annotation-driven — avoid pattern-matching on bash content (fragile).

- **FR-016 — Configuration Vocabulary section published in the SRD**
  (this document). Authoritative list of every Project field +
  state_contract variable. Reference for fork-and-adapt consumers
  (UC-004) until the discovery sibling ships.

---

## Non-Functional Requirements

- **NFR-001 — Token cost (dry-run only).** Normal dry-run uses ≤ Xk
  tokens. Baseline measured before drift detector ships; budget at 80%
  of measured first run. **Imperative path is zero-token.**

- **NFR-002 — Determinism (imperative path).** Same Project + same
  changesets + same target_branch state → identical computed version.

- **NFR-003 — Cycle tolerance (canonical Workflow).** PR-conflicts
  back-merge → retry from open-pr. The imperative YAML implements
  the same cycles.

- **NFR-004 — Replay-ability via LifecycleRun.** DEFERRED to v2.

- **NFR-005 — Failure isolation.** DEFERRED with FR-010; meanwhile
  the YAML's `marketplace.plugins[]` iteration already isolates per-
  plugin failures.

- **NFR-006 — Observability.** Drift-detector failures are
  founder-readable (named Step + named FailureMode that diverged).
  Per-Step LifecycleRun deferred with FR-013.

- **NFR-007 — Branch-policy portability.** Switching a Project's
  `branch_policy` requires editing only the Project entity. (Under
  Path A, the imperative YAML still needs editing — the drift
  detector catches the gap.)

- **NFR-008 — Tool reuse.** Tool catalogue is per-marketplace-tenant.
  Same Tool referenced across multiple Workflows.

- **NFR-009 — Audit-grade artifacts.** Each release produces
  CHANGELOG entry + GitHub Release + Release entity (already in
  place). LifecycleRun journal deferred.

- **NFR-010 — Token budget on probabilistic Steps.** Step 5 declares
  explicit token budget in `mechanism_detail`. Exceeding fires
  `probabilistic-step-token-budget-exceeded` → fallback to
  deterministic CHANGELOG-from-template draft.

---

## Misuse Cases

- **MUC-001 — Coercive prompt style** (ae's anti-pattern). Out of
  scope. Steps describe what they do without commanding the agent.

- **MUC-002 — Workflow updated but imperative remnants not.** Defended
  by FR-015 (drift detector).

- **MUC-003 — Tool implementation changes but schema doesn't.**
  Defenses: Tool versioning + schema-validated tests + drift detector
  annotation refresh in PR review.

- **MUC-004 — Dispatch failure isolation breach.** DEFERRED with FR-010.

- **MUC-005 — Stale Tool catalogue.** Fork uses Tools not in their
  tenant's catalogue. Defense: startup-time Tool-existence check in
  dry-run mode; clear error if `tool_ref` doesn't resolve.

- **MUC-006 — Probabilistic Step burns the cost budget.** Defended by
  NFR-010 + FailureMode.

- **MUC-007 — Founder confirmation gate skipped.** Defended by
  `mechanism=human` Steps cannot be auto-skipped; retries restart
  from the most recent non-human-Step boundary.

- **MUC-008 — Project entity inconsistent with marketplace.json.**
  Defended by a `validate-projects` precondition + drift detector.

- **MUC-009 — Imperative drifts silently from canonical** (new).
  Without FR-015, Path A degrades to documentation that decays. The
  drift detector is the structural defense; this MUC names the failure
  that motivates FR-015.

- **MUC-010 — Fork-consumer can't easily populate Project values**
  (new). Defenses:
  - The Configuration Vocabulary section (below).
  - The marketplace's hand-authored Project instances as worked examples.
  - **Future:** `project-discovery` sibling Workflow.

- **MUC-011 — Abstracting on n=1.** Pre-minting Tools / Workflows /
  FailureModes for variations that don't exist yet. Defense: L13
  honoured — scope to sulis-plugins only; lift at n=2 evidence.

---

## Configuration Vocabulary

**The authoritative list of every variable the release-train Workflow
consumes.** Fork-consumers read this to populate their own Project
instance. Future `project-discovery` Workflow automates this.

### Project entity fields (per DR-016)

| Field | Type | Description | Example (sulis Project) |
|---|---|---|---|
| `name` | string | The release unit's name. | `"sulis"` |
| `belongs_to_tenant` | dna:tenant ref | Tenant that owns this Project. | `dna:tenant:01JA0AAA...` |
| `type` | enum | One of {application, library, service, plugin, website, model, brand-assets, other}. | `"plugin"` |
| `source.repo` | string | GitHub-shorthand repo identifier. | `"sulis-ai/agents"` |
| `source.path` | string | Path within the repo. Empty = repo-root. | `"plugins/sulis"` |
| `source.primary_branch` | string | Branch where releases land. | `"main"` |
| `version_files[]` | string[] | Paths carrying version strings. Order matters (first = canonical). | `["plugins/sulis/.claude-plugin/plugin.json", ".claude-plugin/marketplace.json"]` |
| `branch_policy` | enum | One of {trunk, gitflow-dev-main, gitlab-pre-prod, custom}. | `"gitflow-dev-main"` |
| `belongs_to_product_ref` | string | Product this Project belongs to. | `"sulis-plugins-marketplace"` |
| `depends_on[]` | dna:project[] | Projects this one depends on. | `[]` |
| `consumed_by[]` | dna:project[] | Projects that depend on this one. | `[]` |
| `release_workflow_ref` | dna:workflow | Release Workflow definition this Project uses. | `dna:workflow:01KT0RELEASETRAINDEFINITN` |

### state_contract variables (bound at invocation)

| Variable | Type | Source | Default for sulis-plugins-marketplace |
|---|---|---|---|
| `target_branch` | string | Project.source.primary_branch | `"main"` |
| `source_branch` | string | If branch_policy=gitflow-dev-main → `"dev"`; else target | `"dev"` |
| `merge_strategy` | enum {squash, merge, rebase, ff-only} | Project-level (future field) | `"squash"` |
| `tag_format` | string template | Project-level (future field) | `"v{umbrella_version}"` |
| `confirmation_required` | bool | Project-level | `true` |
| `release_artifact_kind` | enum {github_release, npm_publish, oci_image, signed_binary, none} | Project.type-derived | `"github_release"` |
| `ci_provider` | enum {github_actions, gitlab_ci, bitbucket, internal} | Auto-detected | `"github_actions"` |
| `changeset_dir` | path | Convention | `".changesets/"` |
| `changelog_path` | path | Convention | `"plugins/sulis/CHANGELOG.md"` |
| `pr_title_format` | string template | Convention | `"release: sulis v{plugin_version} ({tier})"` |
| `loop_guard_actor` | string | Convention | `"github-actions[bot]"` |

### Step-bound runtime outputs (propagated through state)

| Variable | Type | Source Step | Used by |
|---|---|---|---|
| `pending_changesets[]` | yaml[] | detect-pending-changesets | compute-next-version, draft-pr-body |
| `tier` | enum | compute-next-version | draft-pr-body, bump, tag |
| `next_plugin_version` | semver | compute-next-version | bump, write-changelog, tag |
| `next_umbrella_version` | semver | compute-next-version | bump (marketplace.json), tag |
| `pr_url` | url | open-release-pr | wait-for-checks, gate-confirmation |
| `merge_sha` | sha | squash-merge | tag-and-push |
| `tag_pushed` | bool | tag-and-push | publish-github-release |
| `release_url` | url | publish-github-release | emit-release-entity |

### Tool ref resolution (per consumer)

The release-train Workflow references Tools by `dna:tool:<ulid>` IDs.
Each consumer's Tool catalogue is **tenant-scoped**. GitHub-based
consumers: `gh-*` Tools. GitLab-based consumers (future): `gl-*` Tools.
Fork-and-adapt requires either reusing the marketplace's GitHub Tool
catalogue (if also on GitHub) or authoring an equivalent for the
consumer's stack.

---

## Future: discovery sibling

A `project-discovery` Workflow (sibling change, deferred) automates
the population of a Project entity instance for any consumer:

- **Trigger:** operator invokes (e.g.) `/sulis:discover-project`.
- **Steps (sketch):** detect-git-remote → parse-git-config →
  scan-for-version-files → infer-branch-policy (mixed; confirm with
  operator) → select-tag-format (human) → select-confirmation-gate
  (human) → detect-ci-provider → propose-tool-bindings (mixed) →
  write-project-instance.
- **Outputs:** populated Project entity at the right location + a
  sibling Tool-binding manifest if non-standard stack.

**Why deferred:**
- n=1 today. Per L13, don't pre-build the abstraction.
- This change's Project instances can be hand-authored.
- Once it exists, it serves env-init too — discovery is a *family*
  of Workflows; release-train Project discovery is one member.

**Trigger to build it:** A second consumer forks the marketplace AND
hits the manual-Project-authoring friction. Or env-init lands as a
sibling SRD and shares the primitive.

---

## Glossary

- **Project** — release-unit entity (foundation v0.5.0).
- **Workflow** — cycle-tolerant graph of Steps. Scoped via `for_project`.
- **Step** — one node; carries mechanism, tool_ref, handles_failures.
- **Tool** — typed deterministic operation. Under Path A, also a
  documentation entity.
- **Trigger** — what fires a Workflow run.
- **FailureMode** — FMEA-grounded recovery declaration.
- **DerivedArtifact** — entity (DR-019); future use for CHANGELOG +
  Release notes provenance.
- **LifecycleRun** — per-Step execution event (deferred to v2).
- **execute-workflow** — the brain's LLM-driven workflow runner (v0.9.0).
- **release-train** — the per-Project release Workflow defined here.
- **Path A / B / C** — execution strategies. This SRD scopes Path A.
- **Drift detector** — CI check verifying the imperative implementation
  conforms to the canonical.
- **state_contract** — Workflow field declaring typed state variables.
- **Configuration Vocabulary** — section of this SRD listing every
  Project + state_contract variable for fork-consumer reference.

---

## Open Questions

1. **Drift detector annotation format.** `# canonical:step:<name>` per
   step boundary, OR a sidecar `release-on-merge.yml.canonical-map.json`.
   Design-pass decision.

2. **Tool minting fidelity for v1.** Stub all ~17 Tools with names +
   minimal `implementation_detail`, OR fully populate the 5-6
   primary Tools and stub the rest? Recommendation: fully populate
   primaries; rest stubbed with `state: draft`.

3. **Token-cost baseline measurement.** Measure one current dry-run
   for input/output tokens, set NFR-001's budget at 80%. Pre-design;
   can be done in parallel.

4. **DerivedArtifact adoption.** Worth the extra entities for
   CHANGELOG + Release-notes provenance, or defer? Recommendation:
   defer to v2.

5. **Composition cycle documentation.** `Workflow.for_project ↔
   Project.release_workflow_ref` is intentional per L25. Already
   documented in DR-017; reference here suffices.

---

## Acceptance

This SRD is accepted when:

1. Every FR-NN (excluding DEFERRALs) has a corresponding entity
   instance under `plugins/sulis/instances/release-train/`
   (workflow.jsonld, steps.jsonld, triggers.jsonld,
   failuremodes.jsonld, tools.jsonld, projects.jsonld).
2. The drift detector (FR-015) runs in `branch-ci.yml` and catches a
   deliberate canonical-vs-YAML divergence in a test fixture.
3. `/sulis:release-train --dry-run` walks the canonical via
   `/sulis-brain:execute-workflow` and produces a founder-readable
   preview within the NFR-001 token budget.
4. Today's three latent defects are each represented as named
   FailureMode entities; the YAML's corresponding code paths
   annotation-match the FailureMode IDs.
5. The Configuration Vocabulary section is complete + cross-referenced
   from the marketplace plugin README.
6. The "Future: discovery sibling" section names the deferred work +
   the trigger to build it.
