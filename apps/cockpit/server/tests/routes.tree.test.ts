// WP-010 — GET /api/changes/:id/tree route tests.

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

describe("GET /api/changes/:id/tree", () => {
  it("returns the worktree root, directories first then files, hiding node_modules", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    await mkdir(join(worktree, "src"));
    await writeFile(join(worktree, "src", "index.ts"), "x", "utf8");
    await writeFile(join(worktree, "README.md"), "readme", "utf8");
    await mkdir(join(worktree, "node_modules"));
    await writeFile(join(worktree, "node_modules", "skip.js"), "", "utf8");

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01DDD", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/changes/01DDD/tree");
      expect(res.status).toBe(200);
      const body = res.body as Array<{ name: string; kind: string }>;
      const names = body.map((n) => n.name);
      expect(names).toContain("src");
      expect(names).toContain("README.md");
      expect(names).not.toContain("node_modules");
      // Directory first then file (TDD §5 ordering).
      const srcIdx = names.indexOf("src");
      const readmeIdx = names.indexOf("README.md");
      expect(srcIdx).toBeLessThan(readmeIdx);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("honours ?path= to list a subdirectory", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    await mkdir(join(worktree, "src"));
    await writeFile(join(worktree, "src", "a.ts"), "", "utf8");
    await writeFile(join(worktree, "src", "b.ts"), "", "utf8");

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01EEE", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/changes/01EEE/tree?path=src");
      expect(res.status).toBe(200);
      const body = res.body as Array<{ name: string }>;
      expect(body.map((n) => n.name).sort()).toEqual(["a.ts", "b.ts"]);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 404 NOT_FOUND for an unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });
    const res = await request(app).get("/api/changes/missing/tree");
    expect(res.status).toBe(404);
    expect((res.body as { code: string }).code).toBe("NOT_FOUND");
  });

  it("returns 400 PATH_OUTSIDE_WORKTREE when path tries to escape", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01FFF", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app)
        .get("/api/changes/01FFF/tree")
        .query({ path: "../../etc/passwd" });
      expect(res.status).toBe(400);
      expect((res.body as { code: string }).code).toBe("PATH_OUTSIDE_WORKTREE");
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 404 NOT_FOUND when path does not exist inside the worktree", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01GGG", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app)
        .get("/api/changes/01GGG/tree")
        .query({ path: "missing-dir" });
      expect(res.status).toBe(404);
      expect((res.body as { code: string }).code).toBe("NOT_FOUND");
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 400 NOT_A_DIRECTORY when path points to a file", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    await writeFile(join(worktree, "file.txt"), "x", "utf8");
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01HHH", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app)
        .get("/api/changes/01HHH/tree")
        .query({ path: "file.txt" });
      expect(res.status).toBe(400);
      expect((res.body as { code: string }).code).toBe("NOT_A_DIRECTORY");
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });
});
