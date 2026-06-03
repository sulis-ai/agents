---
id: WP-001
title: Re-model the release-train Workflow from dev→main promotion to trunk-based (15→10 Steps, coupled mirror + template + live edit)
status: pending
kind: infra
primitive: refactor
group: REORGANISE
sequence_id: WP-001
dependsOn: []
blocks: []
estimated_token_cost:
  input: 14k
  output: 10k
platform: github-actions
touch-class: deploy
founder_facing: false
change: CH-01KT4K
spec: ../../../.changes/refactor-simplify-release-robot.SPEC.md
audit: ../../../.changes/refactor-simplify-release-robot.AUDIT.md
guide: ../../../docs/trunk-based-release-workflow-remodel.md
composite_of:
  - canonical-mirror-steps
  - canonical-mirror-workflow
  - canonical-mirror-failuremodes
  - canonical-mirror-triggers
  - imperative-template-yaml
  - imperative-live-yaml
characterisation_test: plugins/sulis/scripts/tests/methodology/test_release_on_merge_yaml_unchanged_behaviour.sh (+ the drift gate; + a new read-through assertion that the live .github workflow has no reachable promotion/back-merge/ancestry logic)
verification:
  adapter: methodology
  artifact: "check-canonical-drift.py --instance-dir plugins/sulis/instances/release-train --yaml-path plugins/sulis/templates/workflows/release-on-merge.yml exits 0; plus plugins/sulis/scripts/tests/ green (incl. test_branch_ci_has_drift_check.py + _canonical_drift unit tests)"
  shape: concrete
---

## Context

Finish the Model A (trunk-based) cutover by re-modelling the **release-train
Workflow** from the two-branch (`dev→main` promotion) shape to a trunk-based
(`main`-only) shape. The release stops being a *merge between branches* and
becomes a *bump + tag on the trunk*.

Authoritative spec + technical design (already validated — this WP does NOT
re-open design):

- Spec: `.changes/refactor-simplify-release-robot.SPEC.md`
- Edit-map + drift-matcher contract + the failure-mode count decision:
  `.changes/refactor-simplify-release-robot.AUDIT.md`
- Executable end-state: `docs/trunk-based-release-workflow-remodel.md`

This is the **agents-repo half only** (the canonical edit in `sulis-ai/plugins`
is a separate paired change). Until that lands, the vendored mirror at
`plugins/sulis/instances/release-train/` is the working source of truth.

### Why this is ONE atomic WP (the coupling constraint)

The drift gate `check-canonical-drift.py` (run in `branch-ci` as the
`canonical-drift-check` job) compares the **vendored mirror**
(`plugins/sulis/instances/release-train/`) against the **annotated template**
(`plugins/sulis/templates/workflows/release-on-merge.yml`) **bidirectionally**:

- `missing_in_canonical` = every template `# canonical:step:<name>` /
  `# canonical:failuremode:<name>` annotation MUST resolve to a real mirror
  Step/FailureMode. **Delete a Step from the mirror without removing the
  matching template annotation → gate goes RED.**
- `missing_in_yaml` = every non-excluded mirror Step MUST be annotated in the
  template OR listed in `steps.jsonld:excluded_from_yaml`.

Therefore the mirror edit (parts 1-4) and the template-annotation edit (part 5)
**cannot be separate WPs** — any intermediate state where one is edited and the
other is not produces a guaranteed-RED `branch-ci`, and the whole thing ships as
one PR into `main` regardless. Splitting would violate the change's core
constraint: **LIVE release machinery — never leave the release flow bricked.**

This WP lands all six coupled edits in one commit/PR. (A pure-docs follow-up,
if ever wanted, would `dependsOn: [WP-001]` and would not split the coupled
mirror + template + live edits.)

### Baseline (current state — verified at decompose time)

- Drift gate vs **template** (the branch-ci path): `exit 0` clean.
- The mirror is **15 Steps** with `excluded_from_yaml` =
  `[gate-founder-confirmation, open-release-pr, wait-for-checks-and-mergeability,
  publish-github-release, squash-merge, preflight-cross-branch-drift]`.
- The template carries annotations for 8 distinct Steps + 2 FailureModes
  (incl. `draft-pr-body-and-changelog` + `probabilistic-step-token-budget-exceeded`)
  and a dead WP-003 auto-back-merge block (steps 10-12 in the template:
  pin-read / decide+act / verify-atomicity).
- The **live** `.github/workflows/release-on-merge.yml` is **already a clean
  trunk-style** bump+tag+push (303 lines, 0 canonical annotations, no
  promotion/back-merge block). **It is invisible to the drift gate** (the gate's
  `--yaml-path` points at the template, not the live file) — correctness here is
  by read-through only.

> **Note (decompose finding, not a blocker):** the live `.github` workflow
> already lacks the promotion/back-merge logic, so AUDIT.md edit-map item 6
> ("remove the same dead promotion logic from the live workflow") is largely a
> **read-through confirmation** rather than a deletion. The executor MUST still
> read it end-to-end and confirm no reachable `dev`/promotion/ancestry branch of
> logic exists, and add the read-through characterisation assertion. See the
> "Concern" note at the bottom and DECOMPOSE_VALIDATION.md P-PLAT.

## Contract

The "public interface" of this WP is the **drift-matcher contract** (mirror ↔
template parity) plus the well-formedness of the brain instance. No code symbols
change; the contract is the structural agreement enforced by the gate.

### End-state mirror shape (10 Steps, 4 kept FailureModes)

Kept Steps (in linear order):
`detect-pending-changesets` → `preflight-version-drift` → `compute-next-version`
→ `gate-founder-confirmation` → `bump-version-files` → `write-changelog-entry`
→ `commit-bump-on-main` (was `commit-bump-as-bot`) → `tag-and-push`
→ `publish-github-release` → `emit-release-entity`.

Deleted Steps (5): `preflight-cross-branch-drift`, `draft-pr-body-and-changelog`,
`open-release-pr`, `wait-for-checks-and-mergeability`, `squash-merge`.

Kept FailureModes (4): `version-drift-detected-pre-flight`,
`loop-guard-matches-founder-pr`, `bot-tag-doesnt-trigger-release-prod`,
`workflow-yaml-fails-to-parse`.

Deleted FailureModes (4 — per AUDIT.md DIVERGENCE, refining the guide's loose
"2" to the structurally-exact orphaned set): `pr-checks-fail`,
`release-pr-conflicts-with-target-at-merge`, `pr-open-but-mergeability-stuck`,
`probabilistic-step-token-budget-exceeded`.

End-state `excluded_from_yaml` = `[gate-founder-confirmation,
publish-github-release]` (the two real-but-unannotated Steps).

### The complete edit map (6 coupled file edits — from AUDIT.md §"complete edit map")

1. **`plugins/sulis/instances/release-train/steps.jsonld`**
   - Delete the 5 Step objects: `preflight-cross-branch-drift`,
     `draft-pr-body-and-changelog`, `open-release-pr`,
     `wait-for-checks-and-mergeability`, `squash-merge`.
   - Shrink `excluded_from_yaml` to `[gate-founder-confirmation,
     publish-github-release]`.
   - Change `detect-pending-changesets`: reads **main's** `.changesets` (since
     the last tag) — update `agent_instructions` / `input_artifacts` prose.
   - Change `commit-bump-as-bot` → conceptually `commit-bump-on-main`: commits
     **directly to `main`** (no promotion PR). (Keep the bot author identity —
     load-bearing for the loop-guard.)
   - No surviving kept Step references a deleted FailureMode in
     `handles_failures` (verified clean at decompose: only step 7 referenced the
     three PR-merge FMs, and step 5 the token-budget FM — all deleted).
   - Update `_about`: 15 → 10.

2. **`plugins/sulis/instances/release-train/workflow.jsonld`**
   - Remove the 5 deleted step names from `workflows[0].steps[]`.
   - Rewire `transitions[]` to the linear 10-step path; **drop the JT-7 back-edge**
     (`wait-for-checks-and-mergeability -> open-release-pr`) and all promotion
     edges. New path:
     `detect → preflight-version-drift → compute → gate-founder-confirmation →
     bump → changelog → commit → tag → publish → emit`.
   - Update `initial_steps` (unchanged: `detect-pending-changesets`),
     `terminal_steps` (drop nothing required; `gate-founder-confirmation` stays
     a valid abort-terminal). Keep `state_contract` (the `pr_url`/`merge_sha`
     fields may be retained or trimmed — retain to avoid schema churn unless the
     schema rejects; executor confirms against `workflow.schema.json`).
   - Update `_about` + `description` prose: 15 → 10, new arrow sequence.

3. **`plugins/sulis/instances/release-train/failuremodes.jsonld`**
   - Delete the 4 FailureMode objects named above.
   - Update `_about`: eight → four.

4. **`plugins/sulis/instances/release-train/triggers.jsonld`**
   - The release trigger becomes "operator invokes `/sulis:release` on `main`
     (or a cadence)", **not** "open a `dev→main` PR". Update the event Trigger's
     `condition`/`description` (the manual Trigger already matches; the
     `pull-request-merged-to-main` event Trigger's condition is rewritten to the
     push-to-main / cadence shape per the guide's Trigger line).

5. **`plugins/sulis/templates/workflows/release-on-merge.yml`** (the annotated
   template — the file the drift gate reads)
   - Remove the `# canonical:step:draft-pr-body-and-changelog` annotation **and**
     its `# canonical:failuremode:probabilistic-step-token-budget-exceeded`
     annotation (lines ~197-198). These are the ONLY two annotations that would
     become orphaned `missing_in_canonical` drift after the mirror deletions.
   - The other 4 deleted Steps are NOT annotated in the template (they were in
     `excluded_from_yaml`), so there is **no annotation churn** for them.
   - Remove the dead promotion/back-merge YAML: the entire WP-003 auto-back-merge
     block (the `Read dev-sha-at-open pin`, `Fast-forward dev to main, or open
     raced-path back-integrate PR`, and `Verify atomicity (NFR-006)` steps, ~lines
     444-561) — there is no `open-PR` / `wait-for-checks` / `squash-merge` YAML to
     remove (those steps were never imperatively present; they lived only as the
     excluded canonical Steps). Re-fold the draft+prepend CHANGELOG steps so the
     surviving `write-changelog-entry` annotation still resolves (see Notes).
   - Update the header comment block listing "Steps deliberately absent" to the
     2-step end-state (`gate-founder-confirmation`, `publish-github-release`).

6. **`.github/workflows/release-on-merge.yml`** (the LIVE workflow — 0 annotations,
   invisible to the gate)
   - Read end-to-end; confirm it performs exactly the 10-step trunk flow with no
     reachable promotion/back-merge/ancestry branch of logic. (Baseline finding:
     it already does — no back-merge block present. The edit here is
     confirmation + any residual prose/comment cleanup referencing `dev`.)
   - Add the read-through characterisation assertion (see Blue / DoD).

## Definition of Done

> Red-Green-Blue. The **blocking gate** is the drift check exiting 0 against the
> template. NEVER leave the release flow bricked: all six edits land in one
> commit/PR.

### Red — Failing tests written (prove the gap exists, see them fail)

- [ ] **Drift parity (the load-bearing assertion).** Author / extend a
  methodology test (e.g. `tests/methodology/test_release_train_trunk_shape.sh`
  or extend `test_release_train_drift_and_pin.py`) that asserts the mirror has
  exactly the 10 kept Steps + 4 kept FailureModes and that
  `check-canonical-drift.py --instance-dir plugins/sulis/instances/release-train
  --yaml-path plugins/sulis/templates/workflows/release-on-merge.yml` exits 0.
  **Before the edit this fails** — either the mirror still has 15 Steps (count
  assertion red) OR, if the mirror is edited first, the gate goes RED on the two
  orphaned template annotations (`missing_in_canonical:
  draft-pr-body-and-changelog`, `probabilistic-step-token-budget-exceeded`).
- [ ] **Live-workflow no-promotion read-through.** Author a static assertion
  (e.g. `tests/methodology/test_live_release_on_merge_is_trunk.sh`) that greps
  the live `.github/workflows/release-on-merge.yml` for reachable
  promotion/back-merge tokens (`back-integrate`, `main:dev`, `dev-sha-at-open`,
  `gh pr create`, `gh pr merge`) and **fails if any reachable promotion branch
  exists**. Confirm it is RED if/when such logic is present (it is currently
  absent → this assertion guards against re-introduction; if it passes at
  baseline, record that explicitly — the Red is the *template* drift above).
- [ ] **Instance well-formedness.** Confirm an existing or new test runs
  `--validate-schemas` (or the brain rubric / dna-runner / `validate-instance`)
  over the re-modelled instance and would FAIL on a dangling step name in
  `workflow.steps[]`, a `transitions[]` edge to a deleted step, or a
  `handles_failures` id pointing at a deleted FailureMode.

### Green — Implementation makes tests pass

- [ ] All six edits applied per the Contract edit-map, in one commit.
- [ ] `steps.jsonld`: 10 Step objects; `excluded_from_yaml` =
  `[gate-founder-confirmation, publish-github-release]`;
  `detect-pending-changesets` + `commit-bump-as-bot` prose updated; `_about` 15→10.
- [ ] `workflow.jsonld`: `steps[]` = the 10 kept names; `transitions[]` linear,
  no back-edge, no edge references a deleted step; `_about`/`description` updated.
- [ ] `failuremodes.jsonld`: 4 FailureMode objects; `_about` updated.
- [ ] `triggers.jsonld`: event Trigger condition rewritten to push-to-main /
  cadence (no `dev→main` PR language).
- [ ] Template: the two orphaned annotations removed; dead back-merge YAML
  removed; CHANGELOG draft+prepend re-folded so `write-changelog-entry`
  annotation still resolves; header "absent steps" comment updated to the 2.
- [ ] Live workflow: confirmed 10-step trunk flow, no reachable promotion logic;
  residual `dev` references in comments cleaned.
- [ ] **`check-canonical-drift.py … --yaml-path …/templates/workflows/release-on-merge.yml`
  exits 0.** (The blocking gate.)
- [ ] `cd plugins/sulis/scripts && uv run python -m pytest tests/` is green —
  specifically `tests/unit/test_branch_ci_has_drift_check.py`,
  `tests/unit/test_check_canonical_drift.py`,
  `tests/unit/test_release_train_drift_and_pin.py`, and the new
  trunk-shape + live-read-through assertions.
- [ ] `test_branch_ci_has_drift_check.py` still passes — i.e. the branch-ci
  `canonical-drift-check` job still references the `.github/workflows/release-on-merge.yml`
  fragment **in a comment** AND the actual `--yaml-path` points at the template
  (do NOT remove the comment fragment on branch-ci.yml line ~116; the test keys
  off its presence). branch-ci.yml is NOT edited by this WP.

### Blue — Refactor complete (leave it better than found)

- [ ] No dangling references anywhere: no `handles_failures` id, no
  `transitions[]` edge, no `steps[]` name, and no template annotation points at a
  deleted entity. (The gate proves the template↔mirror half; the schema/rubric
  proves the intra-mirror half.)
- [ ] `_about` blocks across all four instance files read as a coherent 10-step
  trunk description — no stale "15"/"promotion"/"dev→main"/"squash" language.
- [ ] The characterisation read-through assertion on the live workflow is
  committed so future edits cannot silently re-introduce promotion logic.
- [ ] Template comment block (the "Canonical Step annotations" + "Steps
  deliberately absent" prose) matches the new reality — no orphaned narrative.

## Sequence

- **dependsOn:** none. This is the head and (currently) only node.
- **blocks:** none in this change. A future pure-docs follow-up (if filed) would
  depend on this WP and MUST NOT split the coupled edits.

## Estimated Token Cost

- **Input:** ~14k (4 instance files + 2 workflow files + drift module + tests +
  the spec/audit/guide). The instance files are large (steps.jsonld ~22KB).
- **Output:** ~10k (edits across 6 files + 2 new/extended test assertions).
- **Total:** ~24k. Routes to a high-capability model tier — the coupling means
  the executor must hold the mirror↔template contract in head while editing both.

## Notes

- **CHANGELOG draft/prepend re-fold (template).** Today the template has TWO
  CHANGELOG steps: `Draft CHANGELOG entry` (annotated
  `draft-pr-body-and-changelog` + the token-budget FM) and `Prepend CHANGELOG
  entry` (annotated `write-changelog-entry`). After deleting the
  `draft-pr-body-and-changelog` Step from the mirror, the **draft annotation
  must go**, but the CHANGELOG drafting behaviour itself is kept (the guide:
  "changelog drafting consolidates into compute-next-version /
  write-changelog-entry"). Simplest boring move: keep both YAML steps' bodies but
  re-annotate the draft step under `# canonical:step:write-changelog-entry` (or
  merge the two YAML steps into one annotated `write-changelog-entry` block).
  Either way the only surviving CHANGELOG annotation is `write-changelog-entry`,
  which resolves cleanly. Executor picks the cleaner of the two; both pass the
  gate.
- **Ordering within the single commit (constraint from SPEC §Constraints):**
  prefer mirror → template → drift-check → live so the gate confirms parity
  before the live file is trusted. But all edits land in ONE commit — the
  ordering is the executor's working sequence, not separate commits.
- **Loop-guard + bot-tag FMs are load-bearing — do NOT delete.** Their deletion
  re-introduces the release-of-release loop (#132) and the downstream-trigger
  bug. They are explicitly in the keep set.
- **Schema location for validation:**
  `plugins/sulis/brain/compiled/foundation/{step,workflow,failuremode,trigger}.schema.json`
  (also vendored under the instance's `schemas/`). Use `--validate-schemas` on
  the drift script or the brain rubric / `sulis-brain:validate-instance`.
