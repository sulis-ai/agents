// WP-004 — GET /api/changes/:id/status route tests (FR-04/05/12).
//
// Drives the app through supertest (no real port bind) with a
// FakeChangeStoreReader. The route composes existing reads (the change
// record, the located+parsed transcript, the liveness probe) and the two
// new pure libs (computeStatus + needsAttention) to return a ChangeStatus
// computed at READ time — never a stored periodic post (FR-05).
//
//   - 200 + ChangeStatus for a known change (shape: changeId, stage,
//     headline, needsAttention{flagged,reason}).
//   - 404 + { error, code: "NOT_FOUND" } for an unknown change.
//   - GET-only (the read-only gate proves no mutation verb is registered;
//     here we assert a POST is rejected by the app's 405 fallback).

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { ChangeStatus } from "../../shared/api-types";

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
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

describe("GET /api/changes/:id/status (FR-04/05/12)", () => {
  it("returns 200 + a read-time ChangeStatus for a known change", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", stage: "design" }),
    ]);
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes/01XYZ/status");
      expect(res.status).toBe(200);
      expect(res.headers["content-type"]).toMatch(/application\/json/);
      const body = res.body as ChangeStatus;
      expect(body.changeId).toBe("01XYZ");
      expect(body.stage).toBe("design");
      expect(typeof body.headline).toBe("string");
      expect(body.headline.length).toBeGreaterThan(0);
      expect(typeof body.needsAttention.flagged).toBe("boolean");
      // No blocker, no question, idle → not flagged, reason null.
      expect(body.needsAttention.flagged).toBe(false);
      expect(body.needsAttention.reason).toBeNull();
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
    }
  });

  it("returns 404 + NOT_FOUND for an unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/changes/does-not-exist/status");
      expect(res.status).toBe(404);
      const body = res.body as { error: string; code: string };
      expect(body.code).toBe("NOT_FOUND");
      expect(typeof body.error).toBe("string");
      expect(body.error.length).toBeGreaterThan(0);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });

  it("rejects a POST to the status route (read-only; 405)", async () => {
    const reader = new FakeChangeStoreReader([record({ changeId: "01XYZ" })]);
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).post("/api/changes/01XYZ/status");
      expect(res.status).toBe(405);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });
});
