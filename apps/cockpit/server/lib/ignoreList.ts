// WP-006 — default ignore list for worktree tree readers.
//
// A small, named, public set so future additions are visible and
// testable. The list is applied by NAME MATCH (not glob): a file
// literally named `node_modules` at any depth is skipped.
//
// WP-009 (transcripts) may also reuse this set; don't duplicate the
// names elsewhere.

export const DEFAULT_IGNORE: ReadonlySet<string> = new Set([
  "node_modules",
  ".git",
  ".DS_Store",
]);
