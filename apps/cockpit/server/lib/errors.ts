// WP-004 / WP-006 / WP-007 — typed errors for the cockpit server's lib layer.
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

/**
 * Thrown by `readWorktreeTree` (WP-006) when the caller asks to list
 * the children of a path that exists but is not a directory — e.g. a
 * regular file. Route handlers translate this into a 400 so the client
 * can correct its request shape.
 */
export class NotADirectoryError extends Error {
  readonly code = "NOT_A_DIRECTORY";

  constructor(message: string) {
    super(message);
    this.name = "NotADirectoryError";
  }
}

/**
 * Thrown by `readWorktreeTree`, `readFileContents`, and other filesystem-
 * reading helpers when the resolved path does not exist on disk. Route
 * handlers translate this into a 404. We define our own class rather
 * than re-throwing the underlying `NodeJS.ErrnoException` so the route
 * doesn't have to inspect `err.code === "ENOENT"` and so the class
 * stays available even when a future implementation switches to a
 * non-fs source (e.g. an in-memory test double).
 */
export class NotFoundError extends Error {
  readonly code = "NOT_FOUND";

  constructor(message: string) {
    super(message);
    this.name = "NotFoundError";
  }
}

/**
 * Thrown by `readFileContents` (WP-007) when the resolved path is a
 * directory rather than a regular file. The route layer maps this to
 * `400 is a directory` — distinct from `404 not found` because the
 * path *does* exist; it is just not a thing the file endpoint can serve.
 */
export class IsADirectoryError extends Error {
  readonly code = "IS_A_DIRECTORY";

  constructor(message: string) {
    super(message);
    this.name = "IsADirectoryError";
  }
}
