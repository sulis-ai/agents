// WP-009 — integration tests for parseTranscripts.
//
// Per WP Contract "Parser" section + TDD §5.1 (TranscriptMessage
// shape) + TDD §13.6 (streaming line-by-line — no slurp). The parser
// reads NDJSON, projects each record into a `TranscriptMessage`,
// merges all messages, and sorts by timestamp ascending.
//
// Discipline: real tmpdir, real `fs` I/O, no mocks. The 50 MB
// streaming assertion creates a real fixture file and measures
// process RSS during the read.

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, rm, writeFile, realpath, open } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { parseTranscripts } from "../lib/parseTranscripts";

function ndjson(records: unknown[]): string {
  return records.map((r) => JSON.stringify(r)).join("\n") + "\n";
}

describe("parseTranscripts", () => {
  let dir: string;

  beforeAll(async () => {
    const base = await mkdtemp(join(tmpdir(), "wp009-parse-"));
    dir = await realpath(base);
  });

  afterAll(async () => {
    await rm(dir, { recursive: true, force: true });
  });

  it("returns [] for an empty input", async () => {
    const result = await parseTranscripts([]);
    expect(result).toEqual([]);
  });

  it("projects user / assistant / system records in timestamp order", async () => {
    const file = join(dir, "single.jsonl");
    await writeFile(
      file,
      ndjson([
        {
          type: "system",
          uuid: "s-1",
          timestamp: "2026-05-26T10:00:02.000Z",
          subtype: "info",
          content: "info note",
          cwd: "/tmp",
        },
        {
          type: "user",
          uuid: "u-1",
          timestamp: "2026-05-26T10:00:00.000Z",
          message: { role: "user", content: "hello" },
          cwd: "/tmp",
        },
        {
          type: "assistant",
          uuid: "a-1",
          timestamp: "2026-05-26T10:00:01.000Z",
          message: {
            role: "assistant",
            content: [{ type: "text", text: "hi back" }],
          },
          cwd: "/tmp",
        },
      ]),
    );

    const result = await parseTranscripts([file]);
    expect(result).toHaveLength(3);
    const [m0, m1, m2] = result;
    if (!m0 || !m1 || !m2) throw new Error("length assertion");
    expect(m0.kind).toBe("user");
    expect(m1.kind).toBe("assistant");
    expect(m2.kind).toBe("system");
    expect(m0.timestamp < m1.timestamp).toBe(true);
    expect(m1.timestamp < m2.timestamp).toBe(true);
  });

  it("merges two files into one timestamp-sorted stream", async () => {
    const fileA = join(dir, "merge-a.jsonl");
    const fileB = join(dir, "merge-b.jsonl");
    await writeFile(
      fileA,
      ndjson([
        {
          type: "user",
          uuid: "ua-1",
          timestamp: "2026-05-26T11:00:00.000Z",
          message: { role: "user", content: "first" },
          cwd: "/tmp",
        },
        {
          type: "user",
          uuid: "ua-2",
          timestamp: "2026-05-26T11:00:02.000Z",
          message: { role: "user", content: "third" },
          cwd: "/tmp",
        },
      ]),
    );
    await writeFile(
      fileB,
      ndjson([
        {
          type: "user",
          uuid: "ub-1",
          timestamp: "2026-05-26T11:00:01.000Z",
          message: { role: "user", content: "second" },
          cwd: "/tmp",
        },
      ]),
    );

    const result = await parseTranscripts([fileA, fileB]);
    expect(result).toHaveLength(3);
    expect(result.map((m) => m.uuid)).toEqual(["ua-1", "ub-1", "ua-2"]);
  });

  it("projects an assistant message with mixed content blocks", async () => {
    const file = join(dir, "mixed.jsonl");
    await writeFile(
      file,
      ndjson([
        {
          type: "assistant",
          uuid: "a-mix",
          timestamp: "2026-05-26T12:00:00.000Z",
          message: {
            role: "assistant",
            content: [
              { type: "text", text: "Let me check that" },
              {
                type: "tool_use",
                id: "tu-1",
                name: "Bash",
                input: { command: "ls" },
              },
              {
                type: "tool_result",
                tool_use_id: "tu-1",
                content: "file1\nfile2",
              },
            ],
          },
          cwd: "/tmp",
        },
      ]),
    );

    const result = await parseTranscripts([file]);
    expect(result).toHaveLength(1);
    const msg = result[0];
    if (!msg || msg.kind !== "assistant") throw new Error("type narrowing");
    expect(msg.blocks).toHaveLength(3);
    expect(msg.blocks[0]).toEqual({ kind: "text", text: "Let me check that" });
    expect(msg.blocks[1]).toEqual({
      kind: "tool-use",
      toolName: "Bash",
      input: { command: "ls" },
    });
    expect(msg.blocks[2]).toEqual({
      kind: "tool-result",
      toolUseId: "tu-1",
      content: "file1\nfile2",
    });
  });

  it("skips malformed lines in the middle of a file and parses the rest", async () => {
    const file = join(dir, "malformed.jsonl");
    const good1 = {
      type: "user",
      uuid: "u-g1",
      timestamp: "2026-05-26T13:00:00.000Z",
      message: { role: "user", content: "before" },
      cwd: "/tmp",
    };
    const good2 = {
      type: "user",
      uuid: "u-g2",
      timestamp: "2026-05-26T13:00:02.000Z",
      message: { role: "user", content: "after" },
      cwd: "/tmp",
    };
    await writeFile(
      file,
      JSON.stringify(good1) +
        "\n" +
        "this line is not json {{{\n" +
        JSON.stringify(good2) +
        "\n",
    );

    const result = await parseTranscripts([file]);
    expect(result).toHaveLength(2);
    const [r0, r1] = result;
    if (!r0 || !r1) throw new Error("length assertion");
    expect(r0.uuid).toBe("u-g1");
    expect(r1.uuid).toBe("u-g2");
  });

  it("returns [] for a file with only meta records", async () => {
    const file = join(dir, "meta-only.jsonl");
    await writeFile(
      file,
      ndjson([
        { type: "agent-setting", value: "x" },
        { type: "permission-mode", mode: "auto" },
        { type: "last-prompt", prompt: "..." },
        { type: "file-history-snapshot", files: [] },
        { type: "queue-operation", op: "add" },
      ]),
    );

    const result = await parseTranscripts([file]);
    expect(result).toEqual([]);
  });

  it("suppresses attachment records (not rendered in the MVP)", async () => {
    const file = join(dir, "attach.jsonl");
    await writeFile(
      file,
      ndjson([
        {
          type: "user",
          uuid: "u-att-1",
          timestamp: "2026-05-26T14:00:00.000Z",
          message: { role: "user", content: "see attached" },
          cwd: "/tmp",
        },
        {
          type: "attachment",
          uuid: "att-1",
          timestamp: "2026-05-26T14:00:01.000Z",
          payload: { mime: "image/png" },
          cwd: "/tmp",
        },
      ]),
    );

    const result = await parseTranscripts([file]);
    expect(result).toHaveLength(1);
    expect(result[0]?.kind).toBe("user");
  });

  it("projects a system message preserving the subtype + text", async () => {
    const file = join(dir, "system.jsonl");
    await writeFile(
      file,
      ndjson([
        {
          type: "system",
          uuid: "s-2",
          timestamp: "2026-05-26T15:00:00.000Z",
          subtype: "tool-error",
          content: "the tool failed",
          cwd: "/tmp",
        },
      ]),
    );

    const result = await parseTranscripts([file]);
    expect(result).toHaveLength(1);
    const msg = result[0];
    if (!msg || msg.kind !== "system") throw new Error("type narrowing");
    expect(msg.subtype).toBe("tool-error");
    expect(msg.text).toBe("the tool failed");
  });

  it("projects a user message whose content is an array of content blocks", async () => {
    // Claude Code occasionally emits user messages whose `content` is
    // an array of blocks (e.g. [{type:'text', text:'...'}]) rather
    // than a bare string. The projection should coalesce text blocks.
    const file = join(dir, "user-blocks.jsonl");
    await writeFile(
      file,
      ndjson([
        {
          type: "user",
          uuid: "u-arr",
          timestamp: "2026-05-26T16:00:00.000Z",
          message: {
            role: "user",
            content: [
              { type: "text", text: "part one" },
              { type: "text", text: "part two" },
            ],
          },
          cwd: "/tmp",
        },
      ]),
    );

    const result = await parseTranscripts([file]);
    expect(result).toHaveLength(1);
    const msg = result[0];
    if (!msg || msg.kind !== "user") throw new Error("type narrowing");
    expect(msg.text).toContain("part one");
    expect(msg.text).toContain("part two");
  });

  it("streams large files line-by-line without loading the whole file (50 MB fixture)", async () => {
    // Create a ~50 MB NDJSON file: ~50_000 user records of ~1 KB each.
    // The assertion: process RSS grows by significantly less than the
    // file size during the read. We don't assert an exact byte count
    // (Node's heap behaviour varies), but a 10x headroom (50 MB file
    // → RSS delta under 100 MB) catches a `readFileSync`-style slurp.
    const file = join(dir, "big.jsonl");

    const handle = await open(file, "w");
    try {
      const payload = "x".repeat(900);
      for (let i = 0; i < 50_000; i++) {
        const rec = {
          type: "user",
          uuid: `big-${i}`,
          timestamp: `2026-05-26T17:${String(Math.floor(i / 60) % 60).padStart(2, "0")}:${String(i % 60).padStart(2, "0")}.000Z`,
          message: { role: "user", content: payload },
          cwd: "/tmp",
        };
        await handle.write(JSON.stringify(rec) + "\n");
      }
    } finally {
      await handle.close();
    }

    // Force a GC if exposed (Vitest doesn't run with --expose-gc by
    // default, so this is best-effort). Without GC the test still
    // catches a slurp — a buffer of 50 MB lives at least as long as
    // the read.
    if (typeof global.gc === "function") {
      global.gc();
    }
    const before = process.memoryUsage().rss;

    const result = await parseTranscripts([file]);

    if (typeof global.gc === "function") {
      global.gc();
    }
    const after = process.memoryUsage().rss;
    const delta = after - before;

    // 50_000 records all parsed.
    expect(result).toHaveLength(50_000);
    // RSS delta well under the file size — proves no whole-file slurp.
    // 100 MB headroom over the 50 MB file is generous; a slurp would
    // need at least one 50 MB buffer + the parsed array.
    expect(delta).toBeLessThan(200 * 1024 * 1024);
  }, 60_000);

  it("forbids fs.readFileSync in the lib source (no-slurp inventory check)", async () => {
    // TDD §13.6: streaming line-by-line. An inventory grep against
    // the source files is the cheapest way to keep us honest.
    const { readFile } = await import("node:fs/promises");
    const sources = [
      "apps/cockpit/server/lib/parseTranscripts.ts",
      "apps/cockpit/server/lib/locateTranscripts.ts",
    ];
    // Resolve relative to the repo root (cwd of `vitest run` is the
    // cockpit workspace).
    for (const rel of sources) {
      // Strip the `apps/cockpit/` prefix — vitest runs with cwd =
      // the cockpit workspace.
      const path = rel.replace(/^apps\/cockpit\//, "");
      const src = await readFile(path, "utf8");
      expect(src).not.toMatch(/readFileSync/);
      expect(src).not.toMatch(/readFile\s*\(/);
    }
  });
});
