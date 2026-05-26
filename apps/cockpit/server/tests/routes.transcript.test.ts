// WP-010 — GET /api/changes/:id/transcript route tests.

import { describe, it, expect } from "vitest";
import request from "supertest";
import { mkdtemp, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import { mangleCwd } from "../lib/mangleCwd";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/wt-default",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
    stage: "specify",
    ...overrides,
  };
}

describe("GET /api/changes/:id/transcript", () => {
  it("returns the chronologically-merged messages", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    const projects = await mkdtemp(join(tmpdir(), "proj-"));
    const mangled = mangleCwd(worktree);
    const projDir = join(projects, mangled);
    await mkdir(projDir, { recursive: true });
    const transcriptPath = join(projDir, "session-001.jsonl");
    const lines =
      [
        JSON.stringify({
          type: "user",
          uuid: "u1",
          timestamp: "2026-05-26T00:00:00Z",
          cwd: worktree,
          message: { role: "user", content: "hello" },
        }),
        JSON.stringify({
          type: "assistant",
          uuid: "a1",
          timestamp: "2026-05-26T00:00:01Z",
          cwd: worktree,
          message: {
            role: "assistant",
            content: [{ type: "text", text: "hi" }],
          },
        }),
      ].join("\n") + "\n";
    await writeFile(transcriptPath, lines, "utf8");

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01TRANS", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: projects,
      });
      const res = await request(app).get("/api/changes/01TRANS/transcript");
      expect(res.status).toBe(200);
      const body = res.body as Array<{ kind: string; timestamp: string }>;
      expect(body).toHaveLength(2);
      expect(body[0]?.kind).toBe("user");
      expect(body[1]?.kind).toBe("assistant");
    } finally {
      await rm(worktree, { recursive: true, force: true });
      await rm(projects, { recursive: true, force: true });
    }
  });

  it("returns an empty array when no transcripts exist for the change", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    const projects = await mkdtemp(join(tmpdir(), "proj-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01NONE", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: projects,
      });
      const res = await request(app).get("/api/changes/01NONE/transcript");
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    } finally {
      await rm(worktree, { recursive: true, force: true });
      await rm(projects, { recursive: true, force: true });
    }
  });

  it("returns 404 NOT_FOUND for an unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });
    const res = await request(app).get("/api/changes/missing/transcript");
    expect(res.status).toBe(404);
    expect((res.body as { code: string }).code).toBe("NOT_FOUND");
  });
});
