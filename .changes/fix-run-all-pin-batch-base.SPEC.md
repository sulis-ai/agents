# fix: run-all pins ONE base ref per batch

Closes #106.

## Problem

In the CH-01KSSV batch, parallel executors branched off inconsistent bases:
WP-001 / WP-002 cut their worktrees off the local change-branch tip while
WP-004 cut from `origin/dev` after an independent fetch. The calling
session then had to reconcile bases + back-integrate by hand before the
train. Each executor was resolving `--base-branch` independently rather
than receiving one pinned by the orchestrator.

## Fix

run-all SKILL.md gains an explicit **Step 7.5 (MUST)** between "mark WPs
in_progress" and the parallel dispatch:

- Resolve the base branch ONCE (the same CW-04 detection used at train
  time): `change/*` if the current branch is a change worktree, else
  `dev` after a fetch.
- Capture `BATCH_BASE_BRANCH` + `BATCH_BASE_SHA`.
- Substitute `BATCH_BASE_BRANCH` into every executor brief in Step 8, so
  every Agent prompt carries `--base-branch <BATCH_BASE_BRANCH>` on its
  `wpx-worktree create` call.

A reinforcing line is added to Step 8 itself ("every executor prompt in
this dispatch MUST include `--base-branch <BATCH_BASE_BRANCH>`") so the
constraint is visible at the dispatch point, not only at Step 7.5.

The executor agent's `wpx-worktree create` invocation already supports
`--base-branch <base>` (executor.md line 573), so no executor-side change
is needed — the wiring is entirely in the orchestrator's prompt
construction.

## Tests

Documentation-only orchestrator-instruction amendment — no executable
test. Verification is review + the existing `Canonical-vs-implementation
drift` CI gate that surfaces SKILL drift.
