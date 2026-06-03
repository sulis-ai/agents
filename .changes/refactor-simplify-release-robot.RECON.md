# Recon — refactor-simplify-release-robot

Stage 0 completed at: 2026-06-02T16:50:00Z

This marker's existence signals `/sulis:recon` has run for this change.

## What's here (and what isn't)

This change worktree is **sulis-ai/agents** only. The intent describes a
two-repo, four-part change. Here is the actual on-disk state vs. the intent's
assumptions — two mismatches matter.

### 1. The canonical source repo is NOT checked out locally
- Intent step (1): edit the canonical release-train Workflow in
  **sulis-ai/plugins** at `.specifications/business-dna/instances/release-train/`.
- That repo is not present anywhere under `/Users/iain`. Cannot be edited from
  this worktree.
- The referenced guide `docs/trunk-based-release-workflow-remodel.md` is also
  NOT in this repo (presumably on sulis-ai/plugins main).
- **Consequence:** the canonical edit (step 1) is out-of-repo. This worktree can
  do steps (2) vendored mirror, (3) imperative workflow, (4) drift check.

### 2. There are TWO `release-on-merge.yml` files; intent names only one
- `.github/workflows/release-on-merge.yml` — 14,874 B, **0 `canonical:`
  annotations**. The workflow that actually RUNS on this repo. Self-contained
  (restored in HEAD commit `10d318b` "restore self-contained release-on-merge.yml").
  NOT checked by the drift gate.
- `plugins/sulis/templates/workflows/release-on-merge.yml` — 29,192 B, **14
  `canonical:` annotations**. The annotated template the drift gate reads.
- The drift gate (`branch-ci.yml` line ~118) compares:
  - `--instance-dir plugins/sulis/instances/release-train` (vendored mirror)
  - `--yaml-path plugins/sulis/templates/workflows/release-on-merge.yml` (template)
- So `check-canonical-drift.py` passing requires the **vendored mirror** and the
  **template** to agree. The live `.github/` copy is invisible to the gate but is
  the file that actually governs releases — it must be kept correct by hand.

## Targets in this repo
- Vendored mirror: `plugins/sulis/instances/release-train/` (workflow.jsonld,
  steps.jsonld, failuremodes.jsonld, tools.jsonld, triggers.jsonld, projects.jsonld)
- Drift-checked template: `plugins/sulis/templates/workflows/release-on-merge.yml`
- Live workflow: `.github/workflows/release-on-merge.yml`
- Drift gate: `plugins/sulis/scripts/check-canonical-drift.py` (+ `_canonical_drift/`)
- Design context: `.architecture/release-train/` (TDD.md, ARCH.yaml, adrs/, work-packages/)
- Related workflows: `promote-dev-to-main.yml`, `release-prod.yml`, `version-check.yml`

## Arrival check
- RC-01: default branch is `main`, expected `dev`. This is the OLD two-branch
  model the checker still encodes; retiring it IS this change. Expected, not a
  blocker (dead-but-harmless / downstream hygiene per intent).

## Scope decision (founder, 2026-06-02)
**Agents repo only, now.** This change does steps (2) vendored mirror, (3)
imperative workflow, (4) drift check. The canonical edit in sulis-ai/plugins is
a SEPARATE paired change. The vendored mirror here becomes the working source of
truth until sulis-ai/plugins catches up.

Imperative handling: update ALL THREE in lockstep to stay consistent and keep
the gate honest —
- `plugins/sulis/instances/release-train/` (vendored mirror)
- `plugins/sulis/templates/workflows/release-on-merge.yml` (drift-checked template, 14 `canonical:` annotations)
- `.github/workflows/release-on-merge.yml` (live workflow that actually runs releases)

Gate to satisfy: `check-canonical-drift.py` (mirror ↔ template) must pass; verify
the live `.github/` copy by hand against the template.
