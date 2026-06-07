// WP-009 — mangle a worktree absolute path into Claude Code's
// `~/.claude/projects/<mangled-cwd>/` directory name.
//
// Per WP-009 Contract "Mangling rule" + ADR-004 §Context. Claude Code
// flattens the cwd into a single directory name by replacing EVERY
// non-alphanumeric character with `-` — not just `/`. Crucially that
// includes `.`: a worktree under `~/.sulis/…` becomes `…--sulis…`
// (the `/` and the `.` each contribute a dash → a double dash).
//
// This is load-bearing: change worktrees live at
// `~/.sulis/changes/<id>/worktree`, a DOTTED path. The earlier rule
// replaced only `/`, so it looked for `…-.sulis…` (dot kept) while
// the real dir is `…--sulis…` — the directory never matched and the
// app reported "no Claude session yet" for every change even though
// the transcripts were on disk. (CH-01KT50.)
//
// The downstream `locateTranscripts` verifier still checks
// `record.cwd === worktreePath`, so over-broad mangling can never
// render the WRONG thread — the worst case stays "not found".
// See `.architecture/cockpit-mvp/adrs/ADR-004-transcript-to-change-association.md`.

/**
 * Mangle an absolute worktree path into the directory-name shape
 * Claude Code uses under `~/.claude/projects/`.
 *
 * Examples:
 *   `/Users/iain/Documents/repos/foo`
 *     → `-Users-iain-Documents-repos-foo`
 *   `/Users/iain/.sulis/changes/01KT74/worktree`
 *     → `-Users-iain--sulis-changes-01KT74-worktree`   (note `--`)
 *
 * Pure function; no I/O. Existing hyphens map to themselves.
 *
 * See ADR-004 (`.architecture/cockpit-mvp/adrs/ADR-004-transcript-to-change-association.md`).
 */
export function mangleCwd(absoluteWorktreePath: string): string {
  return absoluteWorktreePath.replace(/[^a-zA-Z0-9]/g, "-");
}
