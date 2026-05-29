// WP-004 — recreate-on-demand resolver (TDD §3, §5; ADR-003/004).
//
// The serving path (WP-003) calls this to reach a change's contracts. A
// shipped change's worktree is removed by the #56 tidy step, but its
// branch + record (with a pinned `shipped_sha`) are kept. This resolver
// re-materialises a tidied worktree on demand — transparently — by
// composing the already-shipped `sulis-change recreate` (behind the
// RecreateRunner port; ADR-004). It does NOT re-implement worktree
// materialisation.
//
// It distinguishes the three states (acceptance criteria / ADR-004
// consequence):
//   (a) worktree present            → resolve the root directly;
//   (b) absent-but-recreatable      → recreate, then resolve the root;
//   (c) absent-and-not-recreatable  → typed note; the cockpit degrades to
//                                      a plain "couldn't reach this shipped
//                                      change's contracts" rather than
//                                      hanging a request.
// A recreate that fails (TIMEOUT / EXEC_FAIL / SPAWN_FAIL) — or that
// reports success but doesn't actually materialise the worktree — also
// degrades to the typed note rather than hanging or throwing raw
// (TDD §3 bounded recreate).
//
// Generic per-change resolution (ADR-003): every fact comes off the
// change record (`worktreePath`, `branch`, `shippedSha`, `handle`) —
// nothing is hard-wired to a specific change.

import { NotFoundError } from "../lib/errors";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { RecreateRunner } from "../ports/RecreateRunner";

import { resolveWorktreeRoot } from "./_worktree";

/** The founder-legible degrade note (TDD §3). */
const UNAVAILABLE_NOTE = "couldn't reach this shipped change's contracts";

/**
 * The three degrade paths all return the same founder-legible note with
 * a differing machine-readable `reason`. One constructor keeps the note
 * text single-sourced (DRY — the 2-consumer threshold is met three times
 * over here) so a wording change is one edit.
 */
function unavailable(
  reason: "not-recreatable" | "recreate-failed" | "recreate-no-op",
): ContractWorktreeResolution {
  return { status: "unavailable", note: UNAVAILABLE_NOTE, reason };
}

/**
 * The resolved state of a change's worktree for contract rendering.
 *   - `ready`        → `worktreeRoot` is a present, realpath-resolved root
 *                      the serving path can safeJoin into and render from.
 *   - `unavailable`  → the worktree is absent and could not be reached;
 *                      `note` is a plain founder-legible message to show
 *                      instead of a broken render. `reason` is the
 *                      machine-readable cause for logging/telemetry.
 */
export type ContractWorktreeResolution =
  | { status: "ready"; worktreeRoot: string }
  | {
      status: "unavailable";
      note: string;
      reason: "not-recreatable" | "recreate-failed" | "recreate-no-op";
    };

export type ResolveContractWorktreeArgs = {
  record: ChangeStoreRecord;
  runner: RecreateRunner;
};

/**
 * Is a change with an absent worktree recreatable? Recreatable iff the
 * record carries a way for `sulis-change recreate` to find a tree to
 * check out: a branch that may still exist, or a pinned `shipped_sha`.
 * A legacy record with neither (predates `shipped_sha`) is not
 * recreatable (state c).
 */
function isRecreatable(record: ChangeStoreRecord): boolean {
  const hasBranch =
    typeof record.branch === "string" && record.branch.length > 0;
  const hasShippedSha =
    typeof record.shippedSha === "string" && record.shippedSha.length > 0;
  return hasBranch || hasShippedSha;
}

/**
 * Try to resolve a present worktree root. Returns the realpath-resolved
 * root, or `null` if the worktree is absent on disk (ENOENT → the
 * NotFoundError `resolveWorktreeRoot` raises). Any other error (a real
 * I/O fault, a permission error) propagates — those are not "absent", and
 * silently swallowing them would mask a genuine problem.
 */
async function tryResolvePresent(worktreePath: string): Promise<string | null> {
  try {
    return await resolveWorktreeRoot(worktreePath);
  } catch (err) {
    if (err instanceof NotFoundError) {
      return null;
    }
    throw err;
  }
}

/**
 * Resolve a change's worktree for contract rendering, recreating it on
 * demand when it has been tidied. See the module header for the
 * three-state contract.
 */
export async function resolveContractWorktree(
  args: ResolveContractWorktreeArgs,
): Promise<ContractWorktreeResolution> {
  const { record, runner } = args;

  // (a) present → resolve directly, no recreate.
  const present = await tryResolvePresent(record.worktreePath);
  if (present !== null) {
    return { status: "ready", worktreeRoot: present };
  }

  // Absent. (c) not recreatable → typed note, no spawn.
  if (!isRecreatable(record)) {
    return unavailable("not-recreatable");
  }

  // (b) absent-but-recreatable → recreate, then resolve.
  const outcome = await runner.recreate(record.handle);
  if (!outcome.ok) {
    // TIMEOUT / EXEC_FAIL / SPAWN_FAIL — degrade, never hang or throw raw.
    return unavailable("recreate-failed");
  }

  // Recreate reported success (fresh materialisation or the idempotent
  // already-present no-op). Resolve the now-present root.
  const afterRecreate = await tryResolvePresent(record.worktreePath);
  if (afterRecreate !== null) {
    return { status: "ready", worktreeRoot: afterRecreate };
  }

  // Recreate claimed success but the worktree is still absent — degrade
  // rather than hand the serving path a root that isn't there.
  return unavailable("recreate-no-op");
}
