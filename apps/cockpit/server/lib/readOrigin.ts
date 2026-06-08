// WP-P09 — readOrigin: per-file inferred origin for the whole change.
//
// The whole-change list behind `GET /api/changes/:id/origin`. It reuses the
// changed-file set (`readChangedFiles` — the same `git diff` boundary the Files
// view uses) and attributes each path through the injected `OriginAttribution`
// port (the inferred adapter today; the recorded adapter swaps in at WP-P13 with
// no change here — ADR-012).
//
// Fail-soft: a legacy change with no base sha yields an empty file list (no
// baseline to diff); a file the port can't attribute resolves to `unknown`
// (never an error). Composes existing reads — no new git spawn.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { ChangeOriginView, FileOrigin } from "../../shared/api-types";
import type { OriginAttribution } from "../ports/OriginAttribution";

import { readChangedFiles } from "./readChangedFiles";

export interface ReadOriginOptions {
  /** Override the git-diff subprocess timeout (default 5 s). */
  gitTimeoutMs?: number;
}

/**
 * The inferred origin of every file changed in `changeId` (base sha → worktree).
 *
 * `baseSha === null` (legacy record) → `{ changeId, files: [] }`. A removed file
 * still gets attributed by its last-changing commit (its history exists even
 * though the file is gone from the worktree).
 */
export async function readOrigin(
  changeId: string,
  worktreeRoot: string,
  baseSha: string | null,
  attribution: OriginAttribution,
  opts: ReadOriginOptions = {},
): Promise<ChangeOriginView> {
  const changed = await readChangedFiles(
    worktreeRoot,
    baseSha,
    opts.gitTimeoutMs !== undefined ? { timeoutMs: opts.gitTimeoutMs } : {},
  );

  const files: FileOrigin[] = await Promise.all(
    changed.files.map(async (f) => ({
      path: f.path,
      origin: await attribution.originFor(changeId, f.path),
    })),
  );

  return { changeId, files };
}
