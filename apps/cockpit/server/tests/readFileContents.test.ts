// WP-007 — integration tests for readFileContents.
//
// Per TDD §5.1 (FileContents shape), §5.2 (1 MiB server-side cap),
// §13.6 (binary detection — NUL byte in first 8 KiB). The function
// composes safeJoin (WP-004) + fs.stat + fs.readFile + detectBinary
// + languageHint. We use a real tmpdir so the size + binary code
// paths are exercised end-to-end against the filesystem (no fs
// mocking — same discipline as the WP-004 tests).

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, rm, mkdir, writeFile, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { readFileContents, MAX_BYTES } from "../lib/readFileContents";
import {
  PathOutsideWorktreeError,
  NotFoundError,
  IsADirectoryError,
} from "../lib/errors";

describe("readFileContents", () => {
  let worktree: string; // realpath-resolved absolute path

  beforeAll(async () => {
    const base = await mkdtemp(join(tmpdir(), "readfile-test-"));
    worktree = await realpath(base);

    // Seed: 5 KB text TypeScript file.
    const text5k = "// hello\n".repeat(
      Math.ceil((5 * 1024) / "// hello\n".length),
    );
    await mkdir(join(worktree, "src"), { recursive: true });
    await writeFile(join(worktree, "src", "hello.ts"), text5k, "utf8");

    // Seed: 2 MiB text file (exceeds the 1 MiB cap → truncated).
    const text2m = Buffer.alloc(2 * 1024 * 1024, 0x41); // 2 MiB of 'A'
    await writeFile(join(worktree, "big.txt"), text2m);

    // Seed: 100 KB binary file (NUL bytes throughout the first 8 KiB).
    const bin = Buffer.alloc(100 * 1024, 0);
    await writeFile(join(worktree, "blob.bin"), bin);

    // Seed: 0-byte file.
    await writeFile(join(worktree, "empty.txt"), "");

    // Seed: file with unknown extension.
    await writeFile(join(worktree, "data.xyz"), "some content\n", "utf8");

    // Seed: a directory (for IsADirectoryError).
    await mkdir(join(worktree, "adir"));

    // Seed: a file exactly at the cap (= MAX_BYTES bytes) — should
    // NOT be truncated, since the rule is "> MAX_BYTES" not ">=".
    await writeFile(join(worktree, "exact.txt"), Buffer.alloc(MAX_BYTES, 0x42));

    // Seed: a file one byte over the cap — should be truncated.
    await writeFile(
      join(worktree, "over.txt"),
      Buffer.alloc(MAX_BYTES + 1, 0x43),
    );
  });

  afterAll(async () => {
    await rm(worktree, { recursive: true, force: true });
  });

  it("reads a small text file and returns content + language hint", async () => {
    const result = await readFileContents(worktree, "src/hello.ts");
    expect(result.binary).toBe(false);
    expect(result.truncated).toBe(false);
    expect(result.content).not.toBeNull();
    expect(typeof result.content).toBe("string");
    expect((result.content as string).startsWith("// hello")).toBe(true);
    expect(result.language).toBe("typescript");
    expect(result.path).toBe("src/hello.ts");
    expect(result.absolutePath).toBe(join(worktree, "src", "hello.ts"));
    expect(result.sizeBytes).toBeGreaterThan(0);
  });

  it("returns truncated=true for a file larger than MAX_BYTES", async () => {
    const result = await readFileContents(worktree, "big.txt");
    expect(result.content).toBeNull();
    expect(result.truncated).toBe(true);
    expect(result.binary).toBe(false);
    expect(result.sizeBytes).toBe(2 * 1024 * 1024);
    expect(result.path).toBe("big.txt");
  });

  it("returns binary=true for a file with NUL bytes in the first 8 KiB", async () => {
    const result = await readFileContents(worktree, "blob.bin");
    expect(result.content).toBeNull();
    expect(result.binary).toBe(true);
    expect(result.truncated).toBe(false);
    expect(result.sizeBytes).toBe(100 * 1024);
    expect(result.language).toBeNull();
  });

  it("returns content='' for an empty text file (not binary, not truncated)", async () => {
    const result = await readFileContents(worktree, "empty.txt");
    expect(result.content).toBe("");
    expect(result.binary).toBe(false);
    expect(result.truncated).toBe(false);
    expect(result.sizeBytes).toBe(0);
  });

  it("returns language=null for an unknown extension", async () => {
    const result = await readFileContents(worktree, "data.xyz");
    expect(result.language).toBeNull();
    expect(result.binary).toBe(false);
    expect(result.content).toBe("some content\n");
  });

  it("throws PathOutsideWorktreeError when the user-supplied path escapes", async () => {
    await expect(
      readFileContents(worktree, "../escape.txt"),
    ).rejects.toBeInstanceOf(PathOutsideWorktreeError);
  });

  it("throws NotFoundError when the file does not exist", async () => {
    await expect(
      readFileContents(worktree, "does-not-exist.txt"),
    ).rejects.toBeInstanceOf(NotFoundError);
  });

  it("throws IsADirectoryError when the path resolves to a directory", async () => {
    await expect(readFileContents(worktree, "adir")).rejects.toBeInstanceOf(
      IsADirectoryError,
    );
  });

  it("treats a file of EXACTLY MAX_BYTES bytes as NOT truncated", async () => {
    // The cap is `> MAX_BYTES`. A file at exactly the cap is still
    // returned in full. This is the canonical boundary-value test.
    const result = await readFileContents(worktree, "exact.txt");
    expect(result.truncated).toBe(false);
    expect(result.sizeBytes).toBe(MAX_BYTES);
    expect(result.content).not.toBeNull();
    expect((result.content as string).length).toBe(MAX_BYTES);
  });

  it("treats a file one byte over MAX_BYTES as truncated", async () => {
    const result = await readFileContents(worktree, "over.txt");
    expect(result.truncated).toBe(true);
    expect(result.content).toBeNull();
    expect(result.sizeBytes).toBe(MAX_BYTES + 1);
  });

  it("honours the opts.maxBytes override when supplied", async () => {
    // With a tiny cap, even the small 5 KB file should be truncated.
    const result = await readFileContents(worktree, "src/hello.ts", {
      maxBytes: 1024,
    });
    expect(result.truncated).toBe(true);
    expect(result.content).toBeNull();
    expect(result.sizeBytes).toBeGreaterThan(1024);
  });

  it("MAX_BYTES equals 1 MiB (1024 * 1024)", () => {
    expect(MAX_BYTES).toBe(1024 * 1024);
  });
});
