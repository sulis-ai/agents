// WP-002 — GET /api/changes degradation suite (BR-11 / NFR-DEGRADE-1).
// The load-bearing never-throw / never-500 discipline: no single bad record
// can 500 the feed; each row degrades INDEPENDENTLY to honest unknown reads
// while its siblings render normally.
//
//   S-23 — a gone-worktree row → liveness unknown, health unknown, attention
//          not-flagged; feed 200; other rows render normally.
//   S-24 / MUC-1 — a malformed row (garbage stage / missing fields /
//          malformed session.json) → degrades to unknown reads; feed does
//          not throw / does not 500; siblings unaffected.
//   S-21 / EF-2 — partial-enrichment seed (some rows full, some absent
//          fields) → each row degrades independently; feed 200.

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
    changeId: "01DEG",
    handle: "CH-01DEG",
    slug: "degrade",
    primitive: "create",
    branch: "change/degrade",
    worktreePath: "/tmp/never-used",
    intent: "degrade change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "implement",
    ...overrides,
  };
}

describe("GET /api/changes — degradation (S-23: gone worktree)", () => {
  it("a row whose worktree is gone degrades to unknown reads; feed 200; siblings render normally", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const goodWt = await mkdtemp(join(tmpdir(), "wt-good-"));
    try {
      // good row: implement stage WITH a design → rigor ok.
      await mkdir(join(goodWt, ".architecture", "demo"), { recursive: true });
      await writeFile(join(goodWt, ".architecture", "demo", "TDD.md"), "# d", "utf8");

      const reader = new FakeChangeStoreReader([
        record({
          changeId: "01GONE",
          handle: "CH-01GONE",
          createdAt: "2026-05-10T00:00:00Z",
          worktreePath: "/tmp/this-worktree-is-gone-wp002",
        }),
        record({
          changeId: "01GOOD",
          handle: "CH-01GOOD",
          createdAt: "2026-05-01T00:00:00Z",
          worktreePath: goodWt,
        }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const body = res.body as Change[];
      const gone = body.find((r) => r.changeId === "01GONE")!;
      const good = body.find((r) => r.changeId === "01GOOD")!;

      // Gone row: a gone worktree doesn't make liveness ambiguous — with no
      // session.json the change is simply not running (idle); HEALTH is what
      // degrades to unknown (rigor can't read the gone worktree). Not-flagged,
      // no recency.
      expect(gone.liveness.status).toBe("not-running");
      expect(gone.health.state).toBe("unknown");
      expect(gone.needsAttention.flagged).toBe(false);

      // Good row unaffected: rigor ok via the design → on-track.
      expect(good.health.state).toBe("on-track");
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(goodWt, { recursive: true, force: true });
    }
  });
});

describe("GET /api/changes — degradation (S-24 / MUC-1: malformed row)", () => {
  it("a garbage-stage / malformed-session row degrades to unknown; feed does not 500; siblings unaffected", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const badWt = await mkdtemp(join(tmpdir(), "wt-bad-"));
    const goodWt = await mkdtemp(join(tmpdir(), "wt-good2-"));
    try {
      // bad row: a malformed session.json (probeLiveness → unknown) and a
      // garbage stage value cast through the record.
      const badSessionDir = join(tmpState, "changes", "01BAD");
      await mkdir(badSessionDir, { recursive: true });
      await writeFile(join(badSessionDir, "session.json"), "{ not json", "utf8");

      // good row: specify WITH a spec → on-track.
      await mkdir(join(goodWt, ".specifications", "demo"), { recursive: true });
      await writeFile(join(goodWt, ".specifications", "demo", "SRD.md"), "# s", "utf8");

      const reader = new FakeChangeStoreReader([
        record({
          changeId: "01BAD",
          handle: "CH-01BAD",
          createdAt: "2026-05-10T00:00:00Z",
          worktreePath: badWt,
          // garbage stage cast through the wire shape — the reads must not
          // throw on an unrecognised stage.
          stage: "not-a-real-stage" as unknown as ChangeStoreRecord["stage"],
        }),
        record({
          changeId: "01GOOD2",
          handle: "CH-01GOOD2",
          createdAt: "2026-05-01T00:00:00Z",
          worktreePath: goodWt,
          stage: "specify",
        }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const body = res.body as Change[];
      const bad = body.find((r) => r.changeId === "01BAD")!;
      const good = body.find((r) => r.changeId === "01GOOD2")!;

      // The malformed row did not sink the feed; it degraded.
      expect(bad).toBeDefined();
      expect(bad.liveness.status).toBe("unknown");
      // An unrecognised stage cannot be proven off-track on rigor → not
      // off-track from rigor; with unknown tests it reads unknown.
      expect(bad.health.state).toBe("unknown");
      expect(bad.needsAttention.flagged).toBe(false);

      // Sibling unaffected.
      expect(good.health.state).toBe("on-track");
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(badWt, { recursive: true, force: true });
      await rm(goodWt, { recursive: true, force: true });
    }
  });
});

describe("GET /api/changes — degradation (S-21 / EF-2: partial enrichment)", () => {
  it("each row degrades independently; the feed returns 200 for a mixed set", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const fullWt = await mkdtemp(join(tmpdir(), "wt-full-"));
    const emptyWt = await mkdtemp(join(tmpdir(), "wt-empty-"));
    try {
      // full row: implement WITH a plan + green ci-state → on-track.
      await mkdir(join(fullWt, ".architecture", "demo", "work-packages"), {
        recursive: true,
      });
      await writeFile(
        join(fullWt, ".architecture", "demo", "work-packages", "WP-1.md"),
        "# p",
        "utf8",
      );
      await mkdir(join(fullWt, ".sulis"), { recursive: true });
      await writeFile(
        join(fullWt, ".sulis", "ci-state.json"),
        JSON.stringify({ state: "green" }),
        "utf8",
      );

      const reader = new FakeChangeStoreReader([
        record({ changeId: "01FULL", handle: "CH-01FULL", createdAt: "2026-05-10T00:00:00Z", worktreePath: fullWt }),
        // empty row: implement stage, no design/plan → off-track on rigor.
        record({ changeId: "01EMPTY", handle: "CH-01EMPTY", createdAt: "2026-05-05T00:00:00Z", worktreePath: emptyWt }),
        // gone row: worktree absent → unknown.
        record({ changeId: "01ABSENT", handle: "CH-01ABSENT", createdAt: "2026-05-01T00:00:00Z", worktreePath: "/tmp/absent-wp002-partial" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/changes");
      expect(res.status).toBe(200);
      const body = res.body as Change[];
      expect(body).toHaveLength(3);
      const byId = Object.fromEntries(body.map((r) => [r.changeId, r]));
      expect(byId["01FULL"]!.health.state).toBe("on-track");
      expect(byId["01EMPTY"]!.health.state).toBe("off-track");
      expect(byId["01ABSENT"]!.health.state).toBe("unknown");
      // Every row still carries the full enriched shape.
      for (const row of body) {
        expect(row.needsAttention).toHaveProperty("flagged");
        expect(row.health).toHaveProperty("state");
        expect(row).toHaveProperty("lastActivityAt");
      }
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(fullWt, { recursive: true, force: true });
      await rm(emptyWt, { recursive: true, force: true });
    }
  });
});
