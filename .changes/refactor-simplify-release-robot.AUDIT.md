# Audit — Simplify the release robot to trunk-based

**Change:** CH-01KT4K · refactor · brownfield (Stage 2)

This is a precisely-specified refactor; the guide
(`docs/trunk-based-release-workflow-remodel.md`) is the authoritative gap
analysis. The audit's real job was the **drift-matcher contract** and the
**exact ripple of the deletions** — done below. One divergence from the guide
surfaced (failure-mode count) and is resolved with reasoning.

## The drift-matcher contract (the thing that mustn't brick)

`check-canonical-drift.py` runs `StrictDriftMatcher` over (mirror Steps +
FailureModes) vs (template `canonical:` annotations). It is **bidirectional**
with one escape hatch:

- `missing_in_yaml` = canonical Step names − annotated − `excluded_from_yaml`.
  Every mirror Step must be **annotated in the template** OR listed in
  `steps.jsonld:excluded_from_yaml`.
- `missing_in_canonical` = annotated − canonical. Every template annotation
  must resolve to a real mirror Step. **→ delete a Step from the mirror and you
  MUST delete/repoint its template annotation, or the gate goes red.**
- `missing_failuremode_handling` = each non-excluded Step's `handles_failures`
  FailureMode must be annotated somewhere in the template.
- `validate_handles_failures` = every Step's `handles_failures` id must resolve
  in `failuremodes.jsonld`. **→ delete a FailureMode and you must remove its id
  from any surviving Step's `handles_failures`.**

The gate compares the **mirror** to the **template** only. The live
`.github/workflows/release-on-merge.yml` is invisible to the gate — correctness
there is by hand.

## Current `excluded_from_yaml` (steps.jsonld)

`gate-founder-confirmation`, `open-release-pr`, `wait-for-checks-and-mergeability`,
`publish-github-release`, `squash-merge`, `preflight-cross-branch-drift`.

Of these, 4 are deleted steps → they leave the list. Surviving excluded steps:
`gate-founder-confirmation` + `publish-github-release` (real steps, by-design
unannotated in the imperative).

## Step → failure-mode wiring (15 steps today)

| # | Step | handles_failures | fate |
|--:|---|---|---|
| 1 | detect-pending-changesets | — | KEEP (change: read main) |
| 2 | preflight-version-drift | version-drift-detected-pre-flight | KEEP |
| 3 | preflight-cross-branch-drift | version-drift-detected-pre-flight* | **DELETE** |
| 4 | compute-next-version | — | KEEP |
| 5 | draft-pr-body-and-changelog | probabilistic-step-token-budget-exceeded | **DELETE** |
| 6 | open-release-pr | — | **DELETE** |
| 7 | wait-for-checks-and-mergeability | pr-checks-fail, release-pr-conflicts-with-target-at-merge, pr-open-but-mergeability-stuck | **DELETE** |
| 8 | gate-founder-confirmation | — | KEEP |
| 9 | squash-merge | — | **DELETE** |
| 10 | bump-version-files | — | KEEP |
| 11 | write-changelog-entry | — | KEEP |
| 12 | commit-bump-as-bot | — | KEEP (change: commit on main) |
| 13 | tag-and-push | — | KEEP |
| 14 | publish-github-release | bot-tag-doesnt-trigger-release-prod | KEEP |
| 15 | emit-release-entity | — | KEEP |

\* version-drift FM is shared with step 2 (kept) → it survives.

## DIVERGENCE FROM THE GUIDE — failure-modes: guide says 2, reality is 4

The guide says "delete 2 FailureModes (cross-branch/ancestry-drift +
auto-back-merge)" but flags "confirm exact @ids against failuremodes.jsonld."
There is **no FailureMode literally named ancestry-drift**. Driving the deletion
off "which FMs become orphaned when the 5 dev→main Steps are deleted" gives the
structurally-correct set:

**DELETE 4 FailureModes** (all orphaned by the deleted steps, all dev→main-PR-only):
- `pr-checks-fail` (step 7)
- `release-pr-conflicts-with-target-at-merge` (step 7) ← the "auto-back-merge"/JT-7 cycle
- `pr-open-but-mergeability-stuck` (step 7)
- `probabilistic-step-token-budget-exceeded` (step 5; no probabilistic step remains on the trunk)

**KEEP 4 FailureModes** (still real on a trunk):
- `version-drift-detected-pre-flight` (step 2)
- `loop-guard-matches-founder-pr` (the robot loop-guard)
- `bot-tag-doesnt-trigger-release-prod` (step 14)
- `workflow-yaml-fails-to-parse` (workflow-level)

Decision (Sulis, HOW-level): delete the 4 orphaned FMs. This refines the guide's
"2" to "4" by the guide's own principle (remove machinery that only serves
dev→main promotion). Flag if the intent was to retain the token-budget FM for a
future probabilistic step.

## The complete edit map (across the 3 coupled files + 2 prose updates)

1. **`steps.jsonld`** — delete 5 Step objects (3,5,6,7,9); shrink
   `excluded_from_yaml` to `[gate-founder-confirmation, publish-github-release]`;
   change `detect-pending-changesets` (read main) + `commit-bump-as-bot` (commit
   on main); remove deleted-FM ids from any surviving `handles_failures` (none
   survive on kept steps — clean); update `_about` (15→10).
2. **`workflow.jsonld`** — remove 5 steps from `hasStep`; rewire `edges`
   (drop the back-edge JT-7 cycle + all promotion edges; new linear path
   detect→preflight→compute→confirm→bump→changelog→commit→tag→publish→emit);
   update `_about` + `description` prose (15→10, new arrow sequence).
3. **`failuremodes.jsonld`** — delete the 4 FM objects; update `_about`.
4. **`triggers.jsonld`** — trigger becomes "operator invokes /sulis:release on
   main (or cadence)", not "open dev→main PR".
5. **`templates/workflows/release-on-merge.yml`** — remove the
   `# canonical:step:draft-pr-body-and-changelog` annotation + its
   `# canonical:failuremode:probabilistic-step-token-budget-exceeded` + the dead
   promotion YAML (open-PR / wait-for-checks / squash-merge logic). (The other 4
   deleted steps aren't annotated, so no annotation churn for them — but their
   dead YAML should go.)
6. **`.github/workflows/release-on-merge.yml`** — remove the same dead promotion
   logic so the LIVE robot performs the 10-step trunk flow; verify by read-through.

## Verification (blocking gate)

`check-canonical-drift.py` (mirror↔template) exit 0 + existing
`plugins/sulis/scripts/tests/` green, on branch-ci. "Shipped" = that gate green.

## WP shaping note for plan-work

The drift gate **couples** all of this — you cannot merge the mirror change
without the matching template change, or branch-ci goes red, and the whole thing
ships as ONE PR into main anyway. So this is **not** parallel independent tasks.
Right shape: a small number of **sequential** WPs (canonical mirror → imperative
templates → drift-green verify) landing as one atomic PR, never leaving the
release flow bricked mid-way (the core constraint).
