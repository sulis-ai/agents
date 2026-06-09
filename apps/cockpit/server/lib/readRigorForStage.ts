// WP-002 — readRigorForStage: best-effort per-stage rigor read (BR-12).
//
// Does the change have the artifacts it SHOULD for its stage? The cockpit
// reads this signal best-effort at feed-time; it never writes one. Mirrors
// `detectOpenBlocker`'s discipline exactly: read-only, never-throws, and a
// missing worktree / unreadable dir resolves to a safe default rather than
// an exception — a board must never 500 because one change's worktree is
// gone (A-1 / BR-11).
//
// The per-stage required-artifact rule (BR-12):
//   - specify / design → a spec exists (.specifications/<project>/SRD.md).
//   - implement        → a design OR plan exists (.architecture/<project>/
//                        TDD.md OR a .architecture/<project>/work-packages/
//                        dir).
//   - review / ship    → tests exist alongside the code (a *.test.* file or
//                        a tests/ dir anywhere OUTSIDE the .architecture /
//                        .specifications trees).
//   - recon / shipped  → no required artifact: rigor can never pull these
//                        off-track, AND there is no positive rigor signal
//                        to determine, so { ok:true, missing:null,
//                        determinable:false } — that feeds the FR-31 unknown
//                        health when tests are also absent (the BR-12 note:
//                        absent tests on a Recon change ⇒ unknown, never a
//                        false on-track).
//
// Returns { ok, missing, determinable }:
//   - dir readable + rule resolves → determinable:true, ok per the rule.
//   - worktree gone / unreadable / rule can't resolve → { ok:true,
//     missing:null, determinable:false } (can't prove drift ⇒ don't flag
//     off-track on absence alone).
//
// Path containment (MUC-4): every read stays inside the change's own
// worktree via `safeJoin`. A containment violation (a symlinked artifact
// dir pointing outside the worktree) fails soft to determinable:false —
// the escaped path is never read.

import { readdir, realpath, stat } from "node:fs/promises";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { WorkflowStage } from "../../shared/api-types";
import { safeJoin } from "./safeJoin";

/** The fixed artifact names a rigor failure can name (FR-32 — never free text). */
export type MissingArtifact = "spec" | "design" | "tests";

/**
 * The rigor-for-stage verdict the health rollup consumes.
 *   - `ok`            → true unless a required-for-stage artifact is missing.
 *   - `missing`       → which fixed artifact is absent (null when ok).
 *   - `determinable`  → whether we could resolve the rule at all. False on a
 *                       gone/unreadable worktree, and on the no-required-
 *                       artifact stages (recon/shipped) where there is no
 *                       positive rigor signal — both feed the unknown read.
 */
export interface RigorForStage {
  ok: boolean;
  missing: MissingArtifact | null;
  determinable: boolean;
}

const OK_INDETERMINATE: RigorForStage = {
  ok: true,
  missing: null,
  determinable: false,
};
const OK_DETERMINATE: RigorForStage = {
  ok: true,
  missing: null,
  determinable: true,
};

function offTrack(missing: MissingArtifact): RigorForStage {
  return { ok: false, missing, determinable: true };
}

/**
 * Read the change's rigor-for-stage, best-effort. Never throws. See the
 * module header for the per-stage rule and the degrade semantics.
 */
export async function readRigorForStage(
  worktreePath: string,
  stage: WorkflowStage,
): Promise<RigorForStage> {
  // Canonicalise the worktree root once. The record's worktreePath may be a
  // symlinked path (e.g. macOS /var → /private/var); safeJoin's containment
  // check needs a canonical base or every legitimate read would be rejected.
  // realpath also doubles as the readable-directory probe — a gone/unreadable
  // worktree throws here and degrades to indeterminate.
  let root: string;
  try {
    root = await realpath(worktreePath);
  } catch {
    return OK_INDETERMINATE; // gone / unreadable
  }
  if (!(await isReadableDir(root))) {
    return OK_INDETERMINATE; // exists but not a readable directory
  }

  switch (stage) {
    case "specify":
    case "design":
      return (await hasSpec(root)) ? OK_DETERMINATE : offTrack("spec");

    case "implement":
      return (await hasDesignOrPlan(root))
        ? OK_DETERMINATE
        : offTrack("design");

    case "review":
    case "ship":
      return (await hasTestsAlongsideCode(root))
        ? OK_DETERMINATE
        : offTrack("tests");

    case "recon":
    case "shipped":
      // No required artifact: never off-track on rigor, and no positive
      // signal to determine → indeterminate (feeds the unknown read).
      return OK_INDETERMINATE;

    default:
      // An unrecognised / malformed stage: we cannot resolve a rule, so we
      // cannot prove drift. Degrade to indeterminate (BR-11 / MUC-1).
      return OK_INDETERMINATE;
  }
}

/** True iff `<worktree>/.specifications/<project>/SRD.md` exists for some project. */
async function hasSpec(worktreePath: string): Promise<boolean> {
  return await someProjectHas(worktreePath, ".specifications", async (projDir) =>
    fileExists(projDir, "SRD.md"),
  );
}

/**
 * True iff some `.architecture/<project>/` carries a TDD.md design OR a
 * work-packages/ plan dir.
 */
async function hasDesignOrPlan(worktreePath: string): Promise<boolean> {
  return await someProjectHas(worktreePath, ".architecture", async (projDir) => {
    if (await fileExists(projDir, "TDD.md")) {
      return true;
    }
    return await dirExists(projDir, "work-packages");
  });
}

/**
 * True iff a test file (`*.test.*`) or a `tests/` dir exists anywhere in
 * the worktree OUTSIDE the .architecture / .specifications trees (those
 * hold the methodology artifacts, not the change's own tests). Bounded
 * recursion with an explicit ignore list, all reads safeJoin-contained.
 */
async function hasTestsAlongsideCode(worktreePath: string): Promise<boolean> {
  const IGNORE = new Set([
    ".architecture",
    ".specifications",
    ".git",
    "node_modules",
    ".sulis",
  ]);
  // BFS, capped, so a pathological tree can't run unbounded (NFR-PERF).
  const queue: string[] = [""];
  let visited = 0;
  const MAX_DIRS = 2000;
  while (queue.length > 0 && visited < MAX_DIRS) {
    const rel = queue.shift()!;
    visited++;
    const entries = await safeReaddir(worktreePath, rel);
    for (const entry of entries) {
      if (entry.isDirectory()) {
        if (rel === "" && IGNORE.has(entry.name)) {
          continue;
        }
        if (entry.name === "tests") {
          return true;
        }
        queue.push(rel === "" ? entry.name : `${rel}/${entry.name}`);
      } else if (entry.isFile() && isTestFile(entry.name)) {
        return true;
      }
    }
  }
  return false;
}

/**
 * Read a worktree-relative directory's entries (with file types), contained
 * via safeJoin. Fails soft to `[]` on an unreadable/escaped path — the BFS
 * just skips that branch (never throws).
 */
async function safeReaddir(worktreePath: string, rel: string) {
  try {
    const dir = rel === "" ? worktreePath : await safeJoin(worktreePath, rel);
    return await readdir(dir, { withFileTypes: true });
  } catch {
    return [];
  }
}

function isTestFile(name: string): boolean {
  return /\.(test|spec)\.[cm]?[jt]sx?$/.test(name);
}

/**
 * For each immediate `<worktree>/<topDir>/<project>/` directory, run
 * `check(projDir)`; return true on the first match. Best-effort: a missing
 * topDir or an unreadable project dir yields false, never throws. All path
 * joins go through safeJoin (MUC-4) so a symlinked topDir escaping the
 * worktree is refused (the read fails soft to "not found").
 */
async function someProjectHas(
  worktreePath: string,
  topDir: string,
  check: (absoluteProjectDir: string) => Promise<boolean>,
): Promise<boolean> {
  let topAbs: string;
  try {
    topAbs = await safeJoin(worktreePath, topDir);
  } catch {
    return false; // escaped / bad path → treat as absent
  }
  let projects: string[];
  try {
    const entries = await readdir(topAbs, { withFileTypes: true });
    projects = entries.filter((e) => e.isDirectory()).map((e) => e.name);
  } catch {
    return false; // topDir absent / unreadable
  }
  for (const project of projects) {
    let projAbs: string;
    try {
      projAbs = await safeJoin(worktreePath, `${topDir}/${project}`);
    } catch {
      continue;
    }
    try {
      if (await check(projAbs)) {
        return true;
      }
    } catch {
      // a single project's check failing is not fatal — keep scanning.
      continue;
    }
  }
  return false;
}

async function fileExists(dir: string, name: string): Promise<boolean> {
  try {
    const s = await stat(`${dir}/${name}`);
    return s.isFile();
  } catch {
    return false;
  }
}

async function dirExists(dir: string, name: string): Promise<boolean> {
  try {
    const s = await stat(`${dir}/${name}`);
    return s.isDirectory();
  } catch {
    return false;
  }
}

async function isReadableDir(path: string): Promise<boolean> {
  try {
    const s = await stat(path);
    if (!s.isDirectory()) {
      return false;
    }
    await readdir(path);
    return true;
  } catch {
    return false;
  }
}
