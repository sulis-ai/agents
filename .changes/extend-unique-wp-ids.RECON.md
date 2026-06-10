# Recon — extend-unique-wp-ids

Stage 0 completed at: 2026-06-10T06:26:48Z

## What's already here (the seam this change extends)

- **Parser (`_wpxlib.py:parse_index_md`)** is column-position based — it
  reads whatever string sits in the ID column, so it already stores a
  prefixed id fine. BUT its row-filter `if not wp_id.startswith("WP-"):
  continue` (line ~1801) would SILENTLY DROP a `CH-HANDLE-WP-NNN` row.
  This is the load-bearing back-compat seam.
- **`_normalise_wp_reference` (line ~1730)** uses `ref.startswith("WP-")`
  to detect an already-full id (Depends On / Blocks columns). Prefixed ids
  start with `CH-` → needs widening. Suffix-match logic already tolerant.
- **Branch refs already namespaced per-change** by PR #283 (`_branch_name`,
  `resolve_wp_branch`, `change_scope` threading). This change does the same
  for the *id label*; the NNN sequencing logic itself does not change.
- **Filename convention** `WP-{ID}-{slug}.md` (`_wp_slug_from_file`) — glob
  is `{wp_id}-*.md`, so it follows the id automatically once the id changes.
- **Mint path** (the authored example/canonical rows) lives in
  `skills/plan-work/references/work-package-template.md`,
  `skills/design/SKILL.md`, `agents/engineering-architect.md`,
  `agents/orchestrator.md`, `agents/executor.md`.
- **Standards to reconcile:** WORK_PACKAGE_STANDARD (id row) +
  change-work-standard (CW-04). Supersede the parked
  canonicalise-cross-wp-ids effort (do not duplicate).
- **Tests:** `scripts/tests/unit/` (test_wpx_index_*, test_compute_wp_status*,
  test_wpx_train_branch_resolution, test_wpx_wp) need prefixed-id fixtures.

## Arrival check
RC-02 (main requires branch-ci) reports "not required" — standing repo
condition (branch protection unavailable on this plan), not introduced by
this change. Does not block.

See `plugins/sulis/agents/sulis.md` "Change context" for stage-inference.
