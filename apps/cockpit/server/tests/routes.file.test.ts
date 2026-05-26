// WP-010 — GET /api/changes/:id/file route tests.

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

describe("GET /api/changes/:id/file", () => {
  it("returns the file contents with a language hint", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    await mkdir(join(worktree, "src"));
    await writeFile(
      join(worktree, "src", "index.ts"),
      "export const x = 1;\n",
      "utf8",
    );
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01III", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app)
        .get("/api/changes/01III/file")
        .query({ path: "src/index.ts" });
      expect(res.status).toBe(200);
      const body = res.body as {
        path: string;
        content: string;
        language: string;
        binary: boolean;
        truncated: boolean;
      };
      expect(body.path).toBe("src/index.ts");
      expect(body.content).toBe("export const x = 1;\n");
      expect(body.language).toBe("typescript");
      expect(body.binary).toBe(false);
      expect(body.truncated).toBe(false);
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
    const res = await request(app)
      .get("/api/changes/missing/file")
      .query({ path: "x.ts" });
    expect(res.status).toBe(404);
    expect((res.body as { code: string }).code).toBe("NOT_FOUND");
  });

  it("returns 400 PATH_OUTSIDE_WORKTREE for an escape attempt", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01JJJ", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app)
        .get("/api/changes/01JJJ/file")
        .query({ path: "../../etc/passwd" });
      expect(res.status).toBe(400);
      expect((res.body as { code: string }).code).toBe("PATH_OUTSIDE_WORKTREE");
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 404 NOT_FOUND when the file does not exist", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01KKK", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app)
        .get("/api/changes/01KKK/file")
        .query({ path: "missing.ts" });
      expect(res.status).toBe(404);
      expect((res.body as { code: string }).code).toBe("NOT_FOUND");
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 400 IS_A_DIRECTORY when the path resolves to a directory", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    await mkdir(join(worktree, "subdir"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01LLL", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app)
        .get("/api/changes/01LLL/file")
        .query({ path: "subdir" });
      expect(res.status).toBe(400);
      expect((res.body as { code: string }).code).toBe("IS_A_DIRECTORY");
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });

  it("returns 400 when ?path= is missing", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01MMM", worktreePath: worktree }),
    ]);
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app).get("/api/changes/01MMM/file");
      expect(res.status).toBe(400);
    } finally {
      await rm(worktree, { recursive: true, force: true });
    }
  });
});
