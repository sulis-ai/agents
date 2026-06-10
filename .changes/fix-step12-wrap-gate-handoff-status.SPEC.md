# fix: wpx-step12 wrap accepts step-7-complete on the gate-handoff path

Closes #267.

## Problem

In the `--enable-gate-handoff` train flow the calling session flips each WP to
`step-7-complete` before invoking the train, and `mark-gates-complete` returns
a `pending_step12` checklist to drive the wrap from there. But
`wpx-step12 wrap`'s Step 12.2 flip hardcoded `--expected in_progress`, so it
failed: `ERROR: WP WP-001 status is 'step-7-complete', expected 'in_progress'`.
The calling session had to do the wrap's three jobs (flip step-7-complete→done,
remove worktree, delete branch) by hand for every WP across the run.

## Fix

Add a `--from-gate-handoff` flag to `wpx-step12 wrap`. When set, the Step 12.2
flip expects `step-7-complete`; without it, `in_progress` (the legacy per-WP
path, unchanged). `flip-status` is already idempotent when the row is at the
target (`done`) per #142, so a replay is safe either way.

Wire the flag into the run-all SKILL's Step 14.6 `pending_step12` wrap
invocation, with a note explaining why it's required on the gate-handoff path.

## Tests

`tests/integration/test_wpx_step12.py` (2 new):
- `test_step12_wrap_from_gate_handoff_accepts_step_7_complete` — a WP at
  step-7-complete is rejected WITHOUT the flag (the #267 symptom) and succeeds
  WITH it.
- `test_step12_wrap_default_still_expects_in_progress` — the legacy
  in_progress→done path is unchanged.

Full step12 suite green (8 passed).
