// WP-010 — request-log middleware tests (TDD §13.8 logging hygiene).
//
// The middleware logs one line per request: method, path, status,
// duration. It MUST NOT log file contents, transcript contents, headers,
// or environment variables. The test pipes console.log, exercises the
// file endpoint with a uniquely-identifying string in the file contents,
// and then asserts:
//   1. A log line for the request was emitted.
//   2. The log line does NOT contain the unique string.
//   3. The log line includes status + duration.

import { describe, it, expect, vi } from "vitest";
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

describe("request-log middleware (TDD §13.8)", () => {
  it("logs status + duration but never includes file contents", async () => {
    const worktree = await mkdtemp(join(tmpdir(), "wt-"));
    await mkdir(join(worktree, "src"));
    const secretMarker = "VERY-UNIQUE-CONTENT-MARKER-d8f3a1";
    await writeFile(join(worktree, "src", "secret.ts"), secretMarker, "utf8");

    const reader = new FakeChangeStoreReader([
      record({ changeId: "01LOG", worktreePath: worktree }),
    ]);

    const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    try {
      const app = createApp({
        changeStore: reader,
        sulisStateDir: "/tmp/never",
        claudeProjectsDir: "/tmp/never",
      });
      const res = await request(app)
        .get("/api/changes/01LOG/file")
        .query({ path: "src/secret.ts" });
      expect(res.status).toBe(200);

      const lines = logSpy.mock.calls.map((c) => c.map(String).join(" "));
      const reqLog = lines.find(
        (l) => l.includes("GET") && l.includes("/api/changes/01LOG/file"),
      );
      expect(reqLog).toBeDefined();
      // The request log must NOT contain the file's contents.
      const all = lines.join("\n");
      expect(all).not.toContain(secretMarker);
      // Should record status code.
      expect(reqLog).toMatch(/200/);
      // Should record a duration (ms).
      expect(reqLog).toMatch(/\d+\s*ms/);
    } finally {
      logSpy.mockRestore();
      await rm(worktree, { recursive: true, force: true });
    }
  });
});
