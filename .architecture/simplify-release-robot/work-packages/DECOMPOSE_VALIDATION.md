# Decompose Validation — simplify-release-robot

**Change:** CH-01KT4K · refactor · trunk-based cutover (Model A, step 4)
**WP set:** 1 (WP-001, single atomic coupled edit)
**Verdict:** **PASS-WITH-RATIONALE**

> The set passes every rubric phase. The single non-default shape — ONE WP that
> touches six files across two kinds-of-artifact (canonical-entity JSON-LD +
> CI YAML) instead of a decomposed set — is **mandated** by the drift-gate
> coupling, not a decomposition shortcut. That rationale is recorded in P1/P2
> below and is the reason the verdict is PASS-WITH-RATIONALE rather than a bare
> PASS.

---

## P1 — Atomicity

**PASS (with coupling rationale).** A WP is atomic when an execution agent can
implement it without first implementing another WP. WP-001 has no `dependsOn`
and is self-contained. The question that arises for a *single*-WP set is the
inverse: should this have been *more* than one WP?

**No — and the constraint is hard, not stylistic.** The drift gate
`check-canonical-drift.py` (run as the `branch-ci` `canonical-drift-check` job)
matches the mirror (`plugins/sulis/instances/release-train/`) against the
annotated template (`plugins/sulis/templates/workflows/release-on-merge.yml`)
**bidirectionally**:

- `missing_in_canonical`: a template `# canonical:step:<name>` annotation with
  no matching mirror Step → drift (exit 1).
- `missing_in_yaml`: a non-excluded mirror Step with no template annotation →
  drift (exit 1).

Deleting `draft-pr-body-and-changelog` from the mirror without removing its
template annotation (and its `probabilistic-step-token-budget-exceeded` FM
annotation) produces a RED gate. Conversely, removing the template annotation
before the mirror Step produces `missing_in_canonical` … no — it produces the
opposite (annotation gone, mirror present is fine for `missing_in_canonical`;
but the mirror Step would then be `missing_in_yaml` unless excluded). Either
ordering creates a guaranteed-RED intermediate `branch-ci`. Since the work ships
as one PR into `main` regardless, and the SPEC's load-bearing constraint is
"never leave the release flow bricked," **splitting is forbidden, not merely
inadvisable.** Verified at decompose time:

- Baseline drift vs template: `exit 0` (clean).
- Simulated intermediate (mirror edited, template not): would report
  `missing_in_canonical: draft-pr-body-and-changelog` +
  `probabilistic-step-token-budget-exceeded`.

This is the textbook "the coupled edits must land together" case from the
plan-work shaping note in AUDIT.md §"WP shaping note." PASS-WITH-RATIONALE.

## P2 — Sequencing & dependency graph

**PASS.** Single node, no edges. `dependsOn: []`, `blocks: []`. No merge-conflict
ordering to express. The `mermaid` graph in INDEX.md is a single node — correct.
The "working sequence" inside the one commit (mirror → template → drift-check →
live) is documented in WP-001 §Notes and INDEX §Recommended Implementation
Order; it is an executor working order, **not** a WP boundary, which is the
correct modelling for a coupled atomic edit.

## P3 — Contract completeness

**PASS.** The WP's "contract" is the drift-matcher parity contract (mirror ↔
template) plus brain-instance well-formedness — appropriate for an infra/
canonical-entity refactor where no code symbol changes. WP-001 §Contract
enumerates: the end-state 10-Step / 4-FailureMode shape, the deleted sets, the
end-state `excluded_from_yaml`, and the full 6-file edit map lifted verbatim
from AUDIT.md. Nothing is left to executor invention.

## P4 — Definition of Done (Red-Green-Blue)

**PASS.** All three phases present and named:

- **Red** — three failing assertions: (1) drift-parity / Step-count, (2) live
  no-promotion read-through, (3) instance well-formedness via `--validate-schemas`
  / brain rubric. Each is constructed to fail *before* the edit (or to guard
  against regression where the gap is already partly closed — see the honest
  note in P-VER below).
- **Green** — every edit-map item has a checkbox; the blocking gate (drift exit
  0) and the full pytest run are explicit; the branch-ci-test-preservation
  subtlety is called out.
- **Blue** — dangling-reference sweep, `_about` prose coherence, the committed
  read-through guard, template comment-block freshness.

REFACTOR (Blue) is not skipped — it carries the load-bearing "no stale
15/promotion/dev→main language" cleanup that is the whole point of a Model-A
"the shrink IS the model being right" change.

## P5 — Token budget & model routing

**PASS.** `estimated_token_cost: input ~14k / output ~10k` recorded in
frontmatter and INDEX. The estimate is justified (large instance files —
steps.jsonld ~22KB — plus two workflow files plus the drift module plus tests).
Routes to a high-capability tier, which is correct: the coupling means the
executor must hold the mirror↔template contract in working memory while editing
both sides.

## P6 — Primitive + Group classification

**PASS.** `primitive: refactor`, `group: REORGANISE`. Correct per
`references/change-primitives.md`:

- It is **not** EXPAND (no new capability — capability is *removed*).
- It is **not** SUBSTITUTE-Wrap (no internal code wrapped) and **not**
  SUBSTITUTE-Replace (files edited in place, not swapped wholesale).
- It is **not** CONTRACT-Delete-as-a-WP-primitive in the deprecate-then-delete
  sense (the deleted Steps are canonical-model nodes, not production-reachable
  code paths being retired through a deprecation window; the imperative they
  map to is edited in the same atomic move).
- It **is** REORGANISE-refactor: a behaviour-shape change to the canonical graph
  + the imperative it bridges, removing machinery that only served the dev→main
  promotion. The `composite_of:` frontmatter records the six sub-edits.
- `characterisation_test:` frontmatter present (REORGANISE MUST rule). The
  drift gate + the existing byte-equivalence methodology test + a new live
  read-through assertion pin behaviour.

## P7 — Wrap audit / No-Band-Aid-Wrappers

**PASS.** Zero Wrap WPs. The Wrap Audit table in INDEX is empty with the
correct rationale. No wrapper rot is introduced — the change *removes* the
dead auto-back-merge block, the opposite of adding a wrapper layer.

## P8 — Cross-WP identifier canonicalisation

**PASS (trivially / N/A).** Single-WP set → no cross-WP identifiers to
canonicalise. The identifiers that matter (the canonical Step/FailureMode
`@id`s and names) are all defined in one place (the mirror) and consumed by the
template annotations within the same WP; their parity is the drift gate's job,
asserted in WP-001's Red.

---

## P-PLAT — Platform contract (GitHub Actions, write/deploy touch)

**PASS.** The WP carries `platform: github-actions` and `touch-class: deploy`
in frontmatter — correct, because the release workflow pushes commits, tags,
and GitHub Releases. The GitHub Actions platform contract is grounded:

- **`bot-tag-doesnt-trigger-release-prod`** FailureMode is in the **KEEP** set —
  the WP explicitly lists it among the 4 kept FailureModes and flags (in §Notes)
  that deleting it would re-introduce the downstream-trigger bug. This is the
  GitHub-Actions security boundary (a `GITHUB_TOKEN`-pushed tag does not fire
  downstream `workflow_run` events) and it still applies to the kept
  `tag-and-push → publish-github-release` path on a trunk.
- **`loop-guard-matches-founder-pr`** FailureMode is in the KEEP set; the WP
  flags the bot-author loop-guard (`actor == github-actions[bot]`) as
  load-bearing and instructs the executor to keep the bot author identity on
  `commit-bump-on-main` (the bump commit on `main` must not re-trigger the
  robot — exactly the platform-contract concern the SPEC §Constraints names).
- **`workflow-yaml-fails-to-parse`** FailureMode is KEPT — the platform's
  silent-no-op-on-parse-failure behaviour (the #130 regression) means the
  drift gate + branch-ci pyyaml safe-load remain the second line of defence;
  the WP does not touch that guard.

No new platform capability is added; the WP *removes* the auto-back-merge block
that used `gh pr create` / `gh pr merge --auto` / `git push origin main:dev`.
The no-force-push invariant is preserved by deletion (the block carrying it is
removed; no new push refspecs are introduced). The live workflow's existing
`permissions:`, `concurrency:`, and loop-guard `if:` are untouched.

## P-VER — Verification by design

**PASS.** Per the VERIFICATION_QUESTIONS canonical + the per-kind adapter table,
`kind: infra` maps to the methodology/infra adapter; the WP's `verification:`
frontmatter uses **Shape 1 (concrete)**:

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

- **adapter:** `methodology` — the verification artifacts are the drift-gate CLI
  invocation + the `plugins/sulis/scripts/tests/` suite (methodology/unit). This
  matches the SPEC §Verification Plan, which names the drift gate as the
  blocking proof and the existing test suite as the regression armour.
- **artifact (concrete, resolves at design time — repo-grep confirmed):**
  - `check-canonical-drift.py` exists at `plugins/sulis/scripts/check-canonical-drift.py`. ✓
  - `tests/unit/test_branch_ci_has_drift_check.py` exists (9 tests, pass at
    baseline). ✓
  - `tests/unit/test_check_canonical_drift.py` + `tests/unit/test_release_train_drift_and_pin.py`
    exist (56 tests, pass at baseline). ✓
  - The `_canonical_drift` matcher/parser/reader modules exist under
    `plugins/sulis/scripts/_canonical_drift/`. ✓
  - No hallucinated infrastructure: every cited path was verified to resolve at
    decompose time.
- **No `deferred` rows.** The change ships its own test the moment it lands — the
  trunk-shape assertion + the live read-through assertion are authored in WP-001's
  Red. No follow-on infrastructure is needed.
- **Bootstrap-from-zero:** a fresh clone at the merge SHA runs
  `cd plugins/sulis/scripts && uv run python -m pytest tests/` and the drift CLI;
  both resolve via the existing `pyproject.toml` / `uv.lock` (verified present).

### SRD↔TDD Verification Plan contradiction check (UC-002 alt-A)

**One contradiction surfaced and resolved — recorded, not silently overridden.**

The SPEC §Verification Plan says "Manual read-through of the live `.github/`
workflow: confirm the 10-Step path with no reachable promotion/back-merge/
ancestry logic." At decompose time the live workflow was found to **already** be
trunk-shaped (no back-merge block; that logic lives only in the *template*). This
means edit-map item 6 ("remove the same dead promotion logic from the live
workflow") is largely a *confirmation*, not a deletion.

- **Resolution route chosen: inline callout in WP-001** (§Context "decompose
  finding" note) + this P-VER record. The contradiction is not load-bearing (it
  does not make the SPEC's plan impossible — the read-through still happens, it
  just finds nothing to delete), so no founder escalation and no ADR is needed.
- The WP converts the SPEC's manual read-through into a **committed static
  assertion** (`test_live_release_on_merge_is_trunk.sh`) so the guarantee
  becomes regression-proof rather than a one-time manual check — a strengthening
  of the SPEC intent, surfaced explicitly.

---

## Tooling run at decompose time

| Check | Result |
|---|---|
| `wpx-index lint --project simplify-release-robot` | `{"ok": true, "data": {"header": "canonical"}}` — PASS |
| Baseline drift vs template (branch-ci path) | `exit 0` clean (the parity the WP must preserve) |
| `pytest test_branch_ci_has_drift_check.py` | 9 passed |
| `pytest test_check_canonical_drift.py + test_release_train_drift_and_pin.py` | 56 passed |
| Cited verification paths repo-grep | all resolve (no hallucinated infra) |

## Output collision check

Written under `.architecture/simplify-release-robot/work-packages/` — distinct
from the existing `.architecture/release-train/work-packages/` set. No collision.

## Final verdict

**PASS-WITH-RATIONALE.** Every phase passes. The single deviation from a
multi-WP default — one atomic WP spanning six coupled file edits — is mandated
by the bidirectional drift gate and the "never brick the release flow"
constraint, and is fully documented (P1 rationale). No blocking gaps.
