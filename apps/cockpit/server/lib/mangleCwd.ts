// WP-009 — mangle a worktree absolute path into Claude Code's
// `~/.claude/projects/<mangled-cwd>/` directory name.
//
// Per WP-009 Contract "Mangling rule" + ADR-004 §Context: replace
// every `/` with `-`. A leading `/` becomes a leading `-`. Observed
// Claude Code behaviour on macOS — see
// `.architecture/cockpit-mvp/adrs/ADR-004-transcript-to-change-association.md`
// §Context for the rationale and §Consequences for the failsafe (the
// `cwd`-field verification step downstream protects against drift if
// the mangling rule ever changes).

/**
 * Mangle an absolute worktree path into the directory-name shape
 * Claude Code uses under `~/.claude/projects/`.
 *
 * Example:
 *   `/Users/iain/Documents/repos/foo`
 *     → `-Users-iain-Documents-repos-foo`
 *
 * Pure function; no I/O. The downstream `locateTranscripts`
 * verifier checks `record.cwd === worktreePath` to guard against
 * mangling-rule drift, so this helper can stay trivially simple.
 *
 * See ADR-004 (`.architecture/cockpit-mvp/adrs/ADR-004-transcript-to-change-association.md`).
 */
export function mangleCwd(absoluteWorktreePath: string): string {
  return absoluteWorktreePath.replace(/\//g, "-");
}
