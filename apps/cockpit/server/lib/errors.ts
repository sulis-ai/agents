// WP-004 — typed errors for the cockpit server's lib layer.
//
// Errors live here (not co-located with the functions that throw them)
// so route handlers can catch by class without importing the lib
// implementation modules. WP-006/007/008 will add a small mapper from
// these classes to HTTP responses.

/**
 * Thrown by `safeJoin` when a user-supplied path resolves outside the
 * worktree root, either via lexical escape (`..`), absolute path
 * injection, symlink target outside the root, an empty path, or any
 * other input that would let an HTTP caller read a file the cockpit
 * is not authorised to expose. The `code` is the stable identifier
 * route handlers translate into the `400 path outside worktree`
 * response defined in TDD §13.2.
 */
export class PathOutsideWorktreeError extends Error {
  readonly code = "PATH_OUTSIDE_WORKTREE";

  constructor(message: string) {
    super(message);
    this.name = "PathOutsideWorktreeError";
  }
}
