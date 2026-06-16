// WP-010 — GET /api/changes + GET /api/changes/:id route tests.
//
// Drives the app through supertest (no real port bind). Uses a
// FakeChangeStoreReader so the test isolates the route layer from the
// real Python helper. The integration smoke (app.integration.test.ts)
// covers the wired-up combined surface.

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/never-used-in-this-test",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
    stage: "specify",
    ...overrides,
  };
}

describe("GET /api/changes — active-Product scope (WP-003, trivial single-Product)", () => {
  it("returns the active Product's change set; the trivial single-Product case returns all, shape unchanged (FR-37 trivial)", async () => {
    // The single-Product Tenant is the trivial case: one Product, implicitly
    // active → the board receives every change. This pins the seam-owns-scope
    // behaviour (ADR-009) without the full productScope roll-up (WP-008): the
    // route returns the same shape it always did, scoped through the helper.
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01AAA", handle: "CH-01AAA", createdAt: "2026-05-10T00:00:00Z" }),
      record({ changeId: "01BBB", handle: "CH-01BBB", createdAt: "2026-05-01T00:00:00Z" }),
    ]);
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never-used-here",
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const body = res.body as Array<{ changeId: string; stage: string; liveness: { status: string } }>;
      // Trivial scope: every change in the store is the active Product's.
      expect(body.map((r) => r.changeId).sort()).toEqual(["01AAA", "01BBB"]);
      // Shape unchanged: the same enriched Change rows (stage + liveness present).
      for (const row of body) {
        expect(typeof row.stage).toBe("string");
        expect(typeof row.liveness.status).toBe("string");
      }
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });
});

describe("GET /api/changes", () => {
  it("returns the change list with liveness shape attached to each row", async () => {
    const reader = new FakeChangeStoreReader([
      record({
        changeId: "01AAA",
        handle: "CH-01AAA",
        createdAt: "2026-05-10T00:00:00Z",
      }),
      record({
        changeId: "01BBB",
        handle: "CH-01BBB",
        createdAt: "2026-05-01T00:00:00Z",
      }),
    ]);
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never-used-here",
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      expect(res.headers["content-type"]).toMatch(/application\/json/);
      const body = res.body as Array<{
        changeId: string;
        liveness: { status: string };
      }>;
      expect(body).toHaveLength(2);
      // Most-recent-first ordering (matches the adapter's contract).
      expect(body[0]?.changeId).toBe("01AAA");
      expect(body[1]?.changeId).toBe("01BBB");
      // Liveness attached to every record. No session record in our temp
      // state dir, so the change reads as idle: "not-running" (a definite
      // "nothing is live here"), not the vaguer "unknown".
      for (const row of body) {
        expect(row.liveness.status).toBe("not-running");
      }
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });

  it("attaches liveness 'running' when the recorded pid is alive (signal 0 to ourselves)", async () => {
    const reader = new FakeChangeStoreReader([record({ changeId: "01CCC" })]);
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      // Seed session.json with our own pid — process.kill(self, 0)
      // never throws, so liveness must report "running".
      const sessionDir = join(tmpState, "changes", "01CCC");
      await mkdir(sessionDir, { recursive: true });
      await writeFile(
        join(sessionDir, "session.json"),
        JSON.stringify({
          change_id: "01CCC",
          pid: process.pid,
          pid_kind: "session",
          script_path: "/tmp/x",
          spawned_at: "2026-05-26T00:00:00Z",
        }),
        "utf8",
      );

      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never-used-here",
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const body = res.body as Array<{
        changeId: string;
        liveness: { status: string; pid?: number };
      }>;
      expect(body[0]?.liveness.status).toBe("running");
      expect(body[0]?.liveness.pid).toBe(process.pid);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });
});

describe("GET /api/changes/:id", () => {
  it("returns the single change record with transcriptPaths", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const tmpWorktree = await mkdtemp(join(tmpdir(), "wt-"));
    try {
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01XYZ", worktreePath: tmpWorktree }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes/01XYZ");
      expect(res.status).toBe(200);
      const body = res.body as { changeId: string; transcriptPaths: string[] };
      expect(body.changeId).toBe("01XYZ");
      // No transcripts seeded → empty array, not undefined.
      expect(Array.isArray(body.transcriptPaths)).toBe(true);
      expect(body.transcriptPaths).toEqual([]);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(tmpWorktree, { recursive: true, force: true });
    }
  });

  it("returns 404 with NOT_FOUND code for unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/changes/does-not-exist");
      expect(res.status).toBe(404);
      const body = res.body as { error: string; code: string };
      expect(body.code).toBe("NOT_FOUND");
      expect(typeof body.error).toBe("string");
      expect(body.error.length).toBeGreaterThan(0);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });
});
