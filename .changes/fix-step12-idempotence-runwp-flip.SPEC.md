# fix: wpx-step12 wrap is idempotent on replay + run-wp pre-flips status

Closes #142.

## Problem

On CH-01KT48, `wpx-step12 wrap` failed twice in a row:

1. **First** — `flip-status --expected in_progress` rejected the WP because
   the status was still `pending`: the single-WP `run-wp` path never flipped
   `pending → in_progress` as the executor does in `run-all`.
2. **Second** — after a manual flip to `in_progress`, `append-evidence`
   rejected the now-present `## Acceptance Evidence` section: wrap has no
   `--force`, so the partial first attempt left the WP in a state requiring
   manual `flip-status` + `git worktree remove`.

## Fix

Three small changes make the wrap safely replayable:

1. **`wpx-wp append-evidence`** — existing `## Acceptance Evidence` section
   becomes a success no-op (`already_present: true` in the result), not an
   error. The first-write evidence is preserved.
2. **`wpx-index flip-status`** — when the row is already at the target
   status, early-return success (`already: true`) regardless of
   `--expected`. The original safety (catching misuse on a wrong-state WP)
   is preserved when the row is NOT already at target.
3. **`run-wp` SKILL.md** — explicit `pending → in_progress` flip step in
   Step 0a (before executor dispatch), making the single-WP path symmetric
   with `run-all` so Step 12.2's `--expected in_progress` doesn't trip on
   a still-`pending` WP. The flip is idempotent (#2) so it runs
   unconditionally.

## Tests

- `tests/integration/test_wpx_step12_idempotence.py`:
  - `test_step12_wrap_is_idempotent_on_replay` — second wrap returns ok;
    `already_present` + `already` flags surface in the summary; only ONE
    evidence section in the WP file.
  - `test_step12_wrap_retries_after_pending_state` — L2 trigger: first wrap
    fails at Step 12.2 (pending), manual flip + replay lands cleanly with
    no duplicate evidence.
- Both RED before the fix.
- Full scripts suite: 1852 passed, 0 regressions from this change.
