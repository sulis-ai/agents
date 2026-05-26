// WP-010 — GET /api/changes/:id/diff route tests.
//
// Uses a real git repo (per MEA-09: no mocks for the git boundary).

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import request from "supertest";
import { mkdtemp, rm, writeFile, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

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

function git(cwd: string, args: string[]): string {
  const result = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed (status ${result.status}): ${result.stderr}`,
    );
  }
  return result.stdout.trim();
}

describe("GET /api/changes/:id/diff", () => {
  let repo: string;
  let baseSha: string;

  beforeAll(async () => {
    const base = await mkdtemp(join(tmpdir(), "diff-routes-"));
    repo = await realpath(base);
    git(repo, ["init", "-q", "-b", "main"]);
    git(repo, ["config", "user.email", "test@example.com"]);
    git(repo, ["config", "user.name", "WP-010 test"]);
    git(repo, ["config", "commit.gpgsign", "false"]);
    await writeFile(join(repo, "hello.txt"), "hello\n", "utf8");
    git(repo, ["add", "."]);
    git(repo, ["commit", "-q", "-m", "base"]);
    baseSha = git(repo, ["rev-parse", "HEAD"]);
    // Modify post-base.
    await writeFile(join(repo, "hello.txt"), "hello, world\n", "utf8");
  });

  afterAll(async () => {
    await rm(repo, { recursive: true, force: true });
  });

  it("returns base + current contents for a modified file", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01DIFF", worktreePath: repo, baseSha }),
    ]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });
    const res = await request(app)
      .get("/api/changes/01DIFF/diff")
      .query({ path: "hello.txt" });
    expect(res.status).toBe(200);
    const body = res.body as {
      base: string | null;
      current: string | null;
      binary: boolean;
      truncated: boolean;
    };
    expect(body.base).toBe("hello\n");
    expect(body.current).toBe("hello, world\n");
    expect(body.binary).toBe(false);
    expect(body.truncated).toBe(false);
  });

  it("returns 404 NOT_FOUND for an unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });
    const res = await request(app)
      .get("/api/changes/missing/diff")
      .query({ path: "x.ts" });
    expect(res.status).toBe(404);
    expect((res.body as { code: string }).code).toBe("NOT_FOUND");
  });

  it("returns 422 NO_BASE_SHA when the change has no baseSha", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01NOBASE", worktreePath: repo, baseSha: null }),
    ]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });
    const res = await request(app)
      .get("/api/changes/01NOBASE/diff")
      .query({ path: "hello.txt" });
    expect(res.status).toBe(422);
    const body = res.body as { error: string; code: string };
    expect(body.code).toBe("NO_BASE_SHA");
    expect(body.error.toLowerCase()).toContain("base_sha");
  });

  it("returns 400 PATH_OUTSIDE_WORKTREE for an escape attempt", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01ESC", worktreePath: repo, baseSha }),
    ]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });
    const res = await request(app)
      .get("/api/changes/01ESC/diff")
      .query({ path: "../../etc/passwd" });
    expect(res.status).toBe(400);
    expect((res.body as { code: string }).code).toBe("PATH_OUTSIDE_WORKTREE");
  });

  it("returns 504 TIMEOUT when the git subprocess exceeds its budget", async () => {
    // Use a tiny gitTimeoutMs so the subprocess is killed before it
    // returns. 1ms is small enough that even `git show` cannot finish.
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01TIMEOUT", worktreePath: repo, baseSha }),
    ]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
      gitTimeoutMs: 1,
    });
    const res = await request(app)
      .get("/api/changes/01TIMEOUT/diff")
      .query({ path: "hello.txt" });
    expect(res.status).toBe(504);
    expect((res.body as { code: string }).code).toBe("TIMEOUT");
  });

  it("returns 400 when ?path= is missing", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01NOPATH", worktreePath: repo, baseSha }),
    ]);
    const app = createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: "/tmp/never",
    });
    const res = await request(app).get("/api/changes/01NOPATH/diff");
    expect(res.status).toBe(400);
  });
});
