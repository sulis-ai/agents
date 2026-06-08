// Server config — change-listing timeout budget.
//
// The cockpit shells out to `sulis-list-changes list` through
// SulisChangeStoreReader to enumerate every change for the dashboard. A
// single git op is bounded by the tight shared `gitTimeoutMs` (5 s), but
// enumerating MANY changes (40+ in a busy repo) legitimately needs longer
// — and timing the listing out shows the founder a hard
// "Something went wrong loading your changes" error on a slow first load
// even though a retry succeeds.
//
// The listing therefore gets its OWN, more generous budget
// (`changeListTimeoutMs`) — matching the 30 s the recreate / starter
// adapters already use for I/O-heavy ops — WITHOUT loosening the shared
// `gitTimeoutMs` that diff / origin-attribution rely on staying tight.
//
// These pin both facts so a future edit can't silently fold the listing
// back onto the 5 s budget OR loosen the shared git budget.

import { describe, it, expect } from "vitest";

import { CONFIG } from "../config";

describe("CONFIG — change-listing timeout budget", () => {
  it("gives the change listing its own generous default (30 s, the I/O-heavy precedent)", () => {
    expect(CONFIG.changeListTimeoutMs).toBe(30_000);
  });

  it("keeps the shared per-single-git-op timeout tight (5 s) — NOT loosened by the listing fix", () => {
    expect(CONFIG.gitTimeoutMs).toBe(5_000);
  });

  it("makes the listing budget strictly more generous than a single git op", () => {
    expect(CONFIG.changeListTimeoutMs).toBeGreaterThan(CONFIG.gitTimeoutMs);
  });
});
