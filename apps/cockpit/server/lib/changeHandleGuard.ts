// WP-003 — change-handle shape-guard (security hardening; TDD §3 Armor).
//
// WP-003 is where request input first reaches the recreate path: a tidied
// change is re-materialised by spawning `sulis-change recreate --handle
// <handle>` (SulisChangeRecreator). The handle is sourced off the change
// record (ADR-003), not directly off the URL — but defence-in-depth says
// validate its SHAPE before it crosses the spawn boundary. A malformed
// handle must yield a typed failure, never a spawn.
//
// The pattern mirrors SulisChangeStoreReader's CHANGE_ID_PATTERN
// (alphanumerics + underscore + hyphen — tight enough to refuse `..`, `/`,
// glob chars, whitespace, and shell metacharacters) and ADDS an explicit
// rejection of a LEADING hyphen. A leading hyphen is the argparse / getopt
// flag-confusion vector: a handle like `-x` could otherwise be parsed by
// the spawned CLI as a flag rather than a positional value. spawn-with-argv
// already forecloses shell injection; this forecloses flag-confusion too.
//
// This is a pure predicate + a throwing assertion — no I/O, no spawn — so
// it composes cleanly into the serving path before `resolveContractWorktree`
// ever reaches the RecreateRunner.

/**
 * The body shape: alphanumerics, underscore, hyphen. Same character class
 * as SulisChangeStoreReader.CHANGE_ID_PATTERN, kept deliberately in sync so
 * a handle that passes the store's id validation also passes here.
 */
const HANDLE_BODY = /^[A-Za-z0-9_-]+$/;

/**
 * Thrown when a change handle fails the shape-guard. Carries a stable
 * `code` the error mapper renders as 400 INVALID_CHANGE_HANDLE.
 */
export class InvalidChangeHandleError extends Error {
  readonly code = "INVALID_CHANGE_HANDLE";

  constructor(handle: unknown) {
    const shown =
      typeof handle === "string" ? JSON.stringify(handle) : String(handle);
    super(`unsafe change handle (refused before recreate): ${shown}`);
    this.name = "InvalidChangeHandleError";
  }
}

/**
 * True iff `handle` is a safe change handle: a non-empty string of
 * alphanumerics/underscore/hyphen that does NOT start with a hyphen.
 * Non-strings are unsafe (a corrupt record could carry anything; we refuse
 * rather than coerce toward the spawn).
 */
export function isSafeChangeHandle(handle: unknown): handle is string {
  if (typeof handle !== "string" || handle.length === 0) {
    return false;
  }
  // Explicit leading-hyphen rejection — the argparse flag-confusion vector.
  // Checked before the body test so the intent is legible at the call site.
  if (handle.startsWith("-")) {
    return false;
  }
  return HANDLE_BODY.test(handle);
}

/**
 * Assert `handle` is a safe change handle, or throw
 * `InvalidChangeHandleError`. Call this in the serving path before the
 * handle reaches `RecreateRunner.recreate` — so a malformed handle degrades
 * to a typed failure rather than spawning a subprocess.
 */
export function assertSafeChangeHandle(
  handle: unknown,
): asserts handle is string {
  if (!isSafeChangeHandle(handle)) {
    throw new InvalidChangeHandleError(handle);
  }
}
