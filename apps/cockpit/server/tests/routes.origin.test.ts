// WP-P09 — GET /api/changes/:id/origin route tests (ADR-012).
//
// Drives the app through supertest (no real port bind) against a real ephemeral
// git repo worktree (no mocks at the git boundary — MEA-09) seeded with a brain
// run + a transcript, so the route composes the change-lookup (404 for unknown)
// with the InferredOriginAttribution adapter end-to-end.
//
//   - 200 + ChangeOriginView (every changed file's inferred origin) — change-level.
//   - 200 + OriginView for the `?path=<rel>` variant — file-level.
//   - every origin carries attribution:"inferred" (the honesty flag).
//   - 404 + { code: "NOT_FOUND" } for an unknown change id.
//   - 405 for a POST (read-only).

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import request from "supertest";
import {
  mkdtemp,
  mkdir,
  writeFile,
  rm,
  realpath,
} from "node:fs/promises";
import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import { mangleCwd } from "../lib/mangleCwd";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type {
  ChangeOriginView,
  OriginView,
} from "../../shared/api-types";

const RUN_AT = "2026-06-02T12:00:00Z";
const TURN_AT = "2026-06-03T09:00:00Z";
const RUN_ID = "01RUNAUTONOMOUS0000000000A";

function git(cwd: string, args: string[], env?: NodeJS.ProcessEnv): string {
  const result = spawnSync("git", args, {
    cwd,
    encoding: "utf8",
    env: { ...process.env, ...env },
  });
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed (status ${result.status}): ${result.stderr}`,
    );
  }
  return result.stdout.trim();
}

function commitFile(
  repo: string,
  path: string,
  content: string,
  isoDate: string,
  author: string,
): void {
  const m = /^(.*)<(.+)>\s*$/.exec(author);
  const name = (m?.[1] ?? "Tester").trim();
  const email = (m?.[2] ?? "t@example.com").trim();
  writeFileSync(join(repo, path), content, "utf8");
  git(repo, ["add", path]);
  git(repo, ["commit", "-q", "-m", `add ${path}`], {
    GIT_AUTHOR_DATE: isoDate,
    GIT_COMMITTER_DATE: isoDate,
    GIT_AUTHOR_NAME: name,
    GIT_AUTHOR_EMAIL: email,
    GIT_COMMITTER_NAME: name,
    GIT_COMMITTER_EMAIL: email,
  });
}

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/never-used",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

describe("GET /api/changes/:id/origin (ADR-012)", () => {
  let repo: string;
  let baseSha: string;
  let projectsDir: string;

  beforeAll(async () => {
    repo = await realpath(await mkdtemp(join(tmpdir(), "origin-route-")));
    git(repo, ["init", "-q", "-b", "main"]);
    git(repo, ["config", "commit.gpgsign", "false"]);

    // Base commit (the recorded baseSha) — readChangedFiles diffs base→worktree.
    writeFileSync(join(repo, "base.txt"), "base\n", "utf8");
    git(repo, ["add", "base.txt"]);
    git(repo, ["commit", "-q", "-m", "base"], {
      GIT_AUTHOR_DATE: "2026-06-01T00:00:00Z",
      GIT_COMMITTER_DATE: "2026-06-01T00:00:00Z",
    });
    baseSha = git(repo, ["rev-parse", "HEAD"]);

    // Changed files on top of base, each at a controlled date.
    commitFile(repo, "auto.txt", "auto\n", RUN_AT, "Sulis Bot <bot@sulis.ai>");
    commitFile(repo, "assist.txt", "assist\n", TURN_AT, "Iain <i@nivbow.com>");
    commitFile(repo, "stray.txt", "stray\n", "2020-01-01T00:00:00Z", "Iain <i@nivbow.com>");

    // Brain run at RUN_AT.
    const runDir = join(
      repo,
      ".brain",
      "instances",
      "product-development",
      "lifecyclerun",
    );
    await mkdir(runDir, { recursive: true });
    await writeFile(
      join(runDir, `${RUN_ID}.jsonld`),
      JSON.stringify({
        id: `dna:lifecyclerun:${RUN_ID}`,
        _run_id: RUN_ID,
        step_name: "implement",
        at: RUN_AT,
        outcome: "completed",
        confidence: 0.88,
        _workflow: "dna:workflow:WF1",
      }),
      "utf8",
    );

    // Transcript with a turn at TURN_AT.
    projectsDir = await mkdtemp(join(tmpdir(), "origin-route-projects-"));
    const sessionDir = join(projectsDir, mangleCwd(repo));
    await mkdir(sessionDir, { recursive: true });
    const lines = [
      JSON.stringify({
        type: "user",
        uuid: "u0",
        timestamp: "2026-06-03T08:59:00Z",
        cwd: repo,
        message: { role: "user", content: "make the assisted change" },
      }),
      JSON.stringify({
        type: "assistant",
        uuid: "a1",
        timestamp: TURN_AT,
        cwd: repo,
        message: {
          role: "assistant",
          content: [{ type: "text", text: "Done — assisted change made." }],
        },
      }),
    ];
    await writeFile(
      join(sessionDir, "session-abc.jsonl"),
      `${lines.join("\n")}\n`,
      "utf8",
    );
  });

  afterAll(async () => {
    await rm(repo, { recursive: true, force: true });
    await rm(projectsDir, { recursive: true, force: true });
  });

  function app(reader: FakeChangeStoreReader) {
    return createApp({
      changeStore: reader,
      sulisStateDir: "/tmp/never",
      claudeProjectsDir: projectsDir,
    });
  }

  it("returns 200 + a per-file ChangeOriginView classifying each file", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: repo, baseSha }),
    ]);
    const res = await request(app(reader)).get("/api/changes/01XYZ/origin");
    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/application\/json/);
    const body = res.body as ChangeOriginView;
    expect(body.changeId).toBe("01XYZ");

    const byPath = new Map(body.files.map((f) => [f.path, f.origin]));
    expect(byPath.get("auto.txt")?.kind).toBe("autonomous");
    expect(byPath.get("assist.txt")?.kind).toBe("assisted");
    expect(byPath.get("stray.txt")?.kind).toBe("unknown");

    // Every origin carries the honest inferred flag.
    for (const f of body.files) {
      expect(f.origin.attribution).toBe("inferred");
    }
  });

  it("returns 200 + an OriginView for the ?path= variant", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: repo, baseSha }),
    ]);
    const res = await request(app(reader)).get(
      "/api/changes/01XYZ/origin?path=auto.txt",
    );
    expect(res.status).toBe(200);
    const body = res.body as OriginView;
    expect(body.changeId).toBe("01XYZ");
    expect(body.path).toBe("auto.txt");
    expect(body.origin.kind).toBe("autonomous");
    expect(body.origin.attribution).toBe("inferred");
    if (body.origin.kind === "autonomous") {
      expect(body.origin.confidence).toBe(0.88);
    }
  });

  it("returns an empty file list for a legacy change with no baseSha", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01LEGACY", worktreePath: repo, baseSha: null }),
    ]);
    const res = await request(app(reader)).get("/api/changes/01LEGACY/origin");
    expect(res.status).toBe(200);
    const body = res.body as ChangeOriginView;
    expect(body.files).toEqual([]);
  });

  it("returns 404 + NOT_FOUND for an unknown change id", async () => {
    const reader = new FakeChangeStoreReader([]);
    const res = await request(app(reader)).get(
      "/api/changes/does-not-exist/origin",
    );
    expect(res.status).toBe(404);
    const body = res.body as { error: string; code: string };
    expect(body.code).toBe("NOT_FOUND");
    expect(body.error.length).toBeGreaterThan(0);
  });

  it("rejects a POST to the origin route (read-only; 405)", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01XYZ", worktreePath: repo, baseSha }),
    ]);
    const res = await request(app(reader)).post("/api/changes/01XYZ/origin");
    expect(res.status).toBe(405);
  });
});
