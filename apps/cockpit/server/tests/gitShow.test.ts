// WP-008 — tests for gitShow.
//
// gitShow is the **only** place in the cockpit that spawns `git`. The
// subprocess-hygiene invariants (TDD §13.3, §13.6, §13.7) MUST hold:
//   - args supplied as string[] (no shell, no string concatenation),
//   - shell: false,
//   - 5-second default timeout; child killed on timeout (TimeoutError),
//   - only `git show` is invoked (no add/commit/reset/checkout — grep
//     guards against drift).
//
// These tests run against a real ephemeral git repo (no mocks at the
// git boundary — TDD §14.5, MEA-09).

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  mkdtemp,
  rm,
  writeFile,
  readFile,
  realpath,
  unlink,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

import {
  gitShow,
  gitDiffNameStatus,
  gitDiffNumstat,
} from "../lib/gitShow";
import { TimeoutError, GitError } from "../lib/errors";

function gitInit(cwd: string, args: string[]): string {
  const result = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed (status ${result.status}): ${result.stderr}`,
    );
  }
  return result.stdout.trim();
}

describe("gitShow", () => {
  let repo: string; // realpath-resolved
  let baseSha: string;

  beforeAll(async () => {
    const base = await mkdtemp(join(tmpdir(), "gitshow-test-"));
    repo = await realpath(base);

    // Initialise a real git repo with a base commit holding hello.txt
    // = "hello\n" and a binary file with NUL bytes.
    gitInit(repo, ["init", "-q", "-b", "main"]);
    gitInit(repo, ["config", "user.email", "test@example.com"]);
    gitInit(repo, ["config", "user.name", "WP-008 test"]);
    gitInit(repo, ["config", "commit.gpgsign", "false"]);

    await writeFile(join(repo, "hello.txt"), "hello\n", "utf8");
    // Binary file: 1 KiB of NUL bytes — exercises detectBinary.
    await writeFile(join(repo, "blob.bin"), Buffer.alloc(1024, 0));

    gitInit(repo, ["add", "hello.txt", "blob.bin"]);
    gitInit(repo, ["commit", "-q", "-m", "base commit"]);
    baseSha = gitInit(repo, ["rev-parse", "HEAD"]);

    // Modify hello.txt in the worktree (post-base-commit) so future
    // readFileDiff tests can see a delta. gitShow itself does not look
    // at the worktree; this is harmless to gitShow's tests.
    await writeFile(join(repo, "hello.txt"), "hello, world\n", "utf8");
  });

  afterAll(async () => {
    await rm(repo, { recursive: true, force: true });
  });

  it("returns exitCode 0 + stdout containing the base contents for a valid sha:path", async () => {
    const result = await gitShow({
      cwd: repo,
      sha: baseSha,
      relativePath: "hello.txt",
    });
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toBeInstanceOf(Buffer);
    expect(result.stdout.toString("utf8")).toBe("hello\n");
  });

  it("returns the raw bytes (Buffer) for a binary file at base", async () => {
    const result = await gitShow({
      cwd: repo,
      sha: baseSha,
      relativePath: "blob.bin",
    });
    expect(result.exitCode).toBe(0);
    // git show's default behaviour is to emit the bytes verbatim for a
    // tracked blob — no LF conversion, no textconv filter. The caller
    // detects binary; gitShow stays content-agnostic.
    expect(result.stdout.length).toBe(1024);
    expect(result.stdout[0]).toBe(0);
  });

  it("returns non-zero exit + stderr (without throwing) for a path not in the commit", async () => {
    const result = await gitShow({
      cwd: repo,
      sha: baseSha,
      relativePath: "never-existed.txt",
    });
    expect(result.exitCode).not.toBe(0);
    expect(result.stderr.length).toBeGreaterThan(0);
    // git's specific phrasing for "path is in the worktree but not at
    // <sha>" vs "does not exist at all in <sha>" is what readFileDiff
    // pattern-matches on — assert both shapes show up in git's output.
    expect(
      result.stderr.includes("exists on disk") ||
        result.stderr.includes("does not exist") ||
        result.stderr.includes("path") ||
        result.stderr.includes("ambiguous"),
    ).toBe(true);
  });

  it("returns non-zero exit + stderr (without throwing) for a bad-revision sha", async () => {
    const result = await gitShow({
      cwd: repo,
      sha: "0000000000000000000000000000000000000000",
      relativePath: "hello.txt",
    });
    expect(result.exitCode).not.toBe(0);
    expect(result.stderr.length).toBeGreaterThan(0);
  });

  it("kills the child and throws TimeoutError when timeoutMs expires", async () => {
    // Force a timeout that's effectively immediate. The child should be
    // SIGKILLed; the promise should reject with TimeoutError; no zombie
    // child should remain (the test process exits cleanly if not).
    await expect(
      gitShow({
        cwd: repo,
        sha: baseSha,
        relativePath: "hello.txt",
        timeoutMs: 1,
      }),
    ).rejects.toBeInstanceOf(TimeoutError);
  });

  it("source file uses spawn with args:string[] and shell:false (no shell, no concat)", async () => {
    // Read the implementation file and assert it does not contain
    // shell-mode invocations. This is a guard against a future
    // refactor regressing the hygiene invariant.
    const src = await readFile(
      join(__dirname, "..", "lib", "gitShow.ts"),
      "utf8",
    );
    // Must not enable the shell.
    expect(src).not.toMatch(/shell\s*:\s*true/);
    // Must not interpolate the sha or path into a string command line
    // (no `git show ${sha}` patterns; spawn's first arg is the bare
    // executable name).
    expect(src).not.toMatch(/spawn\s*\(\s*[`'"]\s*git\s/);
    // Must use spawn from node:child_process.
    expect(src).toMatch(/from\s+["']node:child_process["']/);
    expect(src).toMatch(/spawn\s*\(/);
  });

  it("source file uses only `git show` (no add/commit/reset/checkout — drift guard)", async () => {
    const src = await readFile(
      join(__dirname, "..", "lib", "gitShow.ts"),
      "utf8",
    );
    // The grep should match the literal git subcommand argument inside
    // the args array (e.g. `"show"`); the absence of any other git
    // mutating subcommand is the invariant the cockpit's read-only
    // guarantee depends on. Comments mentioning these strings are
    // allowed, but as a defence-in-depth the grep is conservative.
    // Strip line-comments before scanning.
    const code = src
      .split("\n")
      .map((line) => line.replace(/\/\/.*$/, ""))
      .join("\n");
    expect(code).not.toMatch(/["']add["']/);
    expect(code).not.toMatch(/["']commit["']/);
    expect(code).not.toMatch(/["']reset["']/);
    expect(code).not.toMatch(/["']checkout["']/);
    expect(code).not.toMatch(/["']push["']/);
    expect(code).not.toMatch(/["']pull["']/);
    expect(code).not.toMatch(/["']merge["']/);
    expect(code).not.toMatch(/["']rebase["']/);
    // The one subcommand it MUST contain:
    expect(code).toMatch(/["']show["']/);
  });
});

// WP-P02 — per-file diff data (git diff --name-status / --numstat).
//
// Both helpers run `git diff <baseSha> --` against the worktree through
// the same sanctioned spawn site as gitShow. Tested against a real
// ephemeral repo (no mocks at the git boundary — TDD §14.5, MEA-09):
//   - hello.txt   edited (1 added, 1 removed)
//   - added.txt   new    (1 added, 0 removed)
//   - removed.txt removed (0 added, 1 removed)
//   - blob.bin    binary edit ("-" / "-" → null counts)
describe("gitDiffNameStatus / gitDiffNumstat", () => {
  let repo: string; // realpath-resolved
  let baseSha: string;

  beforeAll(async () => {
    const base = await mkdtemp(join(tmpdir(), "gitdiff-test-"));
    repo = await realpath(base);

    gitInit(repo, ["init", "-q", "-b", "main"]);
    gitInit(repo, ["config", "user.email", "test@example.com"]);
    gitInit(repo, ["config", "user.name", "WP-P02 test"]);
    gitInit(repo, ["config", "commit.gpgsign", "false"]);

    // Base commit:
    //   hello.txt   — "one\n" (edited later)
    //   removed.txt — "gone\n" (deleted later)
    //   blob.bin    — 8 bytes incl. a NUL (binary; changed later)
    await writeFile(join(repo, "hello.txt"), "one\n", "utf8");
    await writeFile(join(repo, "removed.txt"), "gone\n", "utf8");
    await writeFile(
      join(repo, "blob.bin"),
      Buffer.from([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07]),
    );
    gitInit(repo, ["add", "."]);
    gitInit(repo, ["commit", "-q", "-m", "base"]);
    baseSha = gitInit(repo, ["rev-parse", "HEAD"]);

    // Changes committed on top of the base (the cockpit diffs a
    // change's committed worktree against its recorded base sha, so the
    // fixture commits its edits — `git diff <base>` ignores untracked
    // files):
    //   hello.txt   — "two\n"   (1 added, 1 removed)
    //   added.txt   — new file  (1 added, 0 removed)
    //   removed.txt — deleted   (0 added, 1 removed)
    //   blob.bin    — different bytes (binary; numstat "-\t-")
    await writeFile(join(repo, "hello.txt"), "two\n", "utf8");
    await writeFile(join(repo, "added.txt"), "fresh\n", "utf8");
    await unlink(join(repo, "removed.txt"));
    await writeFile(
      join(repo, "blob.bin"),
      Buffer.from([0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, 0x00]),
    );
    gitInit(repo, ["add", "-A"]);
    gitInit(repo, ["commit", "-q", "-m", "changes"]);
  });

  afterAll(async () => {
    await rm(repo, { recursive: true, force: true });
  });

  it("name-status maps A/M/D to new/edited/removed", async () => {
    const entries = await gitDiffNameStatus({ cwd: repo, baseSha });
    const byPath = new Map(entries.map((e) => [e.path, e.status]));
    expect(byPath.get("hello.txt")).toBe("edited");
    expect(byPath.get("added.txt")).toBe("new");
    expect(byPath.get("removed.txt")).toBe("removed");
    expect(byPath.get("blob.bin")).toBe("edited");
  });

  it("numstat parses added/removed counts for text files", async () => {
    const entries = await gitDiffNumstat({ cwd: repo, baseSha });
    const byPath = new Map(entries.map((e) => [e.path, e]));
    expect(byPath.get("hello.txt")).toMatchObject({ added: 1, removed: 1 });
    expect(byPath.get("added.txt")).toMatchObject({ added: 1, removed: 0 });
    expect(byPath.get("removed.txt")).toMatchObject({ added: 0, removed: 1 });
  });

  it('numstat maps a binary file ("-\\t-") to null counts', async () => {
    const entries = await gitDiffNumstat({ cwd: repo, baseSha });
    const blob = entries.find((e) => e.path === "blob.bin");
    expect(blob).toBeDefined();
    expect(blob?.added).toBeNull();
    expect(blob?.removed).toBeNull();
  });

  it("numstat returns [] for an empty diff (base == worktree)", async () => {
    // A throwaway repo whose worktree matches its only commit exactly.
    const clean = await realpath(
      await mkdtemp(join(tmpdir(), "gitdiff-clean-")),
    );
    try {
      gitInit(clean, ["init", "-q", "-b", "main"]);
      gitInit(clean, ["config", "user.email", "test@example.com"]);
      gitInit(clean, ["config", "user.name", "WP-P02 test"]);
      gitInit(clean, ["config", "commit.gpgsign", "false"]);
      await writeFile(join(clean, "only.txt"), "stable\n", "utf8");
      gitInit(clean, ["add", "."]);
      gitInit(clean, ["commit", "-q", "-m", "only"]);
      const sha = gitInit(clean, ["rev-parse", "HEAD"]);

      const entries = await gitDiffNumstat({ cwd: clean, baseSha: sha });
      expect(entries).toEqual([]);
    } finally {
      await rm(clean, { recursive: true, force: true });
    }
  });

  it("throws GitError on a non-zero exit (bad-revision sha)", async () => {
    await expect(
      gitDiffNumstat({
        cwd: repo,
        baseSha: "0000000000000000000000000000000000000000",
      }),
    ).rejects.toBeInstanceOf(GitError);
    await expect(
      gitDiffNameStatus({
        cwd: repo,
        baseSha: "0000000000000000000000000000000000000000",
      }),
    ).rejects.toBeInstanceOf(GitError);
  });

  it("throws TimeoutError when timeoutMs expires", async () => {
    await expect(
      gitDiffNumstat({ cwd: repo, baseSha, timeoutMs: 1 }),
    ).rejects.toBeInstanceOf(TimeoutError);
  });
});
