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

import { gitDiffNameStatus } from "./gitShow";

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

  const entries = await gitDiffNameStatus({
    cwd: worktreeRoot,
    baseSha,
    ...(opts.timeoutMs !== undefined ? { timeoutMs: opts.timeoutMs } : {}),
  });

  return {
    // added/removed are null placeholders here; WP-P02 fills them from
    // `git diff --numstat` via the sanctioned git boundary.
    files: entries.map((e) => ({
      path: e.path,
      status: e.status,
      added: null,
      removed: null,
    })),
    baseKnown: true,
  };
}
