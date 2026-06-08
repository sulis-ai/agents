// Files redesign (Direction B) — the changed-files set for a change.
//
// Powers the "All files ↔ Changed · N" scope switch + the worded
// new/edited/removed status badges in the repo-browser Files view.
//
// Read-only: it composes `gitDiffNameStatus` (the sanctioned git
// boundary in gitShow.ts — `git diff` never mutates the tree or index),
// shapes the result into the wire `ChangedFiles`, and returns an empty
// set (baseKnown:false) for a legacy change with no recorded base sha
// rather than throwing — the UI says "no baseline recorded" instead of
// implying nothing changed.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import type { ChangedFiles } from "../../shared/api-types";

import { gitDiffNameStatus, gitDiffNumstat } from "./gitShow";

interface ReadChangedFilesOptions {
  /** Override the gitDiffNameStatus subprocess timeout (default 5 s). */
  timeoutMs?: number;
}

/**
 * Return the set of paths that differ between the change's base commit
 * (`baseSha`) and its worktree, each tagged new / edited / removed.
 *
 * `baseSha === null` → `{ files: [], baseKnown: false }` (legacy record;
 * no baseline to diff against — not an error).
 *
 * Throws `GitError` / `TimeoutError` from the underlying git boundary
 * for a genuine failure (bad sha, timeout); the route maps those to the
 * JSON error envelope.
 */
export async function readChangedFiles(
  worktreeRoot: string,
  baseSha: string | null,
  opts: ReadChangedFilesOptions = {},
): Promise<ChangedFiles> {
  if (baseSha === null || baseSha === "") {
    return { files: [], baseKnown: false };
  }

  const gitOpts = {
    cwd: worktreeRoot,
    baseSha,
    ...(opts.timeoutMs !== undefined ? { timeoutMs: opts.timeoutMs } : {}),
  };

  // Name-status is the authoritative set (one row per changed path,
  // worded new/edited/removed). Numstat carries the per-file +N/−N
  // counts; we run it alongside and merge by path. The two views agree
  // on the path set under `--no-renames`, but we key off name-status so
  // a count with no matching status row is never surfaced on its own.
  const [entries, numstat] = await Promise.all([
    gitDiffNameStatus(gitOpts),
    gitDiffNumstat(gitOpts),
  ]);

  const countsByPath = new Map(numstat.map((n) => [n.path, n]));

  return {
    files: entries.map((e) => {
      const counts = countsByPath.get(e.path);
      // A path present in name-status but absent from numstat changed
      // without touching line counts (e.g. a pure mode change) → 0/0.
      // A binary file appears in numstat with null counts → null/null.
      return {
        path: e.path,
        status: e.status,
        added: counts ? counts.added : 0,
        removed: counts ? counts.removed : 0,
      };
    }),
    baseKnown: true,
  };
}
