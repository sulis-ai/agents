// WP-004 — detectOpenBlocker.ts unit tests.
//
// The read-time blocker signal (FR-12): a change is "blocked" when its
// worktree carries a BLOCKER-*.md under any
// .architecture/<project>/work-packages/. Read-only — only directory
// listing, never a write. Best-effort: absent worktree / arch dir → false.

import { describe, it, expect } from "vitest";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { detectOpenBlocker } from "../lib/detectOpenBlocker";

async function makeWorktree(): Promise<string> {
  return await mkdtemp(join(tmpdir(), "wt-blocker-"));
}

describe("detectOpenBlocker (FR-12)", () => {
  it("returns true when a BLOCKER-*.md exists under work-packages", async () => {
    const wt = await makeWorktree();
    try {
      const wpDir = join(wt, ".architecture", "my-project", "work-packages");
      await mkdir(wpDir, { recursive: true });
      await writeFile(join(wpDir, "BLOCKER-WP-004.md"), "# parked", "utf8");
      expect(await detectOpenBlocker(wt)).toBe(true);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("returns false when work-packages has WP files but no BLOCKER", async () => {
    const wt = await makeWorktree();
    try {
      const wpDir = join(wt, ".architecture", "my-project", "work-packages");
      await mkdir(wpDir, { recursive: true });
      await writeFile(join(wpDir, "WP-004-status.md"), "# wp", "utf8");
      await writeFile(join(wpDir, "INDEX.md"), "# index", "utf8");
      expect(await detectOpenBlocker(wt)).toBe(false);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("returns false when the worktree has no .architecture dir", async () => {
    const wt = await makeWorktree();
    try {
      expect(await detectOpenBlocker(wt)).toBe(false);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });

  it("returns false for a non-existent worktree path (best-effort)", async () => {
    expect(await detectOpenBlocker("/tmp/does-not-exist-wp004")).toBe(false);
  });

  it("skips a project dir that has no work-packages subdir, still finds a blocker in another", async () => {
    const wt = await makeWorktree();
    try {
      // project-a has no work-packages dir at all.
      await mkdir(join(wt, ".architecture", "project-a"), { recursive: true });
      // project-b carries the blocker.
      const wpDir = join(wt, ".architecture", "project-b", "work-packages");
      await mkdir(wpDir, { recursive: true });
      await writeFile(join(wpDir, "BLOCKER-WP-009.md"), "# parked", "utf8");
      expect(await detectOpenBlocker(wt)).toBe(true);
    } finally {
      await rm(wt, { recursive: true, force: true });
    }
  });
});
