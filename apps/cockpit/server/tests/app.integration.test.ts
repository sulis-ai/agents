// WP-010 — end-to-end integration smoke (TDD §14.6).
//
// Seeds:
//   - A temp SULIS_STATE_DIR with one fixture change record + state.json.
//   - A temp worktree at the change's worktree_path with src/index.ts +
//     README.md + node_modules/skip-me/ (which the tree reader must hide).
//   - A temp Claude projects dir with a JSONL transcript containing a
//     user + assistant + system record.
//   - A real git repo init'd inside the worktree with a base commit so
//     `git show <base_sha>:<path>` is reachable.
//
// Then drives each endpoint through supertest IN-PROCESS (no real socket
// bind) and asserts the wire-shape contracts.
//
// WP-016 note — combined-run stability:
//   This suite previously called `app.listen(0, "127.0.0.1")` and hit the
//   ephemeral port with `fetch`. That was the ONLY server test binding a
//   real socket. Under the combined `npx vitest run` (server node-env +
//   client jsdom/Monaco env in parallel) the real socket intermittently
//   produced "socket hang up" on the transcript route under load. Switching
//   to in-process `supertest(app)` (the pattern every routes.*.test.ts
//   already uses) removes the socket entirely and makes the combined run
//   deterministic. The bind-address invariant (127.0.0.1, never 0.0.0.0)
//   is fully covered by bind-address.test.ts, so no coverage is lost.

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, rm, writeFile, mkdir, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import request from "supertest";
import type { Application } from "express";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import { mangleCwd } from "../lib/mangleCwd";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

function git(cwd: string, args: string[]): string {
  const result = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed (status ${result.status}): ${result.stderr}`,
    );
  }
  return result.stdout.trim();
}

describe("end-to-end integration smoke (TDD §14.6)", () => {
  let stateDir: string;
  let projectsDir: string;
  let worktree: string;
  let baseSha: string;
  let app: Application;
  const changeId = "01SMOKE";

  beforeAll(async () => {
    stateDir = await mkdtemp(join(tmpdir(), "cockpit-state-"));
    projectsDir = await mkdtemp(join(tmpdir(), "claude-projects-"));
    const wtBase = await mkdtemp(join(tmpdir(), "cockpit-wt-"));
    worktree = await realpath(wtBase);

    // Seed the worktree with a tiny tree + a git repo so diff works.
    await mkdir(join(worktree, "src"));
    await writeFile(
      join(worktree, "src", "index.ts"),
      "export const x = 1;\n",
      "utf8",
    );
    await writeFile(join(worktree, "README.md"), "# demo\n", "utf8");
    // WP-003 — rendered contract artifacts + shared manifest, so the
    // contract endpoints are reachable end-to-end.
    await writeFile(
      join(worktree, "CONTRACT.html"),
      "<!doctype html><title>Contract</title><h1>What it does</h1>",
      "utf8",
    );
    await writeFile(
      join(worktree, "CONTRACT.manifest.json"),
      JSON.stringify({
        data_contract: { format: "servicespec", name: "Smoke", contracts: [] },
        contract_html: join(worktree, "CONTRACT.html"),
        ui_contract: "none",
        note: "No UI contract for this change.",
      }),
      "utf8",
    );
    await mkdir(join(worktree, "node_modules", "skip-me"), { recursive: true });
    await writeFile(
      join(worktree, "node_modules", "skip-me", "x.js"),
      "",
      "utf8",
    );

    git(worktree, ["init", "-q", "-b", "main"]);
    git(worktree, ["config", "user.email", "test@example.com"]);
    git(worktree, ["config", "user.name", "WP-010 smoke"]);
    git(worktree, ["config", "commit.gpgsign", "false"]);
    git(worktree, ["add", "."]);
    git(worktree, ["commit", "-q", "-m", "base"]);
    baseSha = git(worktree, ["rev-parse", "HEAD"]);

    // Modify the worktree post-base so the diff has something to show.
    await writeFile(
      join(worktree, "src", "index.ts"),
      "export const x = 2;\n",
      "utf8",
    );

    // Seed a transcript that targets this worktree.
    const projDir = join(projectsDir, mangleCwd(worktree));
    await mkdir(projDir, { recursive: true });
    const transcriptLines =
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
        JSON.stringify({
          type: "system",
          uuid: "s1",
          timestamp: "2026-05-26T00:00:02Z",
          cwd: worktree,
          subtype: "ack",
          content: "ok",
        }),
      ].join("\n") + "\n";
    await writeFile(
      join(projDir, "smoke-session.jsonl"),
      transcriptLines,
      "utf8",
    );

    const record: ChangeStoreRecord = {
      changeId,
      handle: "CH-01SMOKE",
      slug: "smoke",
      primitive: "create",
      branch: "change/smoke",
      worktreePath: worktree,
      intent: "smoke",
      baseBranch: "main",
      baseSha,
      createdAt: "2026-05-26T00:00:00Z",
      updatedAt: "2026-05-26T00:00:00Z",
      stage: "implement",
    };
    const reader = new FakeChangeStoreReader([record]);

    app = createApp({
      changeStore: reader,
      sulisStateDir: stateDir,
      claudeProjectsDir: projectsDir,
    });
  }, 30_000);

  afterAll(async () => {
    await rm(stateDir, { recursive: true, force: true });
    await rm(projectsDir, { recursive: true, force: true });
    await rm(worktree, { recursive: true, force: true });
  });

  it("GET /api/changes returns one change with liveness", async () => {
    const res = await request(app).get("/api/changes");
    expect(res.status).toBe(200);
    const body = res.body as Array<{
      changeId: string;
      liveness: { status: string };
    }>;
    expect(body).toHaveLength(1);
    expect(body[0]?.changeId).toBe(changeId);
    expect(["running", "not-running", "unknown"]).toContain(
      body[0]?.liveness.status,
    );
  });

  it("GET /api/changes/:id returns the detail + transcriptPaths", async () => {
    const res = await request(app).get(`/api/changes/${changeId}`);
    expect(res.status).toBe(200);
    const body = res.body as {
      changeId: string;
      transcriptPaths: string[];
    };
    expect(body.changeId).toBe(changeId);
    expect(body.transcriptPaths.length).toBeGreaterThanOrEqual(1);
    expect(body.transcriptPaths[0]).toMatch(/\.jsonl$/);
  });

  it("GET /api/changes/:id/tree returns the worktree root without node_modules", async () => {
    const res = await request(app).get(`/api/changes/${changeId}/tree`);
    expect(res.status).toBe(200);
    const body = res.body as Array<{ name: string; kind: string }>;
    const names = body.map((n) => n.name);
    expect(names).toContain("src");
    expect(names).toContain("README.md");
    expect(names).not.toContain("node_modules");
  });

  it("GET /api/changes/:id/file returns the file with a language hint", async () => {
    const res = await request(app)
      .get(`/api/changes/${changeId}/file`)
      .query({ path: "src/index.ts" });
    expect(res.status).toBe(200);
    const body = res.body as {
      content: string;
      language: string;
      binary: boolean;
    };
    expect(body.content).toBe("export const x = 2;\n");
    expect(body.language).toBe("typescript");
    expect(body.binary).toBe(false);
  });

  it("GET /api/changes/:id/diff returns base + current", async () => {
    const res = await request(app)
      .get(`/api/changes/${changeId}/diff`)
      .query({ path: "src/index.ts" });
    expect(res.status).toBe(200);
    const body = res.body as {
      base: string | null;
      current: string | null;
    };
    expect(body.base).toBe("export const x = 1;\n");
    expect(body.current).toBe("export const x = 2;\n");
  });

  it("GET /api/changes/:id/transcript returns the projected messages", async () => {
    const res = await request(app).get(`/api/changes/${changeId}/transcript`);
    expect(res.status).toBe(200);
    const body = res.body as Array<{
      kind: string;
      timestamp: string;
    }>;
    expect(body.length).toBeGreaterThanOrEqual(3);
    // Sorted by timestamp ascending.
    const kinds = body.map((m) => m.kind);
    expect(kinds[0]).toBe("user");
    expect(kinds[1]).toBe("assistant");
    expect(kinds[2]).toBe("system");
  });

  it("returns a JSON error envelope for an unknown change id", async () => {
    const res = await request(app).get("/api/changes/does-not-exist");
    expect(res.status).toBe(404);
    const body = res.body as { error: string; code: string };
    expect(body.code).toBe("NOT_FOUND");
    expect(typeof body.error).toBe("string");
  });

  it("rejects non-GET methods with 405", async () => {
    const res = await request(app).post("/api/changes");
    expect(res.status).toBe(405);
  });

  it("GET /api/changes/:id/contract is mounted + reachable (summary)", async () => {
    const res = await request(app).get(`/api/changes/${changeId}/contract`);
    expect(res.status).toBe(200);
    const body = res.body as {
      status: string;
      dataContract: { name: string } | null;
      uiContract: { status: string };
    };
    expect(body.status).toBe("ready");
    expect(body.dataContract?.name).toBe("Smoke");
    // This change has no UI contract → a note, not a broken link.
    expect(body.uiContract.status).toBe("none");
  });

  it("GET /api/changes/:id/contract/data serves the rendered CONTRACT.html", async () => {
    const res = await request(app).get(
      `/api/changes/${changeId}/contract/data`,
    );
    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/html/);
    expect(res.text).toContain("What it does");
  });
});
