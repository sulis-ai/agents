---
id: WP-001
title: "sulis-change recreate resolves by --change-id (unambiguous), handle stays a display label"
status: pending
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
kind: backend
primitive: SUBSTITUTE-Replace
group: SUBSTITUTE
sequence_id: WP-001
dependsOn: []
blocks: [WP-003, WP-005]
estimated_token_cost:
  input: 7k
  output: 6k
tdd_section: "§2 Form, §5 Components; ADR-001"
adrs: [ADR-001]
hardening_delta: HD-001
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_change_identity_resolution.py::test_recreate_accepts_change_id_and_resolves_exact_change"
---

## Context

`cmd_recreate` (`plugins/sulis/scripts/sulis-change` ~line 1998) resolves by
`--handle` (via the safe `_changes_matching_handle` matcher) or `--slug`, but has
**no `--change-id` entry point** (argparse `p_recreate`, ~line 1885). The cockpit
holds the unique id and needs to drive recreate by it (WP-003). Per ADR-001 the
unambiguous id must be a first-class selector, matching `nuke`/`mark-shipped`.

## Contract

- ADD argparse argument `recreate --change-id <ULID>`.
- `cmd_recreate`: when `--change-id` is given, resolve the record directly by id
  (`read_change_record(change_id)` / scan `list_all_changes()` for the exact id),
  derive `primitive`/`slug`/`branch` off that record. `--handle` and `--slug`
  paths unchanged (backward-compat: unambiguous handle resolves, ambiguous
  refuses via `_changes_matching_handle` + `_emit_ambiguous_match`).
- Validate the id (26-char Crockford via `validate_change_ulid`); a malformed or
  unknown id → clean `emit_error` (Q12 failure mode).
- The `recreate` JSON output keeps `handle` as a display field.

## Definition of Done

**Red**
- `test_recreate_accepts_change_id_and_resolves_exact_change` — two colliding-handle
  changes; `recreate --change-id <a.id>` resolves a's branch, never b's. Fails
  today with argparse `unrecognized arguments: --change-id`.
- `test_recreate_by_change_id_unknown_id_clean_error` — unknown id → `emit_error`,
  non-zero, no spawn/worktree side effect.

**Green**
- `--change-id` resolves the exact change; both tests pass.

**Blue**
- Existing `recreate --handle` / `--slug` tests still pass (backward-compat).
- Id resolution shares the record lookup with `mark-shipped` (no copy-paste — if
  a `resolve_record_by_id` helper isn't already shared, extract it; 2-consumer
  threshold met across recreate + mark-shipped).
