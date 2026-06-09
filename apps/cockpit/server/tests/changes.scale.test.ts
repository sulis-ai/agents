// WP-002 — bounded fan-out (MUC-2 / NFR-PERF-3, S-25).
//
// The enrichment runs inside the SAME single bounded Promise.all the feed
// already uses for liveness — there is no per-card request and no unbounded
// loop. This test seeds hundreds of changes and asserts (a) the feed returns
// every one, fully enriched, and (b) it completes within a generous bound
// (a per-card network round-trip would blow this; a bounded in-process
// Promise.all does not).

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { Change } from "../../shared/api-types";

function record(i: number, worktreePath: string): ChangeStoreRecord {
  const id = `01SCALE${String(i).padStart(4, "0")}`;
  return {
    changeId: id,
    handle: `CH-${id}`,
    slug: `scale-${i}`,
    primitive: "create",
    branch: `change/scale-${i}`,
    worktreePath,
    intent: `change ${i}`,
    baseBranch: "main",
    baseSha: "deadbeef",
    // Descending createdAt so the most-recent-first order is deterministic.
    createdAt: `2026-05-01T00:00:${String(i % 60).padStart(2, "0")}Z`,
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "implement",
  };
}

describe("GET /api/changes — bounded fan-out (S-25)", () => {
  it("enriches hundreds of changes in one bounded pass and returns them all", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    // All point at the same (absent) worktree → every read fails soft to
    // unknown; the point is the COUNT and that it completes bounded.
    const absentWt = "/tmp/absent-wp002-scale";
    try {
      const N = 400;
      const records = Array.from({ length: N }, (_, i) => record(i, absentWt));
      const reader = new FakeChangeStoreReader(records);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });

      const started = Date.now();
      const res = await request(app).get("/api/changes");
      const elapsed = Date.now() - started;

      expect(res.status).toBe(200);
      const body = res.body as Change[];
      expect(body).toHaveLength(N);
      // Every row is fully enriched even at scale.
      for (const row of body) {
        expect(row.needsAttention).toHaveProperty("flagged");
        expect(row.health).toHaveProperty("state");
        expect(row).toHaveProperty("lastActivityAt");
      }
      // Generous bound: a bounded in-process fan-out over 400 best-effort
      // (mostly-absent) reads completes well within 15s even on a slow CI
      // box; an N+1 network pattern would not.
      expect(elapsed).toBeLessThan(15_000);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
    }
  }, 20_000);
});
