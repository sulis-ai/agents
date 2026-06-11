---
id: HD-002
title: Route nuke through the safe matcher; retire the dead head-prefix rung
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
status: proposed
severity: medium
pillar: armor
source: spec:fix-use-change-id-not-handle#scope-3
findings: [A-02]
scenarios: [4, 5, 6]
primitive: SUBSTITUTE-Replace
---

## Gap

`nuke` resolves each candidate's `change_id` through the **legacy**
`_resolve_change_id` chain (`plugins/sulis/scripts/sulis-change:1532`), whose
handle rung calls `_scan_state_dir_by_prefix(prefix=handle_tail)` (line
1366-1380, 1309). Since #101 handles are minted from the ULID **tail**
(`ulid[10:16]`) but the state-dir names are full ULIDs starting with the
**timestamp head**, the tail prefix can never match a dir name — the rung is
**dead** (the mint/lookup mismatch). It is masked by rung 0 (first-slug-match)
and the final >1-match refusal, so `nuke` is not currently unsafe, but it is
inconsistent with the safe `_changes_matching_handle` matcher that `recreate`
and `mark-shipped` already use, and the dead rung is a latent foot-gun.

The disambiguation candidate list (`_emit_ambiguous_match`) carries
change_id + branch + slug + stage; the SPEC asks for handle + **readable name** +
branch. Add the readable `intent`/name field for parity (Scenario 5).

## Failing characterisation test (proves the gap)

```python
def test_scan_state_dir_by_prefix_is_dead_for_tail_minted_handles():
    # A tail-minted handle's prefix is ulid[10:16]; the state dir is named by
    # the FULL ulid (starts with the timestamp head). The prefix scan must miss.
    cid = "01J000000022222222ZZZZZZZZ"   # head != tail
    handle = ulid_handle(cid)            # "CH-2222ZZ"-style tail
    make_state_dir(cid)
    note, found = _scan_state_dir_by_prefix(handle[3:])
    assert found is None                 # documents the dead rung (RED→characterised)

def test_nuke_resolves_tail_minted_handle_via_safe_matcher(tmp_change_store):
    # After the fix nuke must resolve a tail-minted handle the SAME way
    # recreate/mark-shipped do — via _changes_matching_handle, not the dead rung.
    c = one_change(handle_tail_minted=True)
    target = resolve_nuke_target(handle=c.handle)
    assert target["change_id"] == c.change_id   # FAILS if nuke depends on the rung
```

## Change (MODIFIED / REMOVED)

- **MODIFIED** `_resolve_nuke_target`: resolve candidates by
  `_changes_matching_handle(handle, list_all_changes())` for the `--handle`
  case (same matcher as `recreate`/`mark-shipped`), keep `--slug` matching,
  keep the >1-match refusal via `_emit_ambiguous_match`. Add `--change-id` to
  `nuke` for the unambiguous path (symmetry with HD-001).
- **REMOVED** `_scan_state_dir_by_prefix` and the dead handle rung inside
  `_resolve_change_id` (rung 1). `_resolve_change_id` keeps its slug/manifest
  rungs for the slug path. (Confirm no other caller — grep shows only
  `_resolve_change_id` references it.)
- **MODIFIED** `_emit_ambiguous_match`: add a readable name to each candidate
  (`name`/`intent` off the record) so the list reads handle + name + branch.

## Definition of Done

- RED: the two tests above committed; the dead-rung characterisation passes
  (documents current behaviour), the nuke-via-safe-matcher test is red.
- GREEN: `nuke` resolves via the safe matcher; dead rung removed; candidate
  list carries the readable name.
- BLUE: existing `nuke` slug/handle tests still pass; `mark-shipped` and
  `recreate` untouched-and-green (shared matcher behaviour unchanged).
