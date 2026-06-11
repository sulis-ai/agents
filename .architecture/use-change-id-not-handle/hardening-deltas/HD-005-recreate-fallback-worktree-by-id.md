---
id: HD-005
title: Key the recreate fallback worktree by change_id (defence-in-depth)
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
status: proposed
severity: low
pillar: form
source: spec:fix-use-change-id-not-handle#scope-1
findings: [F-02]
scenarios: [3]
primitive: REORGANISE-Refactor
---

## Gap

`change_worktree_path(repo_root, primitive, slug)` (`_wpxlib.py:4373`) composes
the **legacy sibling** worktree path from `{primitive}-{slug}`, not `change_id`.
Co-located worktrees are already id-keyed (`~/.sulis/changes/{change_id}/worktree`),
but `cmd_recreate` falls back to this slug-keyed path when git reports the branch
checked out nowhere. Two changes sharing primitive+slug would compute the **same**
fallback path. Live data shows 0 worktree-path collisions, so realised risk is
low — but it is the structural reason recreate must resolve and key by id
end-to-end, and it is the last residual way two changes could share a directory
(Scenario 3 defence-in-depth).

## Failing characterisation test (proves the gap)

```python
def test_recreate_fallback_worktree_path_is_change_id_keyed():
    # Two changes, same primitive+slug, distinct ids → distinct fallback paths.
    a = change(primitive="fix", slug="x", change_id=ULID_A)
    b = change(primitive="fix", slug="x", change_id=ULID_B)
    assert recreate_fallback_path(a) != recreate_fallback_path(b)  # FAILS today
```

Today both resolve to `<repo>-change-fix-x` → equal → RED.

## Change (MODIFIED)

- **MODIFIED** the recreate fallback to prefer the id-keyed co-located worktree
  dir (`change_worktree_dir(change_id)`) and only use the slug-keyed legacy path
  for changes whose record predates id-keyed worktrees (read off the record), so
  a shared primitive+slug can never collide for id-keyed changes.

## Definition of Done

- RED: test committed and observed red (paths equal today).
- GREEN: distinct ids → distinct fallback paths.
- BLUE: existing recreate worktree tests still pass; legacy slug-keyed changes
  (no co-located worktree) still recreate. **Characterisation test required**
  (REORGANISE primitive — confirm the existing recreate worktree behaviour is
  pinned before changing the path composition).

> **Opportunistic.** Bundle only if cheap alongside HD-001; otherwise capture as
> a follow-up. Not required to close any SPEC acceptance criterion (Scenario 3 is
> already green via id-keyed co-located worktrees + SULIS_CHANGE_ID binding).
