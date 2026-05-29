// WP-003 — change-handle shape-guard tests (security hardening, TDD §3 Armor;
// Step-11 advisory folded forward).
//
// WP-003 is where request input first meets the recreate path: a tidied
// change is re-materialised by spawning `sulis-change recreate --handle
// <handle>` (SulisChangeRecreator). The handle is sourced off the change
// record (ADR-003), but defence-in-depth says validate its SHAPE before it
// reaches the spawn — a malformed handle must yield a typed failure, never a
// spawn.
//
// `assertSafeChangeHandle` mirrors SulisChangeStoreReader's CHANGE_ID_PATTERN
// (alphanumerics + underscore + hyphen — tight enough to refuse `..`, `/`,
// glob chars, whitespace, and shell metacharacters) and ADDS an explicit
// rejection of a LEADING '-'. A leading hyphen is the argparse / getopt
// flag-confusion vector: `recreate --handle -x` would otherwise let the
// handle masquerade as a flag to the spawned CLI. spawn-with-argv already
// prevents shell injection; this forecloses flag-confusion too.

import { describe, it, expect } from "vitest";

import {
  assertSafeChangeHandle,
  isSafeChangeHandle,
  InvalidChangeHandleError,
} from "../lib/changeHandleGuard";

describe("change-handle shape-guard", () => {
  describe("accepts legitimate handles", () => {
    const ok = [
      "01KSSV19SFWBJM01BM2XP6CZZ0", // ULID (Crockford base32)
      "feat-cockpit-contract-preview", // kebab handle
      "CH-01ABC", // the cockpit's CH- handle form
      "fix_thing_123", // underscores + digits
      "a", // single char
    ];
    for (const h of ok) {
      it(`accepts ${JSON.stringify(h)}`, () => {
        expect(isSafeChangeHandle(h)).toBe(true);
        expect(() => assertSafeChangeHandle(h)).not.toThrow();
      });
    }
  });

  describe("rejects a leading '-' (argparse flag-confusion)", () => {
    const flagShapes = ["-x", "--handle", "-rf", "-"];
    for (const h of flagShapes) {
      it(`rejects ${JSON.stringify(h)}`, () => {
        expect(isSafeChangeHandle(h)).toBe(false);
        expect(() => assertSafeChangeHandle(h)).toThrow(
          InvalidChangeHandleError,
        );
      });
    }
  });

  describe("rejects path-traversal / glob / shell-metachar / whitespace shapes", () => {
    const bad = [
      "../etc/passwd",
      "a/b",
      "a..b",
      "with space",
      "semi;rm",
      "glob*",
      "pipe|cat",
      "$(whoami)",
      "back`tick`",
      "nul\0byte",
      "", // empty
    ];
    for (const h of bad) {
      it(`rejects ${JSON.stringify(h)}`, () => {
        expect(isSafeChangeHandle(h)).toBe(false);
        expect(() => assertSafeChangeHandle(h)).toThrow(
          InvalidChangeHandleError,
        );
      });
    }
  });

  it("rejects a non-string handle defensively", () => {
    // The record's handle SHOULD be a string, but a corrupt record could
    // carry anything. The guard treats non-strings as unsafe rather than
    // coercing them toward the spawn.
    expect(isSafeChangeHandle(undefined as unknown as string)).toBe(false);
    expect(isSafeChangeHandle(null as unknown as string)).toBe(false);
    expect(isSafeChangeHandle(42 as unknown as string)).toBe(false);
  });

  it("InvalidChangeHandleError carries a stable code for the error mapper", () => {
    try {
      assertSafeChangeHandle("-x");
      throw new Error("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(InvalidChangeHandleError);
      expect((err as InvalidChangeHandleError).code).toBe(
        "INVALID_CHANGE_HANDLE",
      );
    }
  });
});
