// WP-002 — readTestsState: best-effort read of a change's CI/test state.
//
// The cockpit reads the change's recorded test state; it never writes one.
// The recorded signal is a small JSON sidecar inside the change's own
// worktree at `.sulis/ci-state.json` (the same sidecar discipline
// `session.json` already uses), shape `{ "state": "green" | "red" }`.
//
// Best-effort + never-throws (BR-11): every path that isn't an explicit
// recorded green/red resolves to "unknown" — no sidecar, malformed JSON, an
// unexpected/absent `state`, a gone worktree. A board must never 500 because
// one change's test-state sidecar is missing or garbage. Read-only: a single
// file read, no write, no process start (A-1 / NFR-SEC).

import { readFile } from "node:fs/promises";
import { join } from "node:path";

import type { TestsState } from "./computeHealth";

const CI_STATE_RELPATH = join(".sulis", "ci-state.json");

/**
 * Read the change's recorded test state, best-effort. Returns "green" or
 * "red" only when the sidecar records exactly that; "unknown" otherwise.
 * Never throws.
 */
export async function readTestsState(
  worktreePath: string,
): Promise<TestsState> {
  let raw: string;
  try {
    raw = await readFile(join(worktreePath, CI_STATE_RELPATH), "utf8");
  } catch {
    return "unknown"; // absent sidecar / unreadable worktree
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return "unknown"; // malformed JSON
  }

  if (
    typeof parsed === "object" &&
    parsed !== null &&
    "state" in parsed &&
    (parsed as { state: unknown }).state !== undefined
  ) {
    const state = (parsed as { state: unknown }).state;
    if (state === "green" || state === "red") {
      return state;
    }
  }
  return "unknown"; // missing / unexpected state value
}
