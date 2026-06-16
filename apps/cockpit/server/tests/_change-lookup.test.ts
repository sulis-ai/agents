// WP-002 (characterisation) — pins toWireChange's record→wire field
// mapping BEFORE the REORGANISE-Refactor that widens its signature.
//
// `toWireChange` has three consumers (the list route, the single-change
// detail route, the search route). WP-002 changes its signature from
// `(record, liveness)` to `(record, liveness, enrichment)` so the route
// gathers the attention/health/last-activity signals and the shaper stays
// pure. This characterisation test pins the parts that MUST NOT change
// across that refactor: every record field maps to its wire field
// verbatim, and the passed-in liveness is carried through untouched.
//
// Discipline (EP-07 / WPB-12): write the characterisation, confirm it
// passes, refactor, confirm it still passes. The enrichment assertions are
// added in lockstep with the signature change — the field-mapping
// assertions below are the invariant the refactor preserves.

import { describe, it, expect } from "vitest";

import { toWireChange } from "../routes/_change-lookup";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { Liveness, NeedsAttention, ChangeHealth } from "../../shared/api-types";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01CHAR",
    handle: "CH-01CHAR",
    slug: "char-demo",
    primitive: "create",
    branch: "change/char-demo",
    worktreePath: "/tmp/char-worktree",
    intent: "characterisation change",
    baseBranch: "main",
    baseSha: "cafef00d",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

const ENRICHMENT: {
  needsAttention: NeedsAttention;
  health: ChangeHealth;
  lastActivityAt: string | null;
} = {
  needsAttention: { flagged: false, reason: null },
  health: { state: "unknown", reason: "too early to tell" },
  lastActivityAt: null,
};

describe("toWireChange — record→wire field mapping (characterisation)", () => {
  it("maps every record field to its wire field verbatim", () => {
    const liveness: Liveness = { status: "not-running" };
    const wire = toWireChange(record(), liveness, ENRICHMENT);

    expect(wire.changeId).toBe("01CHAR");
    expect(wire.handle).toBe("CH-01CHAR");
    expect(wire.slug).toBe("char-demo");
    expect(wire.primitive).toBe("create");
    expect(wire.branch).toBe("change/char-demo");
    expect(wire.worktreePath).toBe("/tmp/char-worktree");
    expect(wire.intent).toBe("characterisation change");
    expect(wire.baseBranch).toBe("main");
    expect(wire.baseSha).toBe("cafef00d");
    expect(wire.createdAt).toBe("2026-05-01T00:00:00Z");
    expect(wire.updatedAt).toBe("2026-05-02T00:00:00Z");
    expect(wire.stage).toBe("design");
  });

  it("carries the passed-in liveness through untouched", () => {
    const liveness: Liveness = { status: "running", pid: 4242 };
    const wire = toWireChange(record(), liveness, ENRICHMENT);
    expect(wire.liveness).toEqual({ status: "running", pid: 4242 });
  });

  it("preserves a null baseSha (legacy record)", () => {
    const wire = toWireChange(
      record({ baseSha: null }),
      { status: "unknown", reason: "no session record" },
      ENRICHMENT,
    );
    expect(wire.baseSha).toBeNull();
  });

  it("stays a pure shaper — the enrichment it is handed is what it emits", () => {
    // The shaper does NOT derive attention/health/recency itself (the route
    // gathers them); it carries the enrichment it is given. This is the
    // REORGANISE invariant: gathering lives in the route, shaping in here.
    const liveness: Liveness = { status: "not-running" };
    const enrichment = {
      needsAttention: { flagged: true, reason: "blocked" as const },
      health: { state: "off-track" as const, reason: "tests failing" },
      lastActivityAt: "2026-05-03T12:00:00Z",
    };
    const wire = toWireChange(record(), liveness, enrichment);
    expect(wire.needsAttention).toEqual({ flagged: true, reason: "blocked" });
    expect(wire.health).toEqual({ state: "off-track", reason: "tests failing" });
    expect(wire.lastActivityAt).toBe("2026-05-03T12:00:00Z");
  });
});
