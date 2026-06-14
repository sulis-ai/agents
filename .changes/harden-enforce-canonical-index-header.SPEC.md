# harden: enforce the canonical WP INDEX header on amend (not just emit)

Closes #307.

## Problem

SEA's decompose emitted a WP INDEX with a non-canonical header
(`| WP | Purpose | Delta | Sev | dependsOn | Parallel? |`); run-all
(`wpx-index` / `parse_index_md`) requires the canonical
`| ID | Title | Primitive | Status | Depends On | Blocks |` and failed mid-run
with "Could not find WP table (no | ID | header)". `validate_wp_index_header`
(#60) + the plan-work Step 9.5 lint (#103) already cover the **initial emit** —
but the drift can be reintroduced by a later amend / hand-edit that isn't
re-linted, so it still reached run-all.

## Fix

1. **Structural (amend-time guard):** `wpx-index add-wp` now runs
   `validate_wp_index_header` on the INDEX it reads, before inserting the row.
   An amend through the tooling against a drifted-header INDEX fails surgically
   with the canonical-header error instead of the cryptic mid-run failure.
   (add-wp appends into an existing canonical table, so this never blocks a
   legitimate first row.)
2. **Prose (raw hand-edit):** plan-work Step 9.5 now says to re-run
   `wpx-index lint` after ANY later INDEX amend — the tooling guard catches
   amends through `add-wp`; a raw hand-edit is only caught by re-linting.

## Tests

`tests/integration/test_wpx_index.py`:
- `test_add_wp_refuses_drifted_header` — add-wp against the exact
  `| WP | Purpose | Delta | … |` shape from CH-8BP0XN fails with the
  canonical-header error.
- `test_add_wp_accepts_canonical_header` — a canonical-header INDEX still
  accepts the amend.
44 wpx-index tests green.
