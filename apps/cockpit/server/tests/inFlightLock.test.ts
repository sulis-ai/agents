// WP-005 — inFlightLock unit test (FR-20, NFR-REL-03; ADR-001 §one-in-flight).
//
// One message per change at a time. The lock is per-change, in-memory, and is
// also a resource bulkhead (§3.2). acquire returns a release handle; a second
// acquire while held is refused (the route maps that to SESSION_BUSY 409).
// Releasing frees the change so the NEXT send (a resend after a broken stream
// is a NEW message, Q10) can proceed.

import { describe, it, expect } from "vitest";

import { InFlightLock } from "../lib/inFlightLock";

const CHANGE_A = "01CHANGEAAAAAAAAAAAAAAAAAA";
const CHANGE_B = "01CHANGEBBBBBBBBBBBBBBBBBB";

describe("InFlightLock (FR-20)", () => {
  it("acquires a free change and reports it held", () => {
    const lock = new InFlightLock();
    const handle = lock.acquire(CHANGE_A);
    expect(handle).not.toBeNull();
    expect(lock.isHeld(CHANGE_A)).toBe(true);
  });

  it("refuses a double-acquire of the same change (⇒ SESSION_BUSY)", () => {
    const lock = new InFlightLock();
    const first = lock.acquire(CHANGE_A);
    expect(first).not.toBeNull();
    const second = lock.acquire(CHANGE_A);
    expect(second).toBeNull();
  });

  it("holds locks per-change — a different change is unaffected", () => {
    const lock = new InFlightLock();
    lock.acquire(CHANGE_A);
    const other = lock.acquire(CHANGE_B);
    expect(other).not.toBeNull();
    expect(lock.isHeld(CHANGE_B)).toBe(true);
  });

  it("frees the change on release so a later send can acquire again", () => {
    const lock = new InFlightLock();
    const handle = lock.acquire(CHANGE_A);
    expect(handle).not.toBeNull();
    handle!.release();
    expect(lock.isHeld(CHANGE_A)).toBe(false);
    const again = lock.acquire(CHANGE_A);
    expect(again).not.toBeNull();
  });

  it("is idempotent on a double-release (no throw, stays free)", () => {
    const lock = new InFlightLock();
    const handle = lock.acquire(CHANGE_A);
    handle!.release();
    expect(() => handle!.release()).not.toThrow();
    expect(lock.isHeld(CHANGE_A)).toBe(false);
  });

  it("reports a not-held change as free", () => {
    const lock = new InFlightLock();
    expect(lock.isHeld(CHANGE_A)).toBe(false);
  });
});
