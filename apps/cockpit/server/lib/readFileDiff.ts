// WP-008 — produce a FileDiff (TDD §5.1) for the cockpit's diff toggle.
//
// ADR-006 is the key piece of context: the server does NOT compute the
// diff itself. It returns the two file versions — `base` (contents at
// `base_sha`) and `current` (worktree contents) — and Monaco's
// `DiffEditor` does the visual rendering client-side. So this function
// is really "read two files (one from git, one from disk) and shape
// them into one envelope".
//
// Composition (per WP-008 Contract):
//   safeJoin     (WP-004) — sanitise the relative path before any git
//                            or fs touch.
//   gitShow      (WP-008) — run `git show <sha>:<path>` to retrieve
//                            base contents (the ONLY git boundary).
//   fs.readFile           — retrieve current worktree contents.
//   MAX_BYTES    (WP-007) — single source of truth for the 1 MiB cap.
//   detectBinary (WP-007) — single source of truth for binary detection.
//   languageHint (WP-007) — extension → Monaco language id.
//
// Edge-case mapping (per WP-008 Contract):
//   - File added in worktree (not at base) → base: null, current: <bytes>.
//     gitShow exits non-zero with a "not in <sha>" / "does not exist"
//     stderr; we detect that pattern and map to null rather than throw.
//   - File deleted in worktree (at base, not in worktree) → base: <bytes>,
//     current: null. fs.readFile throws ENOENT; we catch and map.
//   - Either side > MAX_BYTES → both null, truncated: true. (Monaco
//     refuses to render a meaningful diff for over-cap files anyway;
//     the UI shows "file too large to diff — copy path".)
//   - Either side binary → both null, binary: true. Diff-of-binary is
//     not a thing the UI surfaces.
//   - safeJoin escape → PathOutsideWorktreeError (re-thrown unchanged).
//   - gitShow non-zero NOT matching the "not in <sha>" pattern → GitError.
//   - gitShow timeout → TimeoutError (re-thrown).

import { readFile, stat } from "node:fs/promises";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { FileDiff } from "../../shared/api-types";

import { detectBinary } from "./detectBinary";
import { GitError } from "./errors";
import { gitShow } from "./gitShow";
import { languageHint } from "./languageHint";
import { MAX_BYTES } from "./readFileContents";
import { safeJoin } from "./safeJoin";

interface ReadFileDiffOptions {
  /** Override the 1 MiB cap (useful for tests). */
  maxBytes?: number;
  /** Override the gitShow subprocess timeout (default 5 s). */
  timeoutMs?: number;
}

/**
 * Returns a `FileDiff` for `relativePath`:
 *   - `base`:    contents at `baseSha`, or `null` if the file didn't
 *                exist there.
 *   - `current`: contents in the worktree, or `null` if the file was
 *                deleted.
 *
 * `binary` / `truncated` apply to EITHER side: if either side trips
 * the cap or the NUL-byte heuristic, both fields become `null` and
 * the corresponding flag is set. (The UI surfaces a single "too
 * large" or "binary" message; it doesn't try to render half a diff.)
 *
 * `language` comes from `languageHint(relativePath)` regardless of
 * which side(s) are present.
 *
 * Throws:
 *   - `PathOutsideWorktreeError` if `relativePath` escapes (no git
 *     invocation occurs).
 *   - `GitError` if `gitShow` exits non-zero for a reason other than
 *     "file did not exist at this sha" (bad revision, GC'd commit).
 *   - `TimeoutError` if `gitShow` exceeds its timeout.
 */
export async function readFileDiff(
  worktreeRoot: string,
  baseSha: string,
  relativePath: string,
  opts: ReadFileDiffOptions = {},
): Promise<FileDiff> {
  const maxBytes = opts.maxBytes ?? MAX_BYTES;

  // 1. Sanitise the path. safeJoin throws PathOutsideWorktreeError on
  //    escape; that propagates unchanged BEFORE any git or fs touch.
  const absolutePath = await safeJoin(worktreeRoot, relativePath);
  const language = languageHint(relativePath);

  // 2. Retrieve the base contents via `git show <sha>:<path>`.
  //    Distinguish "file did not exist at base" (→ null) from a genuine
  //    git error (→ GitError). git's stderr phrasing varies across
  //    versions but consistently includes one of these substrings:
  //      - "exists on disk, but not in"   (file is in worktree, not in sha)
  //      - "does not exist in"            (file is not anywhere in sha)
  //      - "path"                          (varies; not specific enough alone)
  //    We treat the union of the first two as the "file-not-at-base"
  //    signal; anything else with a non-zero exit is a GitError.
  const baseResult = await gitShow({
    cwd: worktreeRoot,
    sha: baseSha,
    relativePath,
    timeoutMs: opts.timeoutMs,
  });

  let baseBuf: Buffer | null;
  let baseTooBig = false;
  if (baseResult.exitCode === 0) {
    baseBuf = baseResult.stdout;
    if (baseBuf.length > maxBytes) {
      baseTooBig = true;
      baseBuf = null;
    }
  } else if (isFileNotAtBase(baseResult.stderr)) {
    // File didn't exist at base — legitimate added-in-worktree case.
    baseBuf = null;
  } else {
    throw new GitError(
      `git show failed (exitCode=${baseResult.exitCode}, sha=${baseSha}, path=${relativePath}): ${baseResult.stderr.trim()}`,
    );
  }

  // 3. Retrieve the current worktree contents. fs.stat first so we
  //    can refuse oversized files without reading them; ENOENT maps
  //    to "deleted in worktree".
  let currentBuf: Buffer | null = null;
  let currentTooBig = false;
  let currentExists = true;
  try {
    const stats = await stat(absolutePath);
    if (stats.isDirectory()) {
      // A diff request against a directory path is nonsensical; mirror
      // the gitShow non-zero path by treating it as missing on the
      // worktree side. The route layer (WP-010) validates `path` as a
      // file before reaching here in practice, but we stay defensive.
      currentExists = false;
    } else if (stats.size > maxBytes) {
      currentTooBig = true;
      currentExists = true; // it exists; we just won't return contents
    } else {
      currentBuf = await readFile(absolutePath);
    }
  } catch (err) {
    if (isErrnoException(err) && err.code === "ENOENT") {
      currentExists = false;
    } else {
      throw err;
    }
  }

  // 4. Apply the cross-side cap + binary checks.
  //    - If EITHER side is too big, both become null and truncated=true.
  //    - If EITHER side is binary (NUL byte in first 8 KiB), both
  //      become null and binary=true.
  if (baseTooBig || currentTooBig) {
    return {
      path: relativePath,
      absolutePath,
      base: null,
      current: null,
      binary: false,
      truncated: true,
      language,
    };
  }

  const baseBinary = baseBuf !== null && detectBinary(baseBuf);
  const currentBinary = currentBuf !== null && detectBinary(currentBuf);
  if (baseBinary || currentBinary) {
    return {
      path: relativePath,
      absolutePath,
      base: null,
      current: null,
      binary: true,
      truncated: false,
      // Suppress language hint — a binary file has no meaningful
      // syntax highlighting (mirrors readFileContents' behaviour).
      language: null,
    };
  }

  return {
    path: relativePath,
    absolutePath,
    base: baseBuf === null ? null : baseBuf.toString("utf8"),
    current:
      !currentExists || currentBuf === null
        ? null
        : currentBuf.toString("utf8"),
    binary: false,
    truncated: false,
    language,
  };
}

/**
 * Pattern-match git's stderr for the "file did not exist at this sha"
 * shape. We match on the two known substrings rather than the exit
 * code alone because git's exit code is the same (128) for both
 * file-not-at-base AND bad-revision; only stderr distinguishes them.
 *
 * Recorded brittleness: future git versions could re-word these
 * messages. The fallback if the wording changes is a GitError instead
 * of a `base: null` — visible to the caller and easy to fix forward.
 */
function isFileNotAtBase(stderr: string): boolean {
  return (
    stderr.includes("exists on disk") ||
    stderr.includes("does not exist") ||
    stderr.includes("does not exist in")
  );
}

function isErrnoException(err: unknown): err is NodeJS.ErrnoException {
  return (
    err instanceof Error &&
    typeof (err as NodeJS.ErrnoException).code === "string"
  );
}
