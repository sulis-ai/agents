# SPEC — fix: wpx-train abort (NameError) + roll back step-7-shipping on early error

> Change: `change/fix-fix-train-abort-and-rollback` (01KSQN295TRB8BM0B2CBF3M9MN)
> Primitive: `fix`
> Resolves: GitHub issue #62

## Context — two related failure-recovery bugs in `wpx-train`

### Bug 1 — `wpx-train abort` crashes (the supported recovery path is broken)
`wpx-train abort` raises `NameError: name 'TRAIN_HELD_STATUS' is not
defined` (cmd_abort, ~line 665), so there is currently **no working CLI
way** to abort/clean a stranded train — the only workaround is manually
`rm`-ing the train `.state.json`.

**Precise root cause (verified on current dev via AST analysis):**
`TRAIN_HELD_STATUS` is *used* in `plugins/sulis/scripts/wpx-train` at
lines ~390, 665, 668, 683 but is **not imported** — the
`from _wpxlib import (...)` block imports `TRAIN_DONE_STATUS`,
`TRAIN_BLOCKED_STATUS`, `TRAIN_ELIGIBLE_STATUS` but **omits
`TRAIN_HELD_STATUS`**. The constant *is* defined in `_wpxlib.py`
(`TRAIN_HELD_STATUS = "step-7-held"`, line 1470). So the fix is to add
`TRAIN_HELD_STATUS` to the import block — that resolves every use site at
once. (Do NOT redefine it locally; import the canonical one.)

### Bug 2 — no rollback of the step-7-shipping flip on an early error
When `wpx-train run` errors during the `rebasing` phase (before any
merge), it has *already* flipped the bundle WPs into the in-flight
`step-7-shipping` computed state but does **not** roll that back on error.
The stranded `train-runs/<train_id>.state.json` then makes
`compute_wp_status` / `queue-list` report the WPs as `step-7-shipping`, so
the next `run` reports `nothing_to_pack` (eligible_count 0) even though
the INDEX cells correctly say `step-7-complete`.

**Fix:** make `run` roll back the `step-7-shipping` flip (or — cleaner —
never set it until *past* the ref-sha/rebase guards, i.e. only once a
merge is actually about to happen) when it errors before any merge has
landed. The invariant: **if no merge SHA was produced, the run must leave
WP statuses exactly as it found them.**

## The fix

1. Add `TRAIN_HELD_STATUS` to the `from _wpxlib import (...)` block in
   `wpx-train` so `abort` (and the other use sites) stop NameError-ing.
2. Make `run` transactional w.r.t. the step-7-shipping flip: roll it back
   on any error before the first merge, OR defer setting it until past the
   ref-sha/rebase guards. Choose the minimum-change approach that
   guarantees the invariant above (per EL-04 minimum-change Decide).

## Definition of Done (Red → Green → Blue)

Train tests live under `plugins/sulis/scripts/tests/` (e.g.
`test_wpx_train_queue_list.py`, `test_compute_wp_status.py`, and any
`test_wpx_train*.py`). Use real fixtures where the existing train tests do.

**RED** (fail against current code):
1. **abort works.** Set up a train in the pre-merge `rebasing` phase (all
   merge SHAs null, nothing landed) and run `wpx-train abort`. Assert it
   exits 0 (no NameError) and clears/marks the train state so the WPs are
   no longer reported in-flight. Currently NameErrors → RED.
2. **rollback on early error.** Drive a `run` that errors during rebasing
   (before any merge — e.g. the gh ref-sha 404 / a rebase failure).
   Assert that afterward the bundle WPs are NOT stranded in
   `step-7-shipping` — `compute_wp_status` / `queue-list` still see them as
   eligible (`step-7-complete`), so a subsequent `run` does not report
   `nothing_to_pack`. Currently stranded → RED.

**GREEN** — implement both fixes so the tests pass.

**BLUE** — confirm the import is the canonical `_wpxlib` constant (no
local redefinition). If the rollback logic shares state-mutation code,
factor it cleanly rather than duplicating.

## Acceptance criteria
- [ ] `TRAIN_HELD_STATUS` imported from `_wpxlib` in `wpx-train`; `abort`
      no longer NameErrors (regression test for a pre-merge rebasing-phase
      abort).
- [ ] `run` leaves WP statuses unchanged when it errors before any merge
      (no stranded `step-7-shipping`); regression test proves the next
      `run` still sees the WPs as eligible.
- [ ] Full scripts suite green; no new lint/type errors.

## Out of scope
- Redesigning the train state machine — just fix the import + make the
  early-error path leave state clean.
- #60, #61, #63 — already shipped this batch.
