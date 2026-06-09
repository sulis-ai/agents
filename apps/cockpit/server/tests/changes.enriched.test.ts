// WP-002 — GET /api/changes enriched-feed integration tests (FR-30/31/40,
// ADR-002). Drives the app through supertest against a FakeChangeStoreReader
// with real temp-dir worktrees so the enrichment reads (open-blocker,
// rigor, tests-state, last-activity) operate on real on-disk signals.
//
// Each feed row MUST carry needsAttention + health + lastActivityAt, derived
// (not the WP-001 placeholders). idle-but-fine stays flagged:false (FR-12).

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { Change } from "../../shared/api-types";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ENR",
    handle: "CH-01ENR",
    slug: "enriched",
    primitive: "create",
    branch: "change/enriched",
    worktreePath: "/tmp/never-used",
    intent: "enriched change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "specify",
    ...overrides,
  };
}

describe("GET /api/changes — enriched rows (FR-30/31/40)", () => {
  it("each row carries needsAttention, health and lastActivityAt", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wt = await mkdtemp(join(tmpdir(), "wt-enr-"));
    try {
      // A specify-stage change WITH a spec → rigor ok; no ci-state →
      // tests unknown; rigor determinable+ok → health on-track.
      await mkdir(join(wt, ".specifications", "demo"), { recursive: true });
      await writeFile(
        join(wt, ".specifications", "demo", "SRD.md"),
        "# spec",
        "utf8",
      );
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01ENR", worktreePath: wt, stage: "specify" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const body = res.body as Change[];
      const row = body[0]!;
      // needsAttention shape present + derived (not undefined).
      expect(row.needsAttention).toEqual({ flagged: false, reason: null });
      // health derived: spec present at specify → on-track (rigor carries it).
      expect(row.health.state).toBe("on-track");
      expect(typeof row.health.reason).toBe("string");
      // lastActivityAt present: no transcript → falls back to updatedAt.
      expect(row.lastActivityAt).toBe("2026-05-02T00:00:00Z");
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("a fresh Recon change with nothing behind it reads health unknown, not on-track (FR-31)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wt = await mkdtemp(join(tmpdir(), "wt-recon-"));
    try {
      // Recon: no required artifact (rigor determinable+ok) BUT no tests
      // recorded. Recon's rigor is trivially ok+determinable, so per
      // computeHealth this is on-track... UNLESS rigor is indeterminate.
      // For a brand-new recon change we still want honest "too early".
      // The producer maps Recon-with-no-signal to the unknown read by
      // treating Recon rigor as NOT-yet-determinable until any artifact
      // exists. Assert the honest read: not a false on-track.
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01FRESH", worktreePath: wt, stage: "recon", updatedAt: "" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const body = res.body as Change[];
      const row = body[0]!;
      expect(row.health.state).toBe("unknown");
      expect(row.lastActivityAt).toBeNull();
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("a blocked change (open BLOCKER) is flagged, with reason 'blocked'", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wt = await mkdtemp(join(tmpdir(), "wt-blk-"));
    try {
      const wpDir = join(wt, ".architecture", "demo", "work-packages");
      await mkdir(wpDir, { recursive: true });
      await writeFile(join(wpDir, "BLOCKER-WP-002.md"), "# parked", "utf8");
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01BLK", worktreePath: wt, stage: "implement" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const row = (res.body as Change[])[0]!;
      expect(row.needsAttention).toEqual({ flagged: true, reason: "blocked" });
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("a red-tests change reads off-track (BR-10)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wt = await mkdtemp(join(tmpdir(), "wt-red-"));
    try {
      await mkdir(join(wt, ".sulis"), { recursive: true });
      await writeFile(
        join(wt, ".sulis", "ci-state.json"),
        JSON.stringify({ state: "red" }),
        "utf8",
      );
      // give it a spec so rigor isn't the off-track cause; tests-red is.
      await mkdir(join(wt, ".specifications", "demo"), { recursive: true });
      await writeFile(join(wt, ".specifications", "demo", "SRD.md"), "# s", "utf8");
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01RED", worktreePath: wt, stage: "specify" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const row = (res.body as Change[])[0]!;
      expect(row.health.state).toBe("off-track");
      expect(row.health.reason).toBe("tests failing");
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(wt, { recursive: true, force: true });
    }
  });
});
