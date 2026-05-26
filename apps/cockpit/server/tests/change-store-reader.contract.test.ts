// WP-003 — Contract test for ChangeStoreReader (TDD §14.1, ADR-008).
//
// This file defines the behaviour every implementation of the port must
// satisfy. The adapter test and fake test each import `runContract` and
// supply their own factory (one shells out to the Python helper against
// a seeded SULIS_STATE_DIR; the other is in-memory). Same assertions,
// two implementations — that is the boundary parity guarantee ADR-008
// asks for.
//
// The factory's signature is asymmetric on purpose: implementations
// often need fixture data to be seeded before instantiation (the
// adapter needs files on disk; the fake needs an array in memory). The
// `setup` hook lets each factory prepare its world without leaking the
// shape into the contract.
//
// Per MEA-09: no mocks for the change-store boundary. The adapter
// factory uses real fixtures on disk. The fake is its own simplest
// reference implementation.

import { describe, it, expect, beforeEach, afterEach } from "vitest";

import type {
  ChangeStoreReader,
  ChangeStoreRecord,
} from "../ports/ChangeStoreReader";

export type ContractFixture = {
  changeId: string;
  handle: string;
  slug: string;
  primitive: string;
  branch: string;
  worktreePath: string;
  intent: string;
  baseBranch: string;
  baseSha: string | null;
  createdAt: string;
  /** Optional state.json overlay; if absent, the change.json stage is final. */
  liveStage?: string;
  /** Stage value as it appears in change.json (the seed value). */
  seedStage: string;
};

export type ContractFactory = {
  /** Called once before each test, with the canonical fixture set. */
  setup: (fixtures: ContractFixture[]) => Promise<ChangeStoreReader>;
  /** Called once after each test for cleanup. */
  teardown?: () => Promise<void>;
};

/**
 * Convert a contract fixture to the expected `ChangeStoreRecord` shape
 * a conforming implementation should return for that fixture (with
 * live-stage overlay applied if `liveStage` is set).
 *
 * `updatedAt` is determined by the implementation — for the seeded
 * adapter, the test computes it from the same `liveStage` block
 * (state.json's `updated_at`); for the fake, the fixture's overlay is
 * passed through directly.
 */
export function expectedStageFor(fx: ContractFixture): string {
  return fx.liveStage ?? fx.seedStage;
}

export function runContract(name: string, factory: ContractFactory): void {
  describe(`ChangeStoreReader contract — ${name}`, () => {
    const fxOlder: ContractFixture = {
      changeId: "01CCCAAAAAAAAAAAAAAAAAAAA1",
      handle: "CH-01CCCA",
      slug: "older-change",
      primitive: "create",
      branch: "change/older-change",
      worktreePath: "/tmp/older-worktree",
      intent: "an older change",
      baseBranch: "dev",
      baseSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      createdAt: "2026-05-20T10:00:00Z",
      // No state.json overlay — change.json's stage is the final answer.
      seedStage: "recon",
    };
    const fxMiddle: ContractFixture = {
      changeId: "01CCCBBBBBBBBBBBBBBBBBBBB2",
      handle: "CH-01CCCB",
      slug: "middle-change",
      primitive: "fix",
      branch: "fix/middle-change",
      worktreePath: "/tmp/middle-worktree",
      intent: "a middle change",
      baseBranch: "dev",
      baseSha: null,
      createdAt: "2026-05-22T10:00:00Z",
      liveStage: "implement",
      seedStage: "recon",
    };
    const fxNewer: ContractFixture = {
      changeId: "01CCCDDDDDDDDDDDDDDDDDDDD3",
      handle: "CH-01CCCD",
      slug: "newer-change",
      primitive: "create",
      branch: "change/newer-change",
      worktreePath: "/tmp/newer-worktree",
      intent: "the newest change",
      baseBranch: "dev",
      baseSha: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      createdAt: "2026-05-25T10:00:00Z",
      liveStage: "review",
      seedStage: "recon",
    };

    const allFixtures = [fxOlder, fxMiddle, fxNewer];

    let reader: ChangeStoreReader;

    afterEach(async () => {
      if (factory.teardown) {
        await factory.teardown();
      }
    });

    describe("listAllChanges()", () => {
      beforeEach(async () => {
        reader = await factory.setup(allFixtures);
      });

      it("returns an array sorted by createdAt descending", async () => {
        const records = await reader.listAllChanges();
        expect(records).toHaveLength(3);
        expect(records.map((r) => r.changeId)).toEqual([
          fxNewer.changeId,
          fxMiddle.changeId,
          fxOlder.changeId,
        ]);
      });

      it("overlays the live stage from state.json onto each record", async () => {
        const records = await reader.listAllChanges();
        const byId = new Map(records.map((r) => [r.changeId, r]));
        expect(byId.get(fxMiddle.changeId)?.stage).toBe("implement");
        expect(byId.get(fxNewer.changeId)?.stage).toBe("review");
      });

      it("falls back to change.json's stage when no state.json overlay exists", async () => {
        const records = await reader.listAllChanges();
        const older = records.find((r) => r.changeId === fxOlder.changeId);
        expect(older?.stage).toBe("recon");
      });

      it("returns camelCase fields (no snake_case leakage)", async () => {
        const records = await reader.listAllChanges();
        const sample = records[0]!;
        // Spot-check every camelCase field exists.
        expect(sample.changeId).toBeDefined();
        expect(sample.worktreePath).toBeDefined();
        expect(sample.baseBranch).toBeDefined();
        expect(sample.createdAt).toBeDefined();
        expect(sample.updatedAt).toBeDefined();
        // Spot-check no snake_case slipped through.
        const keys = Object.keys(sample);
        for (const k of keys) {
          expect(k).not.toMatch(/_/);
        }
      });
    });

    describe("listAllChanges() — empty store", () => {
      it("returns [] when no changes exist", async () => {
        reader = await factory.setup([]);
        const records = await reader.listAllChanges();
        expect(records).toEqual([]);
      });
    });

    describe("readChangeRecord()", () => {
      beforeEach(async () => {
        reader = await factory.setup(allFixtures);
      });

      it("returns null for an unknown id", async () => {
        const record = await reader.readChangeRecord("01UNKNOWN00000000000000000");
        expect(record).toBeNull();
      });

      it("returns the matching record (with live stage overlay) for a known id", async () => {
        const record = await reader.readChangeRecord(fxMiddle.changeId);
        expect(record).not.toBeNull();
        expect(record?.changeId).toBe(fxMiddle.changeId);
        expect(record?.handle).toBe(fxMiddle.handle);
        expect(record?.slug).toBe(fxMiddle.slug);
        expect(record?.stage).toBe(expectedStageFor(fxMiddle));
        expect(record?.baseSha).toBe(fxMiddle.baseSha);
      });
    });

    describe("readChangeStage()", () => {
      beforeEach(async () => {
        reader = await factory.setup(allFixtures);
      });

      it("returns the live-overlay stage for a known id", async () => {
        const stage = await reader.readChangeStage(fxNewer.changeId);
        expect(stage).toBe("review");
      });

      it("falls back to the change.json stage when no overlay exists", async () => {
        const stage = await reader.readChangeStage(fxOlder.changeId);
        expect(stage).toBe("recon");
      });

      it("returns the same stage listAllChanges reports for the same id", async () => {
        const all = await reader.listAllChanges();
        const middleFromList = all.find((r) => r.changeId === fxMiddle.changeId);
        const directStage = await reader.readChangeStage(fxMiddle.changeId);
        expect(directStage).toBe(middleFromList?.stage);
      });

      it("returns null for an unknown id", async () => {
        const stage = await reader.readChangeStage("01UNKNOWN00000000000000000");
        expect(stage).toBeNull();
      });
    });

    describe("record shape", () => {
      it("each record satisfies the ChangeStoreRecord shape (typed)", async () => {
        reader = await factory.setup(allFixtures);
        const records = await reader.listAllChanges();
        for (const r of records) {
          // Spot-check required fields with their basic kinds.
          expectShape(r);
        }
      });
    });
  });
}

// vitest's include pattern (tests/**/*.test.ts) matches this file. The
// contract is reusable — adapter + fake tests import `runContract` —
// but vitest will fail "no test suite found" if the file has zero
// top-level suites. A trivial self-suite satisfies the runner without
// changing the semantics. The substantive coverage runs through the
// importing test files.
describe("ChangeStoreReader contract module", () => {
  it("exports runContract", () => {
    expect(typeof runContract).toBe("function");
  });
});

function expectShape(r: ChangeStoreRecord): void {
  expect(typeof r.changeId).toBe("string");
  expect(typeof r.handle).toBe("string");
  expect(typeof r.slug).toBe("string");
  expect(typeof r.primitive).toBe("string");
  expect(typeof r.branch).toBe("string");
  expect(typeof r.worktreePath).toBe("string");
  expect(typeof r.intent).toBe("string");
  expect(typeof r.baseBranch).toBe("string");
  expect(["string", "object"]).toContain(typeof r.baseSha); // string | null
  expect(typeof r.createdAt).toBe("string");
  expect(typeof r.updatedAt).toBe("string");
  expect([
    "recon",
    "specify",
    "design",
    "implement",
    "review",
    "ship",
  ]).toContain(r.stage);
}
