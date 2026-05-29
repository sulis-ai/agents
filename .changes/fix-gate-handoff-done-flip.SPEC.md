# fix: gate-handoff completion surfaces the per-WP Step 12 wrap checklist

Closes #75.

## Problem

In the `wpx-train --enable-gate-handoff` flow, after `mark-gates-complete`
returns success the shipped WPs were merged on `dev` but their INDEX cache
cells stayed at `step-7-complete` and their executor worktrees + local
branches were left in place. The batched gate-handoff path never runs the
per-WP **Step 12 wrap** (acceptance evidence + INDEX flip + worktree removal +
branch delete) that the legacy per-WP path runs — so the calling session had
to `wpx-index set-status --to done`, `git worktree remove`, and
`git branch -D` by hand for every WP. Observed repeatedly across 6 train runs.

The wrap genuinely belongs to the calling run-all session: only it owns the
executor worktree paths (the train operates on its own clone and never sees
them). The gap was that the run-all batched gate-handoff path had no Step 12
wrap step after `mark-gates-complete`, and nothing handed the session a
concrete list of what to wrap.

## Fix (two halves — the lesson sanctioned "the run-all loop after it")

1. **`wpx-train mark-gates-complete`** (clean-success path): emit a
   machine-readable `pending_step12` checklist — one `{wp, branch}` per
   shipped WP — plus a `next_action` naming the follow-on. Pure record read;
   no git operations, preserving the subcommand's contract. (Skipped on
   `--critical-found` — those WPs got BLOCKERs, not a clean ship.)
2. **run-all SKILL.md Step 12.6**: an explicit, unmissable step that consumes
   `pending_step12` and runs `wpx-step12 wrap` + `git branch -D` per entry,
   mirroring the legacy per-WP Step 12.

## Tests

- `test_train_failure_paths.py::test_mark_gates_complete_emits_pending_step12_checklist`
  — asserts the clean-success envelope lists all shipped WPs + branches and a
  `next_action` (RED before the fix: the field didn't exist).
- Full scripts suite green (967 passed).
