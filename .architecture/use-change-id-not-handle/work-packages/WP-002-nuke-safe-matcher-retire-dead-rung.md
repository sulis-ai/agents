---
id: WP-002
title: "nuke resolves via the safe matcher; retire the dead head-prefix rung; readable name in candidate list"
status: pending
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
kind: backend
primitive: SUBSTITUTE-Replace
group: SUBSTITUTE
sequence_id: WP-002
dependsOn: []
blocks: [WP-004]
estimated_token_cost:
  input: 7k
  output: 6k
tdd_section: "§2 Form, §3 Armor; HD-002"
adrs: [ADR-001]
hardening_delta: HD-002
characterisation_test: "test_scan_state_dir_by_prefix_is_dead_for_tail_minted_handles"
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_change_identity_resolution.py::test_nuke_resolves_tail_minted_handle_via_safe_matcher"
---

## Context

`_resolve_nuke_target` (`sulis-change` ~line 1532) resolves each candidate's id
through the legacy `_resolve_change_id`, whose handle rung calls
`_scan_state_dir_by_prefix` (matches the tail-minted handle against full-ULID dir
names that start with the timestamp head → **dead** post-#101). Masked by rung 0
(first-slug-match) and the final >1-match refusal, so nuke is not currently
unsafe, but it is inconsistent with the safe matcher `recreate`/`mark-shipped`
use, and the dead rung is a latent foot-gun. The candidate list omits the
readable name the SPEC asks for (Scenario 5).

## Contract

- `_resolve_nuke_target`: for the `--handle` case, resolve via
  `_changes_matching_handle(handle, list_all_changes())` (the shared safe
  matcher); keep `--slug` matching; keep the >1-match refusal via
  `_emit_ambiguous_match`. ADD `nuke --change-id <ULID>` for symmetry (resolve
  the exact id directly).
- REMOVE `_scan_state_dir_by_prefix` and the dead handle rung from
  `_resolve_change_id` (confirm no other caller — grep shows only
  `_resolve_change_id`). Keep the slug/manifest rungs for the slug path.
- `_emit_ambiguous_match`: add a readable `name` (off the record `intent`/slug)
  to each candidate so the list reads **handle + name + branch**.

## Definition of Done

**Red** (REORGANISE → characterisation test first, MUST)
- `test_scan_state_dir_by_prefix_is_dead_for_tail_minted_handles` — pins current
  behaviour (tail handle's prefix never matches a head-named dir). Passes →
  characterises the dead rung before removal.
- `test_nuke_resolves_tail_minted_handle_via_safe_matcher` — fails if nuke
  depends on the dead rung; drives a tail-minted handle to its exact id.
- `test_nuke_ambiguous_handle_lists_handle_name_branch_and_refuses` — shared
  handle → refusal whose candidates carry handle + name + branch.

**Green**
- nuke resolves via the safe matcher; dead rung removed; candidate list enriched.

**Blue**
- Existing `nuke` slug/handle tests pass; `mark-shipped` + `recreate` untouched
  and green (shared-matcher behaviour unchanged). No dead code left
  (`_scan_state_dir_by_prefix` gone, no dangling references).
