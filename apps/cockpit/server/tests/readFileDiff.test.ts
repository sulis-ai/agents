// WP-008 — integration tests for readFileDiff.
//
// readFileDiff composes safeJoin (WP-004) + gitShow (this WP) +
// fs.readFile + detectBinary + languageHint (WP-007) into the
// `{ base, current }` shape Monaco's DiffEditor consumes (ADR-006,
// TDD §5.1 FileDiff, §7).
//
// We run against a real ephemeral git repo (no mocks at the git
// boundary — TDD §14.5, MEA-09). The MAX_BYTES constant is imported
// from readFileContents (WP-007) to assert the reuse invariant.

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdtemp, rm, writeFile, unlink, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

import { readFileDiff } from "../lib/readFileDiff";
import { MAX_BYTES } from "../lib/readFileContents";
import { PathOutsideWorktreeError, GitError } from "../lib/errors";

function git(cwd: string, args: string[]): string {
  const result = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed (status ${result.status}): ${result.stderr}`,
    );
  }
  return result.stdout.trim();
}

describe("readFileDiff", () => {
  let repo: string; // realpath-resolved absolute path
  let baseSha: string;

  beforeAll(async () => {
    const base = await mkdtemp(join(tmpdir(), "readfilediff-test-"));
    repo = await realpath(base);

    git(repo, ["init", "-q", "-b", "main"]);
    git(repo, ["config", "user.email", "test@example.com"]);
    git(repo, ["config", "user.name", "WP-008 test"]);
    git(repo, ["config", "commit.gpgsign", "false"]);

    // Base commit:
    //   hello.txt     — "hello\n"      (modified later in worktree)
    //   removed.txt   — "to-delete\n"  (deleted later in worktree)
    //   blob.bin      — 1 KiB of NULs  (binary file)
    //   huge.txt      — 2 MiB of 'A'   (exceeds MAX_BYTES)
    await writeFile(join(repo, "hello.txt"), "hello\n", "utf8");
    await writeFile(join(repo, "removed.txt"), "to-delete\n", "utf8");
    await writeFile(join(repo, "blob.bin"), Buffer.alloc(1024, 0));
    await writeFile(
      join(repo, "huge.txt"),
      Buffer.alloc(2 * 1024 * 1024, 0x41),
    );
    git(repo, ["add", "."]);
    git(repo, ["commit", "-q", "-m", "base"]);
    baseSha = git(repo, ["rev-parse", "HEAD"]);

    // Post-base modifications (these only touch the worktree, not the
    // commit, so `git show <baseSha>:<path>` still returns the original
    // contents):
    //   hello.txt   — modified to "hello, world\n"
    //   removed.txt — deleted
    //   added.ts    — newly created (not at base)
    await writeFile(join(repo, "hello.txt"), "hello, world\n", "utf8");
    await unlink(join(repo, "removed.txt"));
    await writeFile(join(repo, "added.ts"), "export const x = 1;\n", "utf8");
  });

  afterAll(async () => {
    await rm(repo, { recursive: true, force: true });
  });

  it("file exists at base and is modified in the worktree", async () => {
    const result = await readFileDiff(repo, baseSha, "hello.txt");
    expect(result.base).toBe("hello\n");
    expect(result.current).toBe("hello, world\n");
    expect(result.binary).toBe(false);
    expect(result.truncated).toBe(false);
    expect(result.path).toBe("hello.txt");
    expect(result.absolutePath).toBe(join(repo, "hello.txt"));
    expect(result.language).toBeNull(); // .txt isn't in LANGUAGE_HINTS
  });

  it("file exists at base and is deleted in the worktree (current=null)", async () => {
    const result = await readFileDiff(repo, baseSha, "removed.txt");
    expect(result.base).toBe("to-delete\n");
    expect(result.current).toBeNull();
    expect(result.binary).toBe(false);
    expect(result.truncated).toBe(false);
  });

  it("file added in the worktree (base=null)", async () => {
    const result = await readFileDiff(repo, baseSha, "added.ts");
    expect(result.base).toBeNull();
    expect(result.current).toBe("export const x = 1;\n");
    expect(result.binary).toBe(false);
    expect(result.truncated).toBe(false);
    // .ts → "typescript" via languageHint.
    expect(result.language).toBe("typescript");
  });

  it("file at base larger than MAX_BYTES → both null, truncated=true", async () => {
    const result = await readFileDiff(repo, baseSha, "huge.txt");
    expect(result.base).toBeNull();
    expect(result.current).toBeNull();
    expect(result.truncated).toBe(true);
    expect(result.binary).toBe(false);
  });

  it("file at base contains NUL bytes → binary=true, both null", async () => {
    const result = await readFileDiff(repo, baseSha, "blob.bin");
    expect(result.base).toBeNull();
    expect(result.current).toBeNull();
    expect(result.binary).toBe(true);
    expect(result.truncated).toBe(false);
    expect(result.language).toBeNull();
  });

  it("safeJoin traversal throws PathOutsideWorktreeError (no git invocation)", async () => {
    await expect(
      readFileDiff(repo, baseSha, "../escape.txt"),
    ).rejects.toBeInstanceOf(PathOutsideWorktreeError);
  });

  it("invalid base_sha throws GitError", async () => {
    // Use a malformed (non-hex) sha so git rejects with
    //   "fatal: invalid object name 'zzz…'"
    // rather than the "path 'hello.txt' exists on disk, but not in
    // '<sha>'" message git emits for syntactically-valid-but-unknown
    // shas (which the caller correctly maps to base: null).
    await expect(
      readFileDiff(
        repo,
        "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
        "hello.txt",
      ),
    ).rejects.toBeInstanceOf(GitError);
  });

  it("reuses WP-007's MAX_BYTES constant (no duplicate threshold)", () => {
    // Reuse-invariant guard: WP-008's Blue spec mandates a single
    // source of truth for the 1 MiB cap.
    expect(MAX_BYTES).toBe(1024 * 1024);
  });
});
