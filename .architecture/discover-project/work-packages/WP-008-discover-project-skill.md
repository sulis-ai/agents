---
id: WP-008
title: Author plugins/sulis/skills/discover-project/SKILL.md with 5 phase sections + canonical annotations
status: pending
kind: docs
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-008
dependsOn: [WP-003, WP-004, WP-005, WP-006, WP-007, WP-009]
blocks: [WP-010]
estimated_token_cost:
  input: 5k
  output: 5k
tdd_section: Form §Composition root + §Skill prose; ADR-001 (Path A), ADR-003 (skill name)
adrs: [ADR-001, ADR-003, ADR-004]
---

## Context

Authors the imperative side of Path A — the `SKILL.md` at
`plugins/sulis/skills/discover-project/SKILL.md`. Per ADR-001, this
skill conforms to the canonical Workflow authored in WP-001;
divergence is caught by the drift detector at PR time (per WP-009's
HTML-comment annotation parser).

Per ADR-003, the slash-command name is `/sulis:discover-project`
(matches the canonical Workflow name) — not `/sulis:setup`.

The skill orchestrates the 5 phases by calling into the Python helpers
authored by WP-002 through WP-007:

- Detect → `_discovery.inspector.LocalFilesystemInspector` (WP-003)
- Infer → `_discovery.inferrer.LLMConfigurationInferrer` (WP-004) with `NullConfigurationInferrer` fallback
- Ask → prose fragments from WP-005 (`_prompts/*.md`) + composition logic in the skill
- Mint → `_discovery.minter.write_project_entity` (WP-006) + `slug_from_*` helpers + `_discovery.tenant.Sha256CrockfordTenantDeriver` (WP-002)
- Verify → `_discovery.verifier.verify_and_roll_back_on_failure` (WP-007)

The skill is the **founder-facing entry point** — every prompt is
plain English; structured logs go to stderr; the JSON envelope on
stdout matches the marketplace's existing `{ok, data}` shape.

## Contract

### Files created

```
plugins/sulis/skills/discover-project/
├── SKILL.md                       # the imperative; carries canonical annotations
└── _prompts/                      # symlink or copy of WP-005's prose fragments
    └── (references WP-005 files; SKILL.md includes them)
```

1 new file (SKILL.md). WP-005's `_prompts/` files already live at
`plugins/sulis/skills/discover-project/_prompts/` — this WP doesn't
duplicate them; it includes them.

### SKILL.md shape

```markdown
---
name: discover-project
description: Set up Sulis for a project by minting its Project entity. Run this once when adopting Sulis in a new repo.
canonical_source: plugins/sulis/instances/discover-project/workflow.jsonld
canonical_workflow_ulid: dna:workflow:01KT1WDSCVRWFW00000000000A
---

# /sulis:discover-project

> Minting a Project entity for the repo you're in. One command, one
> outcome: `.sulis/projects/<slug>.jsonld`.

## Flags

- `--update` — re-discovery mode; produces a per-field diff and asks
  about changes one field at a time (per ADR-005).
- `--path <sub-path>` — monorepo mode; scopes Detect to a sub-path and
  derives the slug from the basename.
- `--source-repo <org/name>` — override for repos with no git remote
  (MUC-006).

## Pre-flight: stale .tmp sweep

<!-- canonical:step:write-project-entity -->
On session start, sweep stale `.sulis/projects/*.tmp` files. (Per
TDD §Armor §Atomic write semantics — protection against the
SIGINT-mid-write race in MUC-002.)

## Phase 1 — Detect

<!-- canonical:step:read-repo-root -->
Read the consuming repo's `.git/` state via `LocalFilesystemInspector.read_root`.
- Non-git → raise non-git-directory error (MUC-001). Founder-facing
  message from FailureMode 01KT1WFM01NONGITDIR0000A.
- `.git/` but no remote → raise git-no-remote error (MUC-006). Accept
  `--source-repo` override if provided.

<!-- canonical:step:read-package-manifests -->
Enumerate `package.json`, `pyproject.toml` (and Cargo.toml, Gemfile if
present) under the repo root (or `--path` if set).

<!-- canonical:step:read-ci-workflows -->
Enumerate `.github/workflows/*.yml`, `.gitlab-ci.yml`.

<!-- canonical:step:read-repo-contract -->
Read `.sulis/repo-contract.yml` if present; skip if absent.

## Phase 2 — Infer

<!-- canonical:step:propose-configuration-values -->
Call `LLMConfigurationInferrer.infer(detected, token_budget=10_000)`.
On `TokenBudgetExceeded` OR LLM-unreachable error, swap in
`NullConfigurationInferrer` for the remainder of the run (NFR-006).

Structured log line:

    [discover-project] Infer phase: proposing N configuration values (tokens used: K / 10,000)

## Phase 3 — Ask

<!-- canonical:step:confirm-or-override-inferences -->
For each inferred value, follow the prompt template at
`_prompts/confirm-or-override.md`. Record the founder's confirmation
or override.

<!-- canonical:step:gather-ambiguous-fields -->
For fields the Infer phase couldn't populate (or that the founder is
authoritative on — Project name, brand-scope, description), follow
`_prompts/gather-ambiguous-fields.md`. If `--update` is set, instead
follow `_prompts/per-field-diff.md` and present the diff one field at
a time.

## Phase 4 — Mint

<!-- canonical:step:write-project-entity -->
Compose the Project entity from confirmed inferred values + gathered
ambiguous fields + computed identifiers:

- `belongs_to_tenant` ← `Sha256CrockfordTenantDeriver().derive_consumer_tenant(<org>/<name>)`
- `release_workflow_ref` ← `dna:workflow:01KT0RTRA1NWFW00000000000A` (marketplace release-train)
- slug ← `slug_from_project_name(name)` OR `slug_from_monorepo_path(--path)`
- Collision detection: if `.sulis/projects/<slug>.jsonld` exists AND
  `--update` is absent → raise EntityAlreadyExistsError (MUC-003).
  If a sibling Project exists AND `--path` is absent → raise
  MonorepoSlugCollisionError (MUC-007).

Install the SIGINT handler; write via `write_project_entity`. Atomic.

Structured log line:

    [discover-project] Mint phase: writing to .sulis/projects/<slug>.jsonld (atomic)

## Phase 5 — Verify

<!-- canonical:step:run-drift-detector-on-mint -->
Call `verify_and_roll_back_on_failure(entity_path)`. On
`DriftVerifyFailed`, surface the exception's stderr verbatim to the
operator — this is MUC-005's system response.

Structured log line:

    [discover-project] Verify phase: drift detector PASS

## Output envelope

On success, emit on stdout:

    {"ok": true, "data": {"entity_path": "<path>", "tenant_ulid": "<ulid>", "tokens_consumed": <int>}}

On failure, emit:

    {"ok": false, "error": {"failuremode_id": "<ulid>", "user_message": "<verbatim from FailureMode>"}}

## Tests this skill passes

- Drift detector: every canonical Step in `steps.jsonld` is annotated above.
- Drift detector: every annotation above matches a canonical Step.
- E2E: WP-010's `tests/integration/test_discover_e2e.py` covers
  UC-001 (4 fixtures), UC-002 (re-discovery), UC-003 (monorepo),
  UC-004 (non-git), UC-005 (cancel mid-flow), UC-006 (LLM correction).
```

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_discover_project_skill_conformance.py::test_skill_md_exists` — file at `plugins/sulis/skills/discover-project/SKILL.md` exists
- [ ] `test_skill_md_conformance.py::test_skill_canonical_source_field` — front-matter has `canonical_source: plugins/sulis/instances/discover-project/workflow.jsonld`
- [ ] `test_skill_md_conformance.py::test_skill_workflow_ulid_field` — front-matter `canonical_workflow_ulid` equals `dna:workflow:01KT1WDSCVRWFW00000000000A` byte-exact
- [ ] `test_skill_md_conformance.py::test_skill_has_one_annotation_per_canonical_step` — grep `<!-- canonical:step:<name> -->`; assert set of annotation Step names == set of Step names in `steps.jsonld` (no missing, no extra) — this is the n=2 dogfood of the drift detector
- [ ] `test_skill_md_conformance.py::test_skill_imports_each_phase_helper` — body references `LocalFilesystemInspector`, `LLMConfigurationInferrer`, `NullConfigurationInferrer`, `write_project_entity`, `verify_and_roll_back_on_failure`, `Sha256CrockfordTenantDeriver`, `slug_from_project_name`, `slug_from_monorepo_path`, `stale_tmp_sweep`, `install_sigint_handler`
- [ ] `test_skill_md_conformance.py::test_skill_describes_3_flags` — `--update`, `--path`, `--source-repo` each mentioned in the Flags section
- [ ] `test_skill_md_conformance.py::test_skill_emits_structured_log_lines_per_phase` — each phase section contains its prefixed log line `[discover-project] <Phase> phase:`
- [ ] `test_skill_md_conformance.py::test_skill_specifies_json_envelope` — Output envelope section names both ok-true and ok-false shapes
- [ ] `test_skill_md_conformance.py::test_skill_specifies_pre_flight_sweep` — `stale_tmp_sweep` is invoked before Phase 1
- [ ] `test_skill_md_conformance.py::test_skill_includes_prompt_fragments` — references `_prompts/confirm-or-override.md`, `_prompts/gather-ambiguous-fields.md`, `_prompts/per-field-diff.md` by path (so WP-005's prose is the one source of truth)
- [ ] `tests/unit/test_check_canonical_drift_discover.py::test_drift_detector_passes_against_skill_md` — the existing drift detector (with WP-009's HTML-comment parser) returns exit 0 when run with `--scope plugins/sulis/skills/discover-project/SKILL.md` (n=2 dogfood acceptance)

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/skills/discover-project/SKILL.md` authored per Contract
- [ ] Front matter includes `name`, `description`, `canonical_source`, `canonical_workflow_ulid`
- [ ] One `<!-- canonical:step:<name> -->` annotation per canonical Step from WP-001's `steps.jsonld` (9 annotations)
- [ ] All 11 Red tests pass
- [ ] Drift detector run with `--scope plugins/sulis/skills/discover-project/SKILL.md` passes (exit 0) — this is the load-bearing acceptance check

### Blue — Refactor complete

- [ ] Phase sections in the same order as WP-001's `workflow.jsonld` `phases` field (Detect → Infer → Ask → Mint → Verify)
- [ ] Annotations placed immediately above the section they describe (parser convention)
- [ ] Founder-English (FE-01..FE-10) sweep: no internal IDs in operator-facing text outside front-matter; no token-budget numbers visible in Ask-phase prose
- [ ] `description` front-matter field is the founder-friendly framing (per ADR-003 — *"Set up Sulis..."*); the slash-command name stays canonical

## Sequence

- **dependsOn:**
  - WP-003 (`LocalFilesystemInspector` is imported)
  - WP-004 (`LLMConfigurationInferrer` + `NullConfigurationInferrer` are imported)
  - WP-005 (`_prompts/*.md` fragments included by reference)
  - WP-006 (`write_project_entity`, `stale_tmp_sweep`, `install_sigint_handler`, slug helpers imported)
  - WP-007 (`verify_and_roll_back_on_failure` imported)
  - WP-009 (drift detector must parse HTML-comment annotations + accept `--cross-tenant-refs-allowed-for` for the conformance test to pass)
- **blocks:** WP-010 (E2E + dogfood depends on the assembled skill)
- **Parallelisable with:** — (this WP gates the assembly)

This is the only WP whose `dependsOn` spans the whole backend set. The
critical-path serial step.

## Estimated Token Cost

- **Input:** ~5k (TDD §Form §Composition root + 7 dependency WP outputs' contracts + ADR-001/003/004 + the 3 prompt fragments)
- **Output:** ~5k (`SKILL.md` ≈ 250 LOC including front matter + annotations + 5 phase sections + envelope spec)
- **Total:** ~10k

## Notes

- This WP is `kind: docs` because the deliverable is markdown that the operator reads + the agent executes; per WP_STANDARD WP-01 the kind dispatches on what the WP touches. The "implementation" is prose; the Python helpers it composes were authored in their own backend WPs.
- The skill's `description` front-matter carries the friendly framing per ADR-003 ("Set up Sulis..."). The slash-command name remains `/sulis:discover-project` — the friendly framing lives in metadata, not in the command name.
- Per ADR-001 (Path A n=2): if this skill passes the drift detector against WP-001's canonical, the Path A discipline is proven for a second non-trivial workflow whose imperative is markdown (not YAML). That outcome is the load-bearing acceptance of this whole change.
- The "Tests this skill passes" tail section in the skill itself is informational — it tells future readers where the conformance evidence lives. The actual gating happens in `tests/unit/test_check_canonical_drift_discover.py` (WP-009 extends this) and `tests/integration/test_discover_e2e.py` (WP-010 authors this).
