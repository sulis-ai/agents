// WP-005 — productCounts: the one client-side count + scope-filter helper
// (ADR-002, TDD "Counts & the 'Unassigned' scope — client-derived").
//
// The switcher's per-row counts and the board's Unassigned view are BOTH
// derived from the already-fetched (All-scoped) change list — no new endpoint
// (TDD). This helper is the single home for that derivation (the WP's Blue
// 2-consumer extraction: switcher row counts + board scope filter). Counts are:
//   - All       = total changes
//   - Unassigned = changes with forProduct == null/undefined
//   - per product = changes whose forProduct === productId
//
// The Unassigned scope is a CLIENT sentinel: the server scopes by ?product=<id>
// and has no "unassigned" value, so the sentinel must never reach the wire —
// scopeToProductParam() returns null for both All and Unassigned (fetch the
// full list), and filterChangesByScope() applies the Unassigned predicate
// client-side.

import { describe, it, expect } from "vitest";
import type { Change } from "../../../shared/api-types";
import {
  UNASSIGNED_SCOPE,
  countForScope,
  scopeToProductParam,
  filterChangesByScope,
} from "../lib/productCounts";

const ACME = "dna:product:01ACME00000000000000000000";
const HELP = "dna:product:01HELP00000000000000000000";

function change(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "fix-thing",
    primitive: "fix",
    branch: "fix/thing",
    worktreePath: "/tmp/worktree",
    intent: "Fix the broken thing",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-05-26T11:00:00Z",
    updatedAt: "2026-05-26T11:55:00Z",
    stage: "implement",
    liveness: { status: "unknown", reason: "no session" },
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
    lastActivityAt: null,
    ...overrides,
  };
}

// A spread of changes: 2 on Acme, 1 on Helpdesk, 2 unassigned (one null, one
// undefined — both read as "no product"). All = 5.
const CHANGES: Change[] = [
  change({ changeId: "a1", forProduct: ACME }),
  change({ changeId: "a2", forProduct: ACME }),
  change({ changeId: "h1", forProduct: HELP }),
  change({ changeId: "u1", forProduct: null }),
  change({ changeId: "u2" }), // forProduct omitted → undefined
];

describe("countForScope", () => {
  it("counts ALL changes for the All scope (null)", () => {
    expect(countForScope(CHANGES, null)).toBe(5);
  });

  it("counts UNASSIGNED changes (forProduct null OR undefined) for the Unassigned scope", () => {
    expect(countForScope(CHANGES, UNASSIGNED_SCOPE)).toBe(2);
  });

  it("counts changes assigned to a specific product", () => {
    expect(countForScope(CHANGES, ACME)).toBe(2);
    expect(countForScope(CHANGES, HELP)).toBe(1);
  });

  it("is zero for a product with no changes", () => {
    expect(countForScope(CHANGES, "dna:product:01NONE0000000000000000000")).toBe(0);
  });

  it("handles an empty list", () => {
    expect(countForScope([], null)).toBe(0);
    expect(countForScope([], UNASSIGNED_SCOPE)).toBe(0);
  });
});

describe("scopeToProductParam — the server contract stays untouched", () => {
  it("returns null for the All scope (no ?product=)", () => {
    expect(scopeToProductParam(null)).toBeNull();
  });

  it("returns null for the Unassigned scope — the sentinel NEVER reaches the wire", () => {
    // The server has no "unassigned" scope value (TDD); Unassigned is rendered
    // by fetching the All list and filtering client-side.
    expect(scopeToProductParam(UNASSIGNED_SCOPE)).toBeNull();
  });

  it("passes a real product id straight through to ?product=", () => {
    expect(scopeToProductParam(ACME)).toBe(ACME);
  });
});

describe("filterChangesByScope — the client-side Unassigned view", () => {
  it("returns every change for the All scope (no client filter)", () => {
    expect(filterChangesByScope(CHANGES, null)).toHaveLength(5);
  });

  it("returns only unassigned changes for the Unassigned scope", () => {
    const filtered = filterChangesByScope(CHANGES, UNASSIGNED_SCOPE);
    expect(filtered.map((c) => c.changeId).sort()).toEqual(["u1", "u2"]);
  });

  it("returns the list unchanged for a real product scope (server already scoped it)", () => {
    // When a product is active the SERVER already returned only that product's
    // changes (?product=<id>); the client filter is a no-op pass-through.
    const acmeOnly = CHANGES.filter((c) => c.forProduct === ACME);
    expect(filterChangesByScope(acmeOnly, ACME)).toEqual(acmeOnly);
  });
});
