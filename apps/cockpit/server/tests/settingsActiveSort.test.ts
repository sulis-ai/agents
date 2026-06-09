// WP-002 — Unit test for the extracted activeSortedByName helper (Blue).
//
// The helper is the shared read primitive `readTree` uses at both levels and
// WP-005's real adapter will reuse. Pinning it directly (not only through the
// fake's contract) means a future change to the filter/sort can't silently
// drift the real adapter away from the contract.

import { describe, it, expect } from "vitest";

import {
  activeSortedByName,
  isActive,
  byName,
} from "../adapters/settingsActiveSort";

describe("activeSortedByName", () => {
  it("filters out non-active rows and sorts the rest by name", () => {
    const rows = [
      { name: "Zeta", status: "active" },
      { name: "Alpha", status: "active" },
      { name: "Gone", status: "deleted" },
      { name: "Mu", status: "active" },
    ];
    expect(activeSortedByName(rows).map((r) => r.name)).toEqual([
      "Alpha",
      "Mu",
      "Zeta",
    ]);
  });

  it("treats any non-active status as hidden (allow-list, not deny-list)", () => {
    const rows = [
      { name: "Active", status: "active" },
      { name: "Archived", status: "archived" },
      { name: "Purged", status: "purged" },
      { name: "Future", status: "some-future-status" },
    ];
    expect(activeSortedByName(rows).map((r) => r.name)).toEqual(["Active"]);
  });

  it("does not mutate its input", () => {
    const rows = [
      { name: "B", status: "active" },
      { name: "A", status: "active" },
    ];
    activeSortedByName(rows);
    expect(rows.map((r) => r.name)).toEqual(["B", "A"]);
  });

  it("isActive is true only for active", () => {
    expect(isActive({ status: "active" })).toBe(true);
    expect(isActive({ status: "deleted" })).toBe(false);
  });

  it("byName orders ascending and is stable for equal names", () => {
    expect(byName({ name: "a" }, { name: "b" })).toBeLessThan(0);
    expect(byName({ name: "b" }, { name: "a" })).toBeGreaterThan(0);
    expect(byName({ name: "a" }, { name: "a" })).toBe(0);
  });
});
