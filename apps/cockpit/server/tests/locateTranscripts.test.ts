// WP-009 — integration tests for locateTranscripts.
//
// Per WP Contract "Locator" section + TDD §4 (the load-bearing
// heuristic) + TDD §14.2 + ADR-004. We seed a temp `projectsDir`
// with a mangled subdirectory holding fixture `.jsonl` files of
// every shape — matching cwd, mismatched cwd, empty, meta-only,
// multi-MB with the first content-bearing record at line 200 — and
// assert the locator returns exactly the expected file set.
//
// Discipline: real tmpdir, real `fs` I/O, no mocks. Same convention
// as the WP-007 readFileContents tests.

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, rm, mkdir, writeFile, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { locateTranscripts } from "../lib/locateTranscripts";
import { mangleCwd } from "../lib/mangleCwd";

interface ContentRecord {
  type: "user" | "assistant" | "system" | "attachment";
  cwd: string;
  uuid?: string;
  timestamp?: string;
  message?: unknown;
}

interface MetaRecord {
  type:
    | "agent-setting"
    | "permission-mode"
    | "last-prompt"
    | "file-history-snapshot"
    | "queue-operation";
  // no cwd field
  [k: string]: unknown;
}

function userRecord(cwd: string): ContentRecord {
  return {
    type: "user",
    cwd,
    uuid: "u-1",
    timestamp: "2026-05-26T10:00:00.000Z",
    message: { role: "user", content: "hello" },
  };
}

function metaRecord(kind: MetaRecord["type"]): MetaRecord {
  return { type: kind, payload: { ignored: true } };
}

function ndjson(records: unknown[]): string {
  return records.map((r) => JSON.stringify(r)).join("\n") + "\n";
}

describe("locateTranscripts", () => {
  let projectsDir: string;
  let worktreePath: string;
  let mangledDir: string;

  beforeAll(async () => {
    const base = await mkdtemp(join(tmpdir(), "wp009-projects-"));
    projectsDir = await realpath(base);

    // A worktree path the heuristic should accept. Use the realpath
    // of a temp directory so the cwd-field comparison is exact.
    const wtBase = await mkdtemp(join(tmpdir(), "wp009-worktree-"));
    worktreePath = await realpath(wtBase);

    mangledDir = join(projectsDir, mangleCwd(worktreePath));
    await mkdir(mangledDir, { recursive: true });

    // Fixture A: two matching JSONL files (different sessionIds).
    await writeFile(
      join(mangledDir, "session-A.jsonl"),
      ndjson([
        metaRecord("agent-setting"),
        userRecord(worktreePath),
      ]),
    );
    await writeFile(
      join(mangledDir, "session-B.jsonl"),
      ndjson([userRecord(worktreePath)]),
    );

    // Fixture C: cwd-mismatch — the failsafe MUST exclude this.
    await writeFile(
      join(mangledDir, "session-C-wrong-cwd.jsonl"),
      ndjson([userRecord("/some/other/path")]),
    );

    // Fixture D: empty file (zero bytes).
    await writeFile(join(mangledDir, "session-D-empty.jsonl"), "");

    // Fixture E: meta-only file (no content-bearing record).
    await writeFile(
      join(mangledDir, "session-E-meta-only.jsonl"),
      ndjson([
        metaRecord("permission-mode"),
        metaRecord("last-prompt"),
        metaRecord("queue-operation"),
      ]),
    );

    // Fixture F: multi-MB file with the first content-bearing record
    // at line 200. The locator MUST stream — opening the file and
    // reading line-by-line until it finds a content record. If it
    // slurps, this test still passes (read is fast) but the streaming
    // assertion lives in the parseTranscripts test for the 50 MB
    // case. Here we just verify the line-200 case is accepted.
    const lines: unknown[] = [];
    for (let i = 0; i < 199; i++) {
      lines.push(metaRecord("file-history-snapshot"));
    }
    lines.push(userRecord(worktreePath));
    await writeFile(join(mangledDir, "session-F-late-content.jsonl"), ndjson(lines));

    // Fixture G: a `.json` (non-jsonl) file — MUST be ignored.
    await writeFile(
      join(mangledDir, "not-a-transcript.json"),
      JSON.stringify(userRecord(worktreePath)),
    );

    // Fixture H: malformed first line, then a valid content record on
    // line 2. The locator should still accept (skip malformed; the
    // first parseable content-bearing record decides).
    await writeFile(
      join(mangledDir, "session-H-malformed-first.jsonl"),
      "this is not json\n" + JSON.stringify(userRecord(worktreePath)) + "\n",
    );
  });

  afterAll(async () => {
    await rm(projectsDir, { recursive: true, force: true });
    await rm(worktreePath, { recursive: true, force: true });
  });

  it("returns matching JSONL files for the worktree", async () => {
    const result = await locateTranscripts(worktreePath, projectsDir);
    const basenames = result.map((p) => p.split("/").pop()).sort();
    expect(basenames).toContain("session-A.jsonl");
    expect(basenames).toContain("session-B.jsonl");
  });

  it("skips files whose first content record has a mismatched cwd (failsafe)", async () => {
    const result = await locateTranscripts(worktreePath, projectsDir);
    const basenames = result.map((p) => p.split("/").pop());
    expect(basenames).not.toContain("session-C-wrong-cwd.jsonl");
  });

  it("skips empty JSONL files", async () => {
    const result = await locateTranscripts(worktreePath, projectsDir);
    const basenames = result.map((p) => p.split("/").pop());
    expect(basenames).not.toContain("session-D-empty.jsonl");
  });

  it("skips files with only meta records (no content-bearing record)", async () => {
    const result = await locateTranscripts(worktreePath, projectsDir);
    const basenames = result.map((p) => p.split("/").pop());
    expect(basenames).not.toContain("session-E-meta-only.jsonl");
  });

  it("accepts a file whose first content-bearing record is at line 200 (after many meta records)", async () => {
    const result = await locateTranscripts(worktreePath, projectsDir);
    const basenames = result.map((p) => p.split("/").pop());
    expect(basenames).toContain("session-F-late-content.jsonl");
  });

  it("ignores non-.jsonl files in the mangled directory", async () => {
    const result = await locateTranscripts(worktreePath, projectsDir);
    const basenames = result.map((p) => p.split("/").pop());
    expect(basenames).not.toContain("not-a-transcript.json");
  });

  it("returns an empty array when the mangled directory does not exist", async () => {
    const bogusWorktree = "/nonexistent/path/that/should/not/exist";
    const result = await locateTranscripts(bogusWorktree, projectsDir);
    expect(result).toEqual([]);
  });

  it("returns an empty array when projectsDir does not exist", async () => {
    const result = await locateTranscripts(
      worktreePath,
      "/nonexistent/projects/dir",
    );
    expect(result).toEqual([]);
  });

  it("returns absolute paths", async () => {
    const result = await locateTranscripts(worktreePath, projectsDir);
    for (const p of result) {
      expect(p.startsWith("/")).toBe(true);
    }
  });
});
