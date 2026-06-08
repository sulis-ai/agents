// WP-005 — sessionBinding unit test (ADR-004, FR-21, FR-N2, NFR-SEC-02/06).
//
// The single most dangerous failure for a multi-change cockpit is delivering
// a message to the WRONG change's agent. The binding guard is a pure function
// over (requested change, resolved session) that fails CLOSED: it delivers
// only if it can POSITIVELY prove the session belongs to the named change —
// by carried identity (change_id) AND cwd/worktreePath equality — for live,
// resumed, and spawned sessions alike.
//
// The acceptance is literal: A-request → B-session ⇒ mismatch (so the route
// sends zero bytes, touches no process). These assertions are why the guard
// runs BEFORE resume/spawn at the relay seam.

import { describe, it, expect } from "vitest";

import { checkSessionBinding } from "../lib/sessionBinding";
import type { SessionRef } from "../ports/SessionBridge";

const CHANGE_A = "01CHANGEAAAAAAAAAAAAAAAAAA";
const CHANGE_B = "01CHANGEBBBBBBBBBBBBBBBBBB";
const WORKTREE_A = "/tmp/worktree-a";
const WORKTREE_B = "/tmp/worktree-b";

function sessionFor(changeId: string, cwd: string): SessionRef {
  return { changeId, cwd };
}

describe("checkSessionBinding (ADR-004)", () => {
  it("binds when change_id AND cwd both match (A → A)", () => {
    const verdict = checkSessionBinding(
      { changeId: CHANGE_A, worktreePath: WORKTREE_A },
      sessionFor(CHANGE_A, WORKTREE_A),
    );
    expect(verdict.bound).toBe(true);
  });

  it("refuses when the session belongs to a DIFFERENT change (A → B ⇒ mismatch)", () => {
    const verdict = checkSessionBinding(
      { changeId: CHANGE_A, worktreePath: WORKTREE_A },
      sessionFor(CHANGE_B, WORKTREE_B),
    );
    expect(verdict.bound).toBe(false);
    if (!verdict.bound) {
      expect(verdict.reason.length).toBeGreaterThan(0);
    }
  });

  it("refuses when change_id matches but cwd does NOT (the locateTranscripts failsafe)", () => {
    const verdict = checkSessionBinding(
      { changeId: CHANGE_A, worktreePath: WORKTREE_A },
      sessionFor(CHANGE_A, WORKTREE_B),
    );
    expect(verdict.bound).toBe(false);
  });

  it("refuses when cwd matches but change_id does NOT", () => {
    const verdict = checkSessionBinding(
      { changeId: CHANGE_A, worktreePath: WORKTREE_A },
      sessionFor(CHANGE_B, WORKTREE_A),
    );
    expect(verdict.bound).toBe(false);
  });

  it("fails closed on an empty / missing session change_id", () => {
    const verdict = checkSessionBinding(
      { changeId: CHANGE_A, worktreePath: WORKTREE_A },
      sessionFor("", WORKTREE_A),
    );
    expect(verdict.bound).toBe(false);
  });

  it("fails closed on an empty session cwd", () => {
    const verdict = checkSessionBinding(
      { changeId: CHANGE_A, worktreePath: WORKTREE_A },
      sessionFor(CHANGE_A, ""),
    );
    expect(verdict.bound).toBe(false);
  });

  it("gives the SAME verdict regardless of how the session was resolved (NFR-SEC-02)", () => {
    // The guard is a pure function over identity; it does not know or care
    // whether the session is live / resumed / spawned. Same inputs ⇒ same
    // verdict. We prove it by asserting determinism across repeated calls
    // with identical identity (the resolution kind is not an input).
    const req = { changeId: CHANGE_A, worktreePath: WORKTREE_A };
    const good = sessionFor(CHANGE_A, WORKTREE_A);
    const bad = sessionFor(CHANGE_B, WORKTREE_A);
    expect(checkSessionBinding(req, good).bound).toBe(true);
    expect(checkSessionBinding(req, good).bound).toBe(true);
    expect(checkSessionBinding(req, bad).bound).toBe(false);
    expect(checkSessionBinding(req, bad).bound).toBe(false);
  });
});
