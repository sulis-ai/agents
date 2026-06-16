---
id: WP-005
title: "Defence-in-depth: recreate fallback worktree is keyed by change_id, not {primitive}-{slug}"
status: pending
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
kind: backend
primitive: REORGANISE-Refactor
group: REORGANISE
sequence_id: WP-005
dependsOn: [WP-001]
blocks: []
estimated_token_cost:
  input: 6k
  output: 5k
tdd_section: "§2 Form; HD-005"
adrs: []
hardening_delta: HD-005
characterisation_test: "test_recreate_fallback_worktree_pins_current_path_composition"
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_change_identity_resolution.py::test_recreate_fallback_worktree_path_is_change_id_keyed"
---

## Context

`change_worktree_path(repo_root, primitive, slug)` (`_wpxlib.py:4373`) composes
the legacy sibling worktree path from `{primitive}-{slug}`. `cmd_recreate` falls
back to it when git reports the branch checked out nowhere. Two changes sharing
primitive+slug would collide on the same path. Live data shows 0 such collisions
(low realised risk), so this is **opportunistic defence-in-depth** — the last way
two changes could share a directory (Scenario 3). Not required to close any SPEC
acceptance criterion. Depends on WP-001 (recreate-by-id makes the id available at
the fallback site).

## Contract

- MODIFY the recreate fallback to prefer the id-keyed co-located worktree dir
  (`change_worktree_dir(change_id)`) and use the slug-keyed legacy path only for
  records that predate id-keyed worktrees (detected off the record).

## Definition of Done

**Red** (REORGANISE → characterisation test first, MUST)
- `test_recreate_fallback_worktree_pins_current_path_composition` — pins the
  existing fallback behaviour before changing it.
- `test_recreate_fallback_worktree_path_is_change_id_keyed` — two changes, same
  primitive+slug, distinct ids → distinct fallback paths. Fails today (equal).

**Green**
- Distinct ids → distinct fallback paths.

**Blue**
- Existing recreate worktree tests pass; legacy slug-keyed changes (no co-located
  worktree) still recreate.

> **Schedule:** bundle with WP-001/WP-003 only if cheap; otherwise the executor
> may defer this WP (it closes no SPEC acceptance criterion). Marked low.
