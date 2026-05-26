// WP-010 — shared worktree-root resolution.
//
// The change store's `worktreePath` is the path git itself recorded
// when `git worktree add` ran. On macOS, paths produced by `mkdtemp`
// (used by every integration test in this WP) include a `/var → /private/var`
// symlink that does not get followed by the store. The lib-level
// `safeJoin` realpaths the user-supplied path before its prefix check;
// if we pass the un-realpath'd worktree root, the prefix check fails
// for any subpath inside the worktree.
//
// Fix: realpath the worktree root ONCE per request before calling any
// lib function that uses safeJoin. Cheaper than realpath'ing each
// subpath, and gives a stable canonical root.
//
// This is one adopter on each of: tree, file, diff. 2-consumer
// threshold has fired → the helper is extracted to its own module
// (EP-03).

import { realpath } from "node:fs/promises";

import { NotFoundError } from "../lib/errors";

/**
 * Realpath-resolve the worktree root. Map ENOENT (the recorded
 * worktree no longer exists on disk) into a NotFoundError so the
 * error middleware translates it to a 404 — the WP-007/WP-006 spec
 * for "worktree not found" semantics.
 */
export async function resolveWorktreeRoot(
  worktreePath: string,
): Promise<string> {
  try {
    return await realpath(worktreePath);
  } catch (err) {
    if (isErrnoException(err) && err.code === "ENOENT") {
      throw new NotFoundError(`worktree not on disk: ${worktreePath}`);
    }
    throw err;
  }
}

function isErrnoException(err: unknown): err is NodeJS.ErrnoException {
  return (
    err instanceof Error &&
    typeof (err as NodeJS.ErrnoException).code === "string"
  );
}
