# fix: wpx-index flip-status recomputes Status Summary counts

Closes #143.

## Problem

After `wpx-index flip-status WP-001 --to done`, the WP row read `done` but the
`## Status Summary` table still read `pending: N, in_progress: 0, done: 0`.
The summary drifted from the row truth — anyone reading the INDEX (or any
tool aggregating from the summary) saw a stale picture.

## Fix

Add `_rewrite_status_summary(text)` which recomputes counts from current WP
cells (across all sub-tables per #50) and rewrites only the Count column.
Preserves the existing summary's row order + status set — projects that
track a narrow set (pending / in_progress / done / blocked) keep their lean
summary; projects that extend keep the extra rows. Silent no-op when no
`## Status Summary` section exists.

Wired into `cmd_flip_status` immediately after the row update + before
`_write_index`, so the row and summary are written atomically.

## Tests

- `test_flip_status_recomputes_summary_counts` — RED before fix.
- `test_flip_status_summary_preserves_extra_statuses` — RED before fix.
- `test_flip_status_no_summary_section_is_noop` — pinned silent no-op.
- Full wpx-index suite green (41 passed).
