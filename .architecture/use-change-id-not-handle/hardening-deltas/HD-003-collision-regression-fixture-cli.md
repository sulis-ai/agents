---
id: HD-003
title: 26-collision regression fixture + cross-verb self-resolution (CLI)
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
status: proposed
severity: medium
pillar: proof
source: spec:fix-use-change-id-not-handle#scope-5
findings: [P-01]
scenarios: [7]
primitive: REINFORCE-Test
---

## Gap

`test_sulis_change_safe_resolution.py` unit-tests the matcher in isolation. There
is no regression that **reproduces the live collision state** (26 colliding
handles, one shared by 4 changes) in a throwaway fixture store and proves that,
with all of them present, **every change resolves to itself across all four
verbs** (`recreate`, `mark-shipped`/ship, `nuke`, focus-binding). Per SPEC
Verification Plan §3 the fixture must build its own temp store + git worktrees
(no dependence on the developer's `~/.sulis`).

## Failing characterisation test (proves the gap)

```python
def test_every_colliding_change_resolves_to_itself_across_all_verbs(collision_fixture):
    # collision_fixture seeds a temp SULIS_STATE_DIR with 26 colliding handles
    # (incl. one handle shared by 4 changes), each with a real branch + record.
    for c in collision_fixture.all_changes():
        # recreate (HD-001 path): resolves by id
        assert recreate_by_id(c.change_id).branch == c.branch
        # ship/mark-shipped: safe matcher resolves the exact id
        assert resolve_ship_target(handle=c.handle, change_id=c.change_id) == c.change_id
        # nuke (HD-002 path): exact id or refusal — never a sibling
        assert resolve_nuke_target(change_id=c.change_id)["change_id"] == c.change_id
        # focus/session-binding: SULIS_CHANGE_ID resolves to self
        assert resolve_current_change_for(c.change_id).change_id == c.change_id

def test_ambiguous_handle_lists_candidates_and_refuses(collision_fixture):
    shared = collision_fixture.handle_shared_by_four()   # CH-XXXXXX → 4 changes
    err = run_cli(["nuke", "--handle", shared], expect_fail=True)
    assert "matches 4 changes" in err.stderr
    assert err.json["candidates"] and len(err.json["candidates"]) == 4
```

Today these fail to compile/run (no `collision_fixture`, no `recreate_by_id`,
no cross-verb assertion). RED by absence — the fixture and helpers do not exist.

## Change (ADDED)

- **ADDED** a `collision_fixture` pytest fixture under
  `plugins/sulis/scripts/tests/` that synthesises a temp `SULIS_STATE_DIR` with
  26 colliding handles (mirroring the live `CH-01KSNX`→4 case), each change
  carrying a distinct ULID, a real branch, and a record. Builds temp git
  worktrees so resolution exercises real branch/worktree logic.
- **ADDED** the cross-verb self-resolution suite + the shared-by-four
  disambiguation test above.

## Definition of Done

- RED: suite committed and observed red (fixture/helpers absent).
- GREEN: with HD-001 + HD-002 in place, every colliding change resolves to
  itself across all four verbs; the shared-by-four handle yields a 4-candidate
  refusal.
- BLUE: fixture builders are reused (no copy-paste per test); the fixture is
  self-contained (passes from a fresh clone, zero prior `~/.sulis` state).
