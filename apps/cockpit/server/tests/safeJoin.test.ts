// WP-004 — unit tests for safeJoin path-sanitisation utility.
//
// Per TDD §13.2 (path traversal MUST) and §14.3 (path-sanitisation
// unit tests). The function is the single chokepoint every endpoint
// that accepts a `path` query parameter calls before touching the
// filesystem. The tests use real symlinks in a tmp directory; no
// mocking of fs.realpath (per WP Green spec).

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  mkdtemp,
  rm,
  mkdir,
  writeFile,
  symlink,
  realpath,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, sep } from "node:path";

import { safeJoin } from "../lib/safeJoin";
import { PathOutsideWorktreeError } from "../lib/errors";

describe("safeJoin", () => {
  let worktree: string; // resolved (realpath-d) absolute path
  let outsideDir: string; // a sibling directory the worktree must NOT escape into

  beforeAll(async () => {
    // Create two sibling dirs in tmpdir: one is "the worktree", the other
    // is outside it. realpath the worktree root because macOS tmpdir is
    // /var/folders/... which is itself a symlink to /private/var/folders/...
    const base = await mkdtemp(join(tmpdir(), "safejoin-test-"));
    worktree = await realpath(await mkdtempInside(base, "wt-"));
    outsideDir = await realpath(await mkdtempInside(base, "out-"));

    // Seed an existing file inside the worktree so the "existing file"
    // case has something to resolve to.
    await mkdir(join(worktree, "src"), { recursive: true });
    await writeFile(join(worktree, "src", "index.ts"), "// exists\n", "utf8");

    // Seed a file outside the worktree to be the target of the escaping symlink.
    await writeFile(join(outsideDir, "secret.txt"), "secret\n", "utf8");

    // Symlinks: one pointing outside the worktree, one pointing inside.
    await symlink(join(outsideDir, "secret.txt"), join(worktree, "link-out"));
    await symlink(join(worktree, "src", "index.ts"), join(worktree, "link-in"));
  });

  afterAll(async () => {
    // beforeAll created two sibling dirs under one parent (the mkdtemp
    // result). The worktree's parent is the same as outsideDir's parent.
    // Walk up one level and remove recursively.
    const parent = worktree.substring(0, worktree.lastIndexOf(sep));
    await rm(parent, { recursive: true, force: true });
  });

  // -- Table cases per WP Contract --

  it("accepts a relative path to an existing file", async () => {
    const resolved = await safeJoin(worktree, "src/index.ts");
    expect(resolved).toBe(join(worktree, "src", "index.ts"));
  });

  it("normalises ./ prefix", async () => {
    const resolved = await safeJoin(worktree, "./src/index.ts");
    expect(resolved).toBe(join(worktree, "src", "index.ts"));
  });

  it("normalises src/./ embedded segments", async () => {
    const resolved = await safeJoin(worktree, "src/./index.ts");
    expect(resolved).toBe(join(worktree, "src", "index.ts"));
  });

  it("rejects ../etc/passwd", async () => {
    await expect(safeJoin(worktree, "../etc/passwd")).rejects.toBeInstanceOf(
      PathOutsideWorktreeError,
    );
  });

  it("rejects ../../../../etc/passwd", async () => {
    await expect(
      safeJoin(worktree, "../../../../etc/passwd"),
    ).rejects.toBeInstanceOf(PathOutsideWorktreeError);
  });

  it("rejects an absolute path (/etc/passwd) before any filesystem touch", async () => {
    await expect(safeJoin(worktree, "/etc/passwd")).rejects.toBeInstanceOf(
      PathOutsideWorktreeError,
    );
  });

  it("resolves a non-existent leaf so long as its parent is inside the worktree", async () => {
    const resolved = await safeJoin(worktree, "src/never-existed.ts");
    expect(resolved).toBe(join(worktree, "src", "never-existed.ts"));
  });

  it("rejects a symlink whose target is outside the worktree", async () => {
    await expect(safeJoin(worktree, "link-out")).rejects.toBeInstanceOf(
      PathOutsideWorktreeError,
    );
  });

  it("resolves a symlink whose target is inside the worktree", async () => {
    const resolved = await safeJoin(worktree, "link-in");
    expect(resolved).toBe(join(worktree, "src", "index.ts"));
  });

  it("rejects an empty user path", async () => {
    await expect(safeJoin(worktree, "")).rejects.toBeInstanceOf(
      PathOutsideWorktreeError,
    );
  });

  it("rejects a path containing a NUL byte", async () => {
    await expect(safeJoin(worktree, "src/\0null")).rejects.toBeInstanceOf(
      PathOutsideWorktreeError,
    );
  });

  // -- Property-style test per WP Red checklist --
  // 50 randomly-generated relative paths. Half are guaranteed-inside
  // (no .. segments), half include at least one escaping .. that
  // would take the resolved path above the worktree root. The
  // guaranteed-inside set must resolve (to a path with the worktree
  // prefix); the escaping set must throw PathOutsideWorktreeError.
  // We hand-roll the generator rather than pulling in fast-check to
  // keep the dep footprint at zero (CP-01 — established convention,
  // no new deps for a 50-iteration loop).
  it("property: random in-bound paths resolve; random escaping paths throw", async () => {
    const SEGMENTS = ["a", "b", "c", "src", "dir1", "dir2", "x", "y"];
    const rand = (n: number) => Math.floor(Math.random() * n);
    const segment = () => SEGMENTS[rand(SEGMENTS.length)]!;

    for (let i = 0; i < 25; i++) {
      // In-bound: 1..5 segments, no ..
      const depth = 1 + rand(5);
      const parts: string[] = [];
      for (let d = 0; d < depth; d++) parts.push(segment());
      const userPath = parts.join("/");
      const resolved = await safeJoin(worktree, userPath);
      expect(resolved.startsWith(worktree + sep) || resolved === worktree).toBe(
        true,
      );
    }

    for (let i = 0; i < 25; i++) {
      // Escaping: enough ".." to climb above worktree root, then a tail
      // segment. The number of leading ".." (5..8) exceeds the worktree
      // root depth from anywhere inside it.
      const climbs = 5 + rand(4);
      const parts: string[] = [];
      for (let c = 0; c < climbs; c++) parts.push("..");
      parts.push("etc", "passwd");
      const userPath = parts.join("/");
      await expect(safeJoin(worktree, userPath)).rejects.toBeInstanceOf(
        PathOutsideWorktreeError,
      );
    }
  });
});

// mkdtemp creates a directory using a prefix that includes a random
// suffix; we want two siblings inside one shared parent so the cleanup
// in afterAll is straightforward.
async function mkdtempInside(parent: string, prefix: string): Promise<string> {
  return await mkdtemp(join(parent, prefix));
}
