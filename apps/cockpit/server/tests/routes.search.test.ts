// WP-007 — GET /api/search route tests (FR-10/11/12).
//
// Drives the app through supertest (no real port bind) with a
// FakeChangeStoreReader + real on-disk transcripts/brain so the FR-10
// keystone is a TRUE round-trip: a term that appears ONLY in a change's
// conversation (seeded as a real JSONL transcript in the mangled
// projects dir) narrows the result to that change.
//
// The route composes existing reads (list → scope to active Product →
// gather content [transcript + brain] + attention signals per change →
// searchChanges) and returns `{ results: Change[] }` (same row shape as
// the board list). GET-only; the read-only gate proves no mutation verb.

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import { mangleCwd } from "../lib/mangleCwd";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { Change } from "../../shared/api-types";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/never",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

/**
 * Seed a real Claude Code transcript whose first content record's `cwd`
 * matches the worktree (so locateTranscripts accepts it) and whose
 * conversation carries `userText`. Returns nothing; writes to disk.
 */
async function seedTranscript(
  projectsDir: string,
  worktreePath: string,
  userText: string,
): Promise<void> {
  const dir = join(projectsDir, mangleCwd(worktreePath));
  await mkdir(dir, { recursive: true });
  const lines = [
    JSON.stringify({
      type: "user",
      uuid: "u1",
      timestamp: "2026-05-01T00:00:01Z",
      cwd: worktreePath,
      message: { role: "user", content: userText },
    }),
    JSON.stringify({
      type: "assistant",
      uuid: "a1",
      timestamp: "2026-05-01T00:00:02Z",
      cwd: worktreePath,
      message: { role: "assistant", content: [{ type: "text", text: "ok." }] },
    }),
  ];
  await writeFile(join(dir, "session.jsonl"), lines.join("\n") + "\n", "utf8");
}

describe("GET /api/search (FR-10/11/12)", () => {
  it("KEYSTONE (FR-10): a term that appears ONLY in a change's conversation narrows the board to it", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wtHit = await mkdtemp(join(tmpdir(), "wt-hit-"));
    const wtMiss = await mkdtemp(join(tmpdir(), "wt-miss-"));
    try {
      const reader = new FakeChangeStoreReader([
        record({
          changeId: "01HIT",
          handle: "CH-01HIT",
          intent: "Refactor the auth flow",
          worktreePath: wtHit,
        }),
        record({
          changeId: "01MISS",
          handle: "CH-01MISS",
          intent: "Unrelated work",
          worktreePath: wtMiss,
        }),
      ]);
      // The query word lives ONLY in 01HIT's conversation — not in any
      // handle/intent/slug/stage. A title-only search would miss it.
      await seedTranscript(
        tmpProjects,
        wtHit,
        "we agreed on the marshmallow rollback approach",
      );
      await seedTranscript(tmpProjects, wtMiss, "nothing relevant here");

      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/search").query({ q: "marshmallow" });
      expect(res.status).toBe(200);
      const body = res.body as { results: Change[] };
      expect(Array.isArray(body.results)).toBe(true);
      expect(body.results.map((c) => c.changeId)).toEqual(["01HIT"]);
      // Same row shape as the board (stage + liveness present).
      expect(typeof body.results[0]?.stage).toBe("string");
      expect(typeof body.results[0]?.liveness.status).toBe("string");
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(wtHit, { recursive: true, force: true });
      await rm(wtMiss, { recursive: true, force: true });
    }
  });

  it("returns { results } with every change when no filters are given (the full board)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    try {
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01A", handle: "CH-01A" }),
        record({ changeId: "01B", handle: "CH-01B" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/search");
      expect(res.status).toBe(200);
      const body = res.body as { results: Change[] };
      expect(body.results.map((c) => c.changeId).sort()).toEqual(["01A", "01B"]);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
    }
  });

  it("filters to the requested stages with a repeated ?stage param → array (FR-11)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    try {
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01R", stage: "recon" }),
        record({ changeId: "01D", stage: "design" }),
        record({ changeId: "01S", stage: "ship" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      // supertest serialises an array value as repeated params: ?stage=design&stage=ship
      const res = await request(app)
        .get("/api/search")
        .query({ stage: ["design", "ship"] });
      expect(res.status).toBe(200);
      const body = res.body as { results: Change[] };
      expect(body.results.map((c) => c.changeId).sort()).toEqual(["01D", "01S"]);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
    }
  });

  it("accepts a single ?stage param as a one-element stage filter (FR-11)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    try {
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01R", stage: "recon" }),
        record({ changeId: "01D", stage: "design" }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app).get("/api/search").query({ stage: "design" });
      expect(res.status).toBe(200);
      const body = res.body as { results: Change[] };
      expect(body.results.map((c) => c.changeId)).toEqual(["01D"]);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
    }
  });

  it("filters to needs-attention only — keeps a blocked change, drops idle-but-fine (FR-12)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wtBlocked = await mkdtemp(join(tmpdir(), "wt-blk-"));
    const wtIdle = await mkdtemp(join(tmpdir(), "wt-idle-"));
    try {
      // A BLOCKER-*.md in the worktree's architecture tree → detectOpenBlocker
      // → the FR-12 `blocked` reason → needsAttention flagged. This proves the
      // route reuses WP-004's predicate (single source of truth).
      const wpDir = join(
        wtBlocked,
        ".architecture",
        "some-project",
        "work-packages",
      );
      await mkdir(wpDir, { recursive: true });
      await writeFile(join(wpDir, "BLOCKER-WP-001.md"), "# blocked\n", "utf8");

      const reader = new FakeChangeStoreReader([
        record({ changeId: "01BLK", handle: "CH-01BLK", worktreePath: wtBlocked }),
        record({ changeId: "01IDL", handle: "CH-01IDL", worktreePath: wtIdle }),
      ]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app)
        .get("/api/search")
        .query({ needsAttention: "true" });
      expect(res.status).toBe(200);
      const body = res.body as { results: Change[] };
      expect(body.results.map((c) => c.changeId)).toEqual(["01BLK"]);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(wtBlocked, { recursive: true, force: true });
      await rm(wtIdle, { recursive: true, force: true });
    }
  });

  it("composes content + stage filters (filters narrow the same set)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    const tmpProjects = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wtA = await mkdtemp(join(tmpdir(), "wt-a-"));
    const wtB = await mkdtemp(join(tmpdir(), "wt-b-"));
    try {
      const reader = new FakeChangeStoreReader([
        record({ changeId: "01A", stage: "design", worktreePath: wtA }),
        record({ changeId: "01B", stage: "recon", worktreePath: wtB }),
      ]);
      // Both conversations mention "rollback"; only 01A is in the design stage.
      await seedTranscript(tmpProjects, wtA, "the rollback plan is ready");
      await seedTranscript(tmpProjects, wtB, "the rollback plan is ready");
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: tmpProjects,
      });
      const res = await request(app)
        .get("/api/search")
        .query({ q: "rollback", stage: "design" });
      expect(res.status).toBe(200);
      const body = res.body as { results: Change[] };
      expect(body.results.map((c) => c.changeId)).toEqual(["01A"]);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
      await rm(tmpProjects, { recursive: true, force: true });
      await rm(wtA, { recursive: true, force: true });
      await rm(wtB, { recursive: true, force: true });
    }
  });

  it("rejects a POST to the search route (read-only; 405)", async () => {
    const tmpState = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    try {
      const reader = new FakeChangeStoreReader([record({ changeId: "01A" })]);
      const app = createApp({
        changeStore: reader,
        sulisStateDir: tmpState,
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).post("/api/search");
      expect(res.status).toBe(405);
    } finally {
      await rm(tmpState, { recursive: true, force: true });
    }
  });
});
