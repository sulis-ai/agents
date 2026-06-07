// WP-010 — onboarding confirm gate (FR-N6 / NFR-DISC-04; ADR-007).
//
// The confirm gate is a PURE module — the WP-005 sessionBinding / inFlightLock
// sibling pattern. It is the single decision point that separates a read-only
// PROPOSE turn (which mints nothing) from the consequential ACT (mint +
// repo-create). The act may proceed ONLY when:
//
//   1. the turn's phase is `confirm` (no other phase can ever open the gate),
//   2. a LIVE proposal exists (something to confirm), and
//   3. the turn's `confirmToken` exactly matches the live proposal's token.
//
// Any mismatch, a missing token, or a confirm with no live proposal is refused
// with DISCOVERY_CONFIRM_STALE — a stale proposal can never be mis-confirmed
// (NFR-DISC-04). A declined / absent confirm leaves the gate CLOSED and the
// caller MUST NOT proceed.
//
// Pure: no fs / git / process / bridge, no clock, no randomness. Unit-testable
// without a live agent — the same discipline as `lib/sessionBinding.ts`.

/** The minimal turn fields the gate decides on. */
export interface ConfirmGateRequest {
  phase: "search" | "ask" | "confirm";
  confirmToken?: string;
}

/** The live proposal a confirm is checked against (null = nothing proposed). */
export interface LiveProposal {
  confirmToken: string;
}

/**
 * The gate's verdict. `open: true` is the ONLY path that permits the act; every
 * other input shape yields `open: false` with a typed code (the route maps it
 * to a 422 / error event).
 */
export type ConfirmGateVerdict =
  | { open: true }
  | { open: false; code: "DISCOVERY_CONFIRM_STALE" | "NOT_AN_ACT" };

/**
 * Decide whether this turn may perform the consequential act. Fails closed on
 * any non-confirm phase, any missing/mismatched token, or an absent live
 * proposal.
 */
export function evaluateConfirmGate(
  request: ConfirmGateRequest,
  live: LiveProposal | null,
): ConfirmGateVerdict {
  // Only a `confirm` phase can ever be an act. A token on a search/ask turn is
  // ignored — the caller streams a read-only proposal, never a mint.
  if (request.phase !== "confirm") {
    return { open: false, code: "NOT_AN_ACT" };
  }

  // A confirm with nothing live to confirm is stale by definition.
  if (live === null) {
    return { open: false, code: "DISCOVERY_CONFIRM_STALE" };
  }

  // The token must positively match the live proposal (carried identity, never
  // inferred). A missing or mismatched token is refused.
  if (!request.confirmToken || request.confirmToken !== live.confirmToken) {
    return { open: false, code: "DISCOVERY_CONFIRM_STALE" };
  }

  return { open: true };
}
