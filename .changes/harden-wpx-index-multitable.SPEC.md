---
founder_facing: false
---
# Spec — harden wpx-index for multi-table per-kind INDEX (closes #50)

**Closes:** [#50](https://github.com/sulis-ai/agents/issues/50)
**Primitive:** harden

## Problem (verified)

Contract-first decompose (#33–#37) produces a per-kind multi-table
INDEX. `parse_index_md` already iterates all sub-tables (so `status`,
`wpx-train`, and the run-all read-path work). But four subcommands use
`_find_wp_table`, which returns only the FIRST `| ID | Title |` table:

- `flip-status`, `set-status` — write the status cell
- `propagate-blocked` — BFS-marks dependents blocked
- `list-ready` — computes the ready set

On a multi-table INDEX, `flip-status WP-AJ-DC-01` reports "not found"
because the resolver returned a different sub-table (the platform
agent's exact blocker).

## Verified data-flow facts (from reconnaissance)

1. **Frontmatter `dependsOn` is the complete, uniform, executable-
   dependency set.** Backend `WP-AJ-003` has
   `dependsOn: [WP-AJ-002, WP-AJ-DC-01]` (includes its data contract).
2. **The INDEX dep columns are heterogeneous display variants** — the
   visual-contract sub-table carries a "Data contract" column (an
   informational pairing, NOT a readiness dependency: `WP-AJ-VC-01`
   correctly has `dependsOn: []` — it gates the frontend, depends on
   nothing executable). So deps CANNOT be read uniformly from the
   table; they MUST come from frontmatter.
3. **Live status lives in the INDEX cell** (written by flip-status);
   frontmatter `status:` is the seed. So status reads stay
   INDEX-sourced, but must span all sub-tables.

## Fix

### New helpers (in wpx-index)

- `_find_all_wp_tables(text) -> list[(start, end, table_text)]` —
  every `| ID | Title |` table with a Status column, document order.
  (`_find_wp_table` kept as the first-match shim.)
- `_load_deps_from_frontmatter(paths, known_wps) -> dict[id, list[id]]`
  — enumerate `paths.wp_dir.glob("WP-*.md")`, read each frontmatter's
  `dependsOn`, normalise short refs via `_normalise_wp_reference`.
  Returns `{}` when no WP files exist (pure-INDEX fixtures) so callers
  fall back to table deps (single-table back-compat).
- `_collect_status_across_tables(text) -> dict[id, str]` — iterate all
  sub-tables, `resolve_wp_columns` per table, collect id→status.

### Rewired subcommands

- **`flip-status` / `set-status`**: iterate `_find_all_wp_tables`; find
  the sub-table containing the WP; flip its status cell; rewrite that
  sub-table. Error only if the WP is in NONE of the tables.
- **`list-ready`**: status from `_collect_status_across_tables`; deps
  from frontmatter (fallback: per-table "depends" column when no WP
  files). Ready = stored-pending WP whose every dep is done.
- **`propagate-blocked`**: same status + deps sourcing; BFS the
  transitive dependents; write `dependency_blocked` into whichever
  sub-table each dependent lives in.

### Back-compat guarantee

Single-table INDEX → `_find_all_wp_tables` returns a 1-element list →
behaviour byte-identical. Deps-from-frontmatter falls back to table
deps when WP files are absent, so existing INDEX-only test fixtures
are unaffected.

## How we'll know it's done

- New `test_wpx_index_multitable.py`:
  - flip-status finds + flips a WP in the 2nd/3rd sub-table
  - flip-status errors when WP in no table
  - list-ready spans all sub-tables; deps from frontmatter; a WP whose
    dep (in another sub-table) isn't done is NOT ready
  - propagate-blocked marks a dependent in a different sub-table
  - visual-contract WP with `dependsOn: []` is ready regardless of its
    "Data contract" column pairing
- Existing single-table tests (`test_wpx_index_columns.py`,
  `test_wpx_index_status_vocab.py`, `test_visual_contract_gate.py`,
  all `test_wpx_train_*`) still pass — regression pin.
- End-to-end: `wpx-index flip-status --wp WP-AJ-DC-01` against the
  platform's actual multi-table INDEX succeeds (dry-run / temp copy).
- Full suite green; compile clean.
- Step 4.5 review gate PASS.

## What to avoid

- **Do NOT treat the visual-contract "Data contract" column as a
  readiness dependency.** It's informational pairing; the VC's real
  deps are in frontmatter `dependsOn` (empty for VCs).
- **Do NOT change `parse_index_md`** — it's already multi-table-aware;
  just regression-pin it.
- **Do NOT make flip-status write frontmatter** — live status is the
  INDEX cell (computed-status logic in wpx-train depends on this
  separation). Out of scope.
- **Do NOT break single-table behaviour** — every existing fixture +
  test must pass unchanged.

## References

- `plugins/sulis/scripts/wpx-index` — the 4 subcommands + `_find_wp_table`
- `plugins/sulis/scripts/_wpxlib.py` — `parse_index_md` (already
  multi-table), `resolve_wp_columns`, `_normalise_wp_reference`,
  `read_frontmatter`, `paths.wp_dir`
- Issue #50; the platform INDEX at
  `platform-change-create-agent-journey/.architecture/agent-journey/work-packages/INDEX.md`
