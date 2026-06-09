# fix: scope run-all worktree cleanup to the current change (no name-glob)

Closes #211, #253.

## Problem

During a run-all integration pass, a session improvised a grep-based worktree
cleanup (`git worktree list | grep …`) that matched and **removed 4 worktrees
belonging to OTHER in-flight changes** (different change IDs). They were
recovered from their intact branches, but uncommitted work in them would have
been lost (#211; #253 is the general re-statement).

## Root cause + state on arrival

All *scripted* worktree removal is already scoped — `wpx-worktree remove`
takes an explicit `--worktree-path`, and `wpx-step12 wrap` passes the per-WP
path it created. There is no scripted glob-remove. The over-reach was a
session **improvising** an ad-hoc enumerate-and-glob cleanup during
integration, which the run-all orchestration prose didn't explicitly forbid.

## Fix

Add an explicit **MUST guardrail — Step 14.7 "Worktree cleanup safety"** to
`run-all` SKILL.md, right after the per-WP Step-12 wrap:

- Remove ONLY worktrees this batch created for the current change, by the
  explicit `--worktree-path` already held (co-located under
  `~/.sulis/changes/<this-change-id>/`).
- NEVER enumerate + name-glob the worktree list — other changes' worktrees
  live under their own `~/.sulis/changes/<other-id>/` parents and are never
  yours to remove.
- ✓ `wpx-worktree remove --worktree-path <path>` vs
  ✗ `for w in $(git worktree list | grep wp- …); do git worktree remove "$w"; done`
- Idempotent: an already-gone path is fine; never widen the match to "find" it.

Composes with the #106 base-pin discipline (a batch operates entirely within
its own change's worktree parent).

## Tests

Orchestration-prose guardrail — no executable test (the scripted removal paths
are already scoped by construction; this prevents a session re-improvising the
unsafe glob). Verified by the existing `Canonical-vs-implementation drift` CI
gate that the SKILL change is well-formed.
