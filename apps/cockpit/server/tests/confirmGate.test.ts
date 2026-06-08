// WP-010 — confirm-gate tests (FR-N6 / NFR-DISC-04; ADR-007).
//
// The confirm gate is a PURE module — the WP-005 sessionBinding / inFlightLock
// sibling pattern. A read-and-propose turn needs NO confirmation; the ACT
// (mint or repo-create) requires an explicit token-matched confirm referencing
// the LIVE proposal. A stale / mismatched token is refused
// (DISCOVERY_CONFIRM_STALE); a declined / absent token leaves the gate CLOSED
// and the caller MUST NOT proceed. Deterministic, no fs/git/process/bridge.

import { describe, it, expect } from "vitest";

import {
  evaluateConfirmGate,
  type ConfirmGateRequest,
} from "../lib/discovery/confirmGate";

/** The live proposal the gate checks a confirm against. */
const LIVE = { confirmToken: "tok-live-abc" };

describe("evaluateConfirmGate", () => {
  it("a read/propose turn (no live proposal yet) is never an act — gate closed", () => {
    // phase=search/ask: there is nothing to confirm; the gate is closed (the
    // caller streams a read-only proposal turn, it never mints).
    const req: ConfirmGateRequest = { phase: "search" };
    const verdict = evaluateConfirmGate(req, null);
    expect(verdict.open).toBe(false);
  });

  it("a confirm matching the live proposal token opens the gate", () => {
    const req: ConfirmGateRequest = {
      phase: "confirm",
      confirmToken: "tok-live-abc",
    };
    const verdict = evaluateConfirmGate(req, LIVE);
    expect(verdict.open).toBe(true);
  });

  it("a confirm with a STALE / mismatched token is refused with DISCOVERY_CONFIRM_STALE", () => {
    const req: ConfirmGateRequest = {
      phase: "confirm",
      confirmToken: "tok-stale-xyz",
    };
    const verdict = evaluateConfirmGate(req, LIVE);
    expect(verdict.open).toBe(false);
    if (verdict.open === false) {
      expect(verdict.code).toBe("DISCOVERY_CONFIRM_STALE");
    }
  });

  it("a confirm with NO token against a live proposal is refused (cannot prove intent)", () => {
    const req: ConfirmGateRequest = { phase: "confirm" };
    const verdict = evaluateConfirmGate(req, LIVE);
    expect(verdict.open).toBe(false);
    if (verdict.open === false) {
      expect(verdict.code).toBe("DISCOVERY_CONFIRM_STALE");
    }
  });

  it("a confirm with NO live proposal at all is refused (nothing to confirm)", () => {
    const req: ConfirmGateRequest = {
      phase: "confirm",
      confirmToken: "tok-live-abc",
    };
    const verdict = evaluateConfirmGate(req, null);
    expect(verdict.open).toBe(false);
    if (verdict.open === false) {
      expect(verdict.code).toBe("DISCOVERY_CONFIRM_STALE");
    }
  });

  it("a declined / absent (search) phase carrying a token is still NOT an act", () => {
    // Defence in depth: only phase=confirm can ever open the gate. A token on a
    // non-confirm phase is ignored — the gate stays closed.
    const req: ConfirmGateRequest = {
      phase: "ask",
      confirmToken: "tok-live-abc",
    };
    const verdict = evaluateConfirmGate(req, LIVE);
    expect(verdict.open).toBe(false);
  });

  it("is deterministic — same inputs, same verdict (no clock / randomness)", () => {
    const req: ConfirmGateRequest = {
      phase: "confirm",
      confirmToken: "tok-live-abc",
    };
    const a = evaluateConfirmGate(req, LIVE);
    const b = evaluateConfirmGate(req, LIVE);
    expect(a).toEqual(b);
  });
});
