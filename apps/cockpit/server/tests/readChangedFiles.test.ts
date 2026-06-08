// WP-P02 — integration tests for readChangedFiles.
//
// readChangedFiles composes the two sanctioned git-diff boundaries
// (gitDiffNameStatus + gitDiffNumstat, both in gitShow.ts) into the wire
// `ChangedFiles` shape: one row per changed path, worded status, and the
// per-file +N/−N counts merged on by path.
//
// We run against a real ephemeral git repo (no mocks at the git boundary
// — TDD §14.5, MEA-09). The `baseKnown:false` legacy path needs no repo.

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  mkdtemp,
  rm,
  writeFile,
  unlink,
  chmod,
  realpath,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

import { readChangedFiles } from "../lib/readChangedFiles";

function git(cwd: string, args: string[]): string {
  const result = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed (status ${result.status}): ${result.stderr}`,
    );
  }
  return result.stdout.trim();
}

describe("readChangedFiles", () => {
  describe("legacy record (no baseSha)", () => {
    it("returns an empty set with baseKnown:false for null baseSha", async () => {
      const result = await readChangedFiles("/nonexistent", null);
      expect(result).toEqual({ files: [], baseKnown: false });
    });

    it("treats an empty-string baseSha as legacy too", async () => {
      const result = await readChangedFiles("/nonexistent", "");
      expect(result).toEqual({ files: [], baseKnown: false });
    });
  });

  describe("against a real repo", () => {
    let repo: string; // realpath-resolved
    let baseSha: string;

    beforeAll(async () => {
      const base = await mkdtemp(join(tmpdir(), "readchanged-test-"));
      repo = await realpath(base);

      git(repo, ["init", "-q", "-b", "main"]);
      git(repo, ["config", "user.email", "test@example.com"]);
      git(repo, ["config", "user.name", "WP-P02 test"]);
      git(repo, ["config", "commit.gpgsign", "false"]);
      git(repo, ["config", "core.fileMode", "true"]);

      // Base commit:
      //   hello.txt   — "one\n" (edited later: 1 add / 1 remove)
      //   removed.txt — "gone\n" (deleted later: 0 add / 1 remove)
      //   blob.bin    — binary (changed later → numstat "-\t-" → null)
      //   mode.sh     — "#!/bin/sh\n" (only its mode changes later → 0/0)
      await writeFile(join(repo, "hello.txt"), "one\n", "utf8");
      await writeFile(join(repo, "removed.txt"), "gone\n", "utf8");
      await writeFile(
        join(repo, "blob.bin"),
        Buffer.from([0x00, 0x01, 0x02, 0x03]),
      );
      await writeFile(join(repo, "mode.sh"), "#!/bin/sh\n", "utf8");
      await chmod(join(repo, "mode.sh"), 0o644);
      git(repo, ["add", "."]);
      git(repo, ["commit", "-q", "-m", "base"]);
      baseSha = git(repo, ["rev-parse", "HEAD"]);

      // Changes committed on top of the base — the cockpit diffs a
      // change's committed worktree against its recorded base sha, and
      // `git diff <base>` ignores untracked files, so the fixture commits.
      await writeFile(join(repo, "hello.txt"), "two\n", "utf8");
      await writeFile(join(repo, "added.txt"), "fresh\n", "utf8");
      await unlink(join(repo, "removed.txt"));
      await writeFile(
        join(repo, "blob.bin"),
        Buffer.from([0x07, 0x06, 0x05, 0x04]),
      );
      // Pure mode change: same bytes, executable bit flipped on.
      await chmod(join(repo, "mode.sh"), 0o755);
      git(repo, ["add", "-A"]);
      git(repo, ["commit", "-q", "-m", "changes"]);
    });

    afterAll(async () => {
      await rm(repo, { recursive: true, force: true });
    });

    it("merges +N/−N counts onto each entry and words the status", async () => {
      const result = await readChangedFiles(repo, baseSha);
      expect(result.baseKnown).toBe(true);
      const byPath = new Map(result.files.map((f) => [f.path, f]));

      expect(byPath.get("hello.txt")).toMatchObject({
        status: "edited",
        added: 1,
        removed: 1,
      });
      expect(byPath.get("added.txt")).toMatchObject({
        status: "new",
        added: 1,
        removed: 0,
      });
      expect(byPath.get("removed.txt")).toMatchObject({
        status: "removed",
        added: 0,
        removed: 1,
      });
    });

    it("nulls both counts for a binary file", async () => {
      const result = await readChangedFiles(repo, baseSha);
      const blob = result.files.find((f) => f.path === "blob.bin");
      expect(blob).toBeDefined();
      expect(blob?.added).toBeNull();
      expect(blob?.removed).toBeNull();
    });

    it("reports 0/0 for a pure mode change (no lines touched)", async () => {
      const result = await readChangedFiles(repo, baseSha);
      const mode = result.files.find((f) => f.path === "mode.sh");
      // A mode-only change touches no lines — numstat reports 0/0 (and
      // the merge would also fall back to 0/0 if numstat omitted it).
      // Either way the count is 0/0, never null.
      expect(mode).toBeDefined();
      expect(mode?.added).toBe(0);
      expect(mode?.removed).toBe(0);
    });
  });
});
