---
founder_facing: false
---

# Spec — Simplify the release robot to trunk-based (Model A cutover, step 4)

**Change:** CH-01KT4K · refactor

## Intent

Finish the Model A cutover by re-modelling the release-train Workflow from the
two-branch (`dev→main` promotion) shape to a trunk-based (`main`-only) shape.
The release stops being a *merge between branches* and becomes a *bump + tag on
the trunk*. Authoritative end-state: `docs/trunk-based-release-workflow-remodel.md`
(on `main` as of `3da681c`).

This change is the **agents-repo half** only (founder decision, recon): the
vendored mirror + the imperative workflow(s) + the drift gate. The canonical
edit in `sulis-ai/plugins` (`.specifications/business-dna/instances/release-train/`)
is a **separate paired change**; until it lands, the vendored mirror in this repo
is the working source of truth.

## Scope

**1. Vendored canonical mirror** — `plugins/sulis/instances/release-train/`
(re-model to match the guide's 10-Step end-state):

- **Delete 5 Steps** from the current 15 (`steps.jsonld`, and their ordering in
  `workflow.jsonld`):
  - `preflight-cross-branch-drift` (no cross-branch ancestry on a trunk)
  - `draft-pr-body-and-changelog` (no release PR; changelog drafting consolidates
    into `compute-next-version` / `write-changelog-entry` so
    `gate-founder-confirmation` still shows version + changelog)
  - `open-release-pr` (no `dev→main` PR)
  - `wait-for-checks-and-mergeability` (CI gating moves to the per-feature PR into `main`)
  - `squash-merge` (the `dev→main` squash that diverged the branches)
- **Delete 2 FailureModes** (`failuremodes.jsonld`):
  - the cross-branch / ancestry-drift guard
  - the auto-back-merge failure mode
- **Keep 2 FailureModes** (still real on a trunk):
  - the robot loop-guard (`actor == github-actions[bot]`)
  - `bot-tag-doesn't-trigger-release-prod` (GitHub Actions platform-contract grounded)
- **Change 2 Steps:**
  - `detect-pending-changesets` reads **main's** `.changesets` (since last tag)
  - `commit-bump-as-bot` → commits **directly to `main`** (no promotion PR);
    conceptually `commit-bump-on-main`
- **Trigger** (`triggers.jsonld`): release triggered by operator invoking
  `/sulis:release` on `main` (or a cadence), not by opening a `dev→main` PR.
- Net: **15 → 10 Steps**, 2 FailureModes deleted.

**2. Imperative workflow(s)** — simplify to match the re-modelled Workflow:
drop the promotion-PR + back-merge + ancestry-guard logic; keep
bump-on-push-with-changesets + tag. Two files in this repo, updated in lockstep:
- `plugins/sulis/templates/workflows/release-on-merge.yml` (the **annotated**
  template, 14 `canonical:` annotations — the file the drift gate reads)
- `.github/workflows/release-on-merge.yml` (the **live** workflow that actually
  runs releases; 0 annotations; not seen by the drift gate — kept correct by hand)

**3. Drift gate** — `check-canonical-drift.py` (mirror ↔ template) must pass
green in `branch-ci`.

## Non-goals

- **Editing the canonical in `sulis-ai/plugins`** — separate paired change.
- **Re-applying `branch-ci` as a required check on `main`** (guide line 67) — a
  branch-protection config change, not a workflow-file edit; tracked as
  follow-up.
- **Wiring `gh release create` into `publish-github-release` (#148)** — adjacent;
  out of scope unless trivially co-located.
- **The §8 first-run changeset reconciliation** — a one-off precondition already
  satisfied (0.89.0 shipped, default branch already `main`), not part of the
  steady-state Workflow.
- **Removing the now-dead `.github/workflows/promote-dev-to-main.yml`** etc. —
  dead-but-harmless under trunk; hygiene, not this change (capture separately if
  wanted).

## Acceptance

- `plugins/sulis/instances/release-train/{steps,workflow,failuremodes,triggers}.jsonld`
  reflect the 10-Step / 2-deleted-FailureMode shape; the brain rubric / dna-runner
  validates the instance as well-formed.
- Both `release-on-merge.yml` files contain no promotion-PR, back-merge, or
  ancestry-guard logic; they bump-on-changesets and tag directly on `main`.
- `check-canonical-drift.py --instance-dir plugins/sulis/instances/release-train
  --yaml-path plugins/sulis/templates/workflows/release-on-merge.yml` exits 0.
- `branch-ci` is green on the change PR (drift gate + existing tests, incl.
  `test_branch_ci_has_drift_check.py`).
- The live `.github/` workflow, read end-to-end, performs exactly the 10-Step
  trunk flow with no dead `dev→main` branches of logic that could fire.

## Constraints

- **LIVE release machinery** — 0.89.0 just shipped through this pipeline. Go
  step by step; verify each edit; never leave the release flow in a bricked
  intermediate state on `main`. Prefer mirror → template → drift-check → live
  ordering so the gate confirms parity before the live file is trusted.
- **Platform touch (GitHub Actions, write/deploy)** — the release workflow pushes
  commits, tags, and GitHub Releases via GitHub Actions. Design stage must ground
  the GitHub Actions Platform Contract (notably the
  `bot-tag-doesn't-trigger-release-prod` behaviour and the `actor==bot` loop-guard)
  before changing the trigger/commit/tag steps.
- **COUPLED invariant** — canonical (mirror, here) + imperative (template) must
  agree or `check-canonical-drift.py` flags. Edit them together, never one alone.
- **Ship via the trunk flow** — PR into `main`, branch-ci-gated. No `dev`.
- Keep the two kept FailureModes intact; their deletion would re-introduce the
  loop / downstream-trigger bugs they guard.

## Verification Plan

- **Drift gate (blocking):** `check-canonical-drift.py` mirror↔template exit 0 in
  branch-ci — the load-bearing structural proof that imperative matches canonical.
- **Instance validity:** brain rubric / dna-runner validates the re-modelled
  instance (well-formed Steps/FailureModes/Trigger graph; no dangling refs).
- **Existing test suite:** `plugins/sulis/scripts/tests/` (incl.
  `test_branch_ci_has_drift_check.py`, drift-detector unit tests) stays green.
- **Manual read-through of the live `.github/` workflow:** confirm the 10-Step
  path with no reachable promotion/back-merge/ancestry logic.
- **Definition of done is the blocking gate:** branch-ci on `main` (drift + tests).
  "Shipped" is claimed only when that gate is green, not on a local pass.
- **Out of scope to verify here:** an actual end-to-end release run (would mint a
  real tag); covered by the next real release, not by this change's CI.
