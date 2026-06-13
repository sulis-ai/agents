---
founder_facing: false
---
# Spec — De-branch-scope the brain: move it to the user-level settings home

**Change:** CH-6XVHA0 · refactor

## Intent
Today the brain's *default* location resolves to `<repo_root>/.brain/instances`.
When a change runs inside its own per-change worktree, `repo_root` IS the
worktree, so the brain is created **inside the throwaway workspace** and is lost
when the worktree is removed at ship. This leaves the capture/recall loop open:
ideas, decisions, requirements and scenarios captured mid-change don't persist
across changes.

Move the brain out of the worktree and tie its default to the same user-level
home the product/project settings already use (`~/.sulis`), namespaced **per
project**, so captures survive the change that made them and accumulate across
all work on a project.

## Scope
- Change the *default* branch of the single brain-location resolver
  (`plugins/sulis/scripts/_brain_location.py` → `brain_base_dir`) from
  `<repo_root>/.brain/instances` to a user-level, per-project location under the
  settings home (`~/.sulis`), namespaced by tenant/project the same way the
  product store is (`~/.sulis/instances/{tenant_id}/...`).
- Keep the override chain above the default exactly as-is and in the same order:
  explicit arg → `SULIS_BRAIN_BASE_DIR` env → repo-contract `brain_location`
  field → (new) user-level default.
- All existing call sites already route through `brain_base_dir`
  (`_brain_emit_helper.py`, `_change_emission.py`, `_verify_requirements.py`,
  `_seam_close_gate.py`); they inherit the new default with no call-site edits.

## Non-goals
- Building a migration tool that hauls data out of old per-worktree `.brain`
  folders. Those are ephemeral by nature; the fix is forward-looking. Anything
  already in the user-level brain (`~/.sulis/.brain`) is preserved by pointing
  at that home, not rebuilt.
- Changing the brain's on-disk schema, the emit helpers, or any entity shape.
- Changing the override mechanisms (env var, repo-contract field) — only the
  default they fall through to.
- Any user-visible UI work — this is internal plumbing.

## Acceptance
- A capture made while inside a change worktree (with no override set) lands in
  the user-level, per-project brain — NOT inside the worktree — and is still
  there after the worktree is removed at ship.
- Two different projects/tenants get distinct brains; captures from one do not
  appear in the other.
- The override chain still wins when set: an explicit path, `SULIS_BRAIN_BASE_DIR`,
  and a repo-contract `brain_location` each still take precedence over the new
  default, in that order.
- Nothing is orphaned: Sulis's own committed in-repo brain still resolves (via
  an explicit repo-contract `brain_location` setting), so the dogfood repo keeps
  reading its committed brain.
- All call sites continue to work unchanged (the resolver is the only edit).

## Constraints
- **Orphan nothing (MUST).** Changing the default must not silently strand any
  setup that relied on the old in-repo default. Sulis's own repo keeps its
  committed brain by setting `brain_location` in its repo-contract explicitly.
- Mirror the existing settings/product-store namespacing convention
  (`~/.sulis/instances/{tenant_id}/`) rather than inventing a new layout —
  default to the established convention (CP-01).
- Resolve the tenant/project identity the same way the product store already
  does; do not introduce a second source of truth for "which project am I."
- Keep `brain_base_dir` the single resolver — no second place that decides the
  brain's location (this change closes exactly that class of gap, per the
  module's own #127 history).
- Characterisation tests first (EP-07): the resolver has existing behaviour
  (override precedence) that MUST be pinned before the default branch changes.
