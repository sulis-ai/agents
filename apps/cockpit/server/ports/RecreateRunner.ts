// WP-004 — RecreateRunner port (TDD §3, §5; ADR-004).
//
// The recreate-on-demand path composes the already-shipped
// `sulis-change recreate` CLI to re-materialise a tidied change's
// worktree before its contracts can be rendered (ADR-004). It does NOT
// re-implement worktree materialisation (`cmd_recreate`) — it drives it.
//
// This port is the seam between the serving path and that CLI. Behind it
// sit two adapters: `SulisChangeRecreator` (production — spawns the CLI
// with the cockpit's spawn-not-exec + bounded-timeout discipline) and
// `FakeRecreateRunner` (an in-memory adapter for tests — WPB-03 / MEA-09,
// a real adapter shape, not an ad-hoc mock). Keeping recreate behind this
// port is what lets WP-004 ship in parallel with the renderers and keeps
// the cockpit read-only by composition: recreate is an explicitly-invoked
// step, never in-process server work (ADR-001/004).

/**
 * The outcome of one recreate attempt.
 *
 * Success carries `alreadyPresent` so the resolver can distinguish a
 * fresh materialisation from the idempotent no-op (`recreate` reports
 * "worktree already exists" → no-op success — the documented idempotent
 * path the resolver must treat as success, not error).
 *
 * Failure is typed (never a thrown raw error across the seam) so the
 * serving path can degrade to a plain founder-legible note rather than
 * hanging or 500-ing a request (TDD §3 bounded recreate):
 *   - `TIMEOUT`   — recreate exceeded its bounded timeout (child killed);
 *   - `EXEC_FAIL` — recreate exited non-zero;
 *   - `SPAWN_FAIL`— the CLI could not be spawned (ENOENT / EACCES / …).
 */
export type RecreateFailureReason = "TIMEOUT" | "EXEC_FAIL" | "SPAWN_FAIL";

export type RecreateOutcome =
  | { ok: true; alreadyPresent: boolean }
  | { ok: false; reason: RecreateFailureReason; detail: string };

/**
 * Drive `sulis-change recreate --change-id <changeId>` (or its in-memory
 * twin). The implementation owns the subprocess discipline; this
 * interface owns only the contract: given a change's UNIQUE id, return a
 * typed outcome — never throw across the boundary.
 *
 * The seam is keyed by the unique `change_id`, NOT the 6-char display
 * handle (ADR-001). The handle is shared by 2–4 changes in live data;
 * driving recreate by it is the cockpit half of "session works on the
 * wrong change". The cockpit already reads the record by its id, so it
 * carries that id straight across this seam.
 */
export interface RecreateRunner {
  /**
   * Re-materialise the worktree for the change identified by its unique
   * `changeId`. Idempotent: an already-present worktree is reported as
   * `{ ok: true, alreadyPresent: true }`, not an error.
   */
  recreate(changeId: string): Promise<RecreateOutcome>;
}
