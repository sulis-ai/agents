// WP-004 — detectOpenBlocker: read-time check for a parked change.
//
// A change is "blocked" (FR-12) when an executor has written a BLOCKER
// record into its worktree's architecture tree. The cockpit reads that
// signal at status-read time — it never writes one. This is the only
// concrete blocker source the server can observe locally without a live
// agent.
//
// Read-only: a recursive listing of `<worktree>/.architecture/**/
// work-packages/` for any `BLOCKER-*.md`. No files written, no process
// started (NFR-SEC-05 / read-only gate).
//
// Best-effort: a missing worktree or architecture dir means "no blocker
// observable" → false (never throws on a legitimate absence).

import { readdir } from "node:fs/promises";
import { join } from "node:path";

const BLOCKER_PREFIX = "BLOCKER-";
const BLOCKER_SUFFIX = ".md";

/**
 * Return true iff the change's worktree carries at least one
 * `BLOCKER-*.md` under any `.architecture/<project>/work-packages/`.
 * Best-effort: returns false on any read failure (absent worktree,
 * absent architecture dir, permission error).
 */
export async function detectOpenBlocker(
  worktreePath: string,
): Promise<boolean> {
  const archRoot = join(worktreePath, ".architecture");

  let projects: string[];
  try {
    projects = await listDirs(archRoot);
  } catch {
    return false;
  }

  for (const project of projects) {
    const wpDir = join(archRoot, project, "work-packages");
    let entries: string[];
    try {
      entries = await readdir(wpDir);
    } catch {
      continue; // this project has no work-packages dir — skip
    }
    if (entries.some(isBlockerFile)) {
      return true;
    }
  }
  return false;
}

function isBlockerFile(name: string): boolean {
  return name.startsWith(BLOCKER_PREFIX) && name.endsWith(BLOCKER_SUFFIX);
}

async function listDirs(dir: string): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true });
  return entries.filter((e) => e.isDirectory()).map((e) => e.name);
}
