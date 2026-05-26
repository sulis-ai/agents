// WP-004 — path-sanitisation utility for the cockpit's HTTP surface.
//
// TDD §13.2 (path traversal MUST), verbatim:
//
//   Every endpoint that accepts a `path` query parameter (`/tree`,
//   `/file`, `/diff`) sanitises it:
//     1. The change-id resolves to a worktree root (absolute path)
//        via the change store.
//     2. The path is `path.normalize`'d and
//        `path.resolve(worktreeRoot, userPath)`'d.
//     3. The resolved path must start with `worktreeRoot + path.sep`,
//        else 400 `path outside worktree`.
//     4. Symlinks inside the worktree are followed only if their
//        target also resolves inside the worktree (use `fs.realpath`
//        + the same prefix check).
//
// This module is the single chokepoint. Per WP-004 Blue spec, every
// other call site in apps/cockpit/ that needs a worktree-relative path
// goes through `safeJoin` — no other module calls `fs.realpath` directly.

import { realpath } from "node:fs/promises";
import {
  dirname,
  basename,
  normalize,
  resolve,
  sep,
  isAbsolute,
} from "node:path";

import { PathOutsideWorktreeError } from "./errors";

/**
 * Resolve `userPath` relative to `worktreeRoot`, normalise it, and
 * (where the leaf exists) realpath-resolve it so symlink targets are
 * checked. Throws `PathOutsideWorktreeError` if the resolved path
 * is not inside `worktreeRoot`.
 *
 * The pre-realpath prefix check catches lexical escapes (`..`) before
 * any filesystem touch. The post-realpath check catches symlinks whose
 * targets leave the worktree. On `ENOENT` (the leaf doesn't exist),
 * we fall back to realpath-ing the parent and re-checking — a file
 * may legitimately not exist (e.g. computing a diff for a file deleted
 * in the worktree, per TDD §7).
 *
 * `worktreeRoot` is trusted (comes from the change store);
 * `userPath` is the untrusted HTTP query parameter.
 */
export async function safeJoin(
  worktreeRoot: string,
  userPath: string,
): Promise<string> {
  if (userPath === "") {
    throw new PathOutsideWorktreeError("empty path");
  }
  if (userPath.includes("\0")) {
    throw new PathOutsideWorktreeError("path contains NUL byte");
  }
  if (isAbsolute(userPath)) {
    throw new PathOutsideWorktreeError(
      `absolute paths are not permitted: ${userPath}`,
    );
  }

  // Lexical normalisation + resolution. After this, `resolved` is an
  // absolute path with `..` segments collapsed (per Node's path semantics).
  const resolved = resolve(worktreeRoot, normalize(userPath));

  // Pre-filesystem prefix check — catches `..` escapes before any
  // filesystem syscall, so a malicious caller cannot probe for the
  // existence of arbitrary paths on disk.
  assertInside(worktreeRoot, resolved, userPath);

  // Symlink check: realpath the resolved path. If the leaf doesn't
  // exist (ENOENT), walk up to the deepest existing ancestor, realpath
  // that, then reattach the non-existent tail. This catches symlinks
  // on any *existing* ancestor while still permitting a non-existent
  // leaf (e.g. computing a diff for a file deleted in the worktree).
  const realResolved = await realpathWithMissingTail(resolved, userPath);
  assertInside(worktreeRoot, realResolved, userPath);
  return realResolved;
}

/**
 * Walk up `dirname` until `realpath` succeeds (the deepest existing
 * ancestor), then reattach the non-existent tail segments unchanged.
 * The pre-realpath lexical prefix check has already proved the
 * lexical resolved path is inside the worktree, so any non-existent
 * tail cannot escape; the realpath of existing ancestors catches
 * symlinks on those ancestors.
 */
async function realpathWithMissingTail(
  resolvedPath: string,
  userPath: string,
): Promise<string> {
  const missingTail: string[] = [];
  let current = resolvedPath;

  // Safety bound: a sane filesystem path on macOS/Linux has at most a
  // few hundred segments. We cap at 4096 iterations to avoid an
  // infinite loop if dirname ever stops shrinking (it stops at "/"
  // anyway).
  for (let i = 0; i < 4096; i++) {
    try {
      const real = await realpath(current);
      if (missingTail.length === 0) {
        return real;
      }
      return resolve(real, ...missingTail);
    } catch (err) {
      if (!isErrnoException(err) || err.code !== "ENOENT") {
        throw err;
      }
      const parent = dirname(current);
      if (parent === current) {
        // Reached filesystem root without finding an existing ancestor.
        // The path is structurally bogus relative to anything we know
        // about the worktree — treat as outside.
        throw new PathOutsideWorktreeError(
          `path outside worktree (no existing ancestor): ${userPath}`,
        );
      }
      missingTail.unshift(basename(current));
      current = parent;
    }
  }
  throw new PathOutsideWorktreeError(
    `path outside worktree (ancestor walk exhausted): ${userPath}`,
  );
}

/**
 * Throws `PathOutsideWorktreeError` if `candidate` is not equal to,
 * nor a descendant of, `worktreeRoot`. Equality is required for the
 * worktree-root-itself case; descendancy uses the trailing `sep`
 * guard so `/wt-foo` is not treated as inside `/wt`.
 */
function assertInside(
  worktreeRoot: string,
  candidate: string,
  userPath: string,
): void {
  if (candidate === worktreeRoot) {
    return;
  }
  if (!candidate.startsWith(worktreeRoot + sep)) {
    throw new PathOutsideWorktreeError(
      `path outside worktree: ${userPath} → ${candidate}`,
    );
  }
}

function isErrnoException(err: unknown): err is NodeJS.ErrnoException {
  return (
    err instanceof Error &&
    typeof (err as NodeJS.ErrnoException).code === "string"
  );
}
