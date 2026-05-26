// WP-006 — unit tests for readWorktreeTree.
//
// Per TDD §2.1 step 2, §5 (/api/changes/:id/tree), §5.2, §13.6 and the
// WP-006 Contract test matrix. The function returns ONE LEVEL of
// children per request (TreeNode[]). Children are fetched on expand.
//
// Tests use real temp directories + real symlinks (no fs mocking) so
// the directory-entry resolution, symlink classification, and
// safeJoin integration are exercised end-to-end.

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
import { join } from "node:path";

import { readWorktreeTree } from "../lib/readWorktreeTree";
import {
  PathOutsideWorktreeError,
  NotADirectoryError,
  NotFoundError,
} from "../lib/errors";

describe("readWorktreeTree", () => {
  let base: string;
  let emptyWorktree: string;
  let mixedWorktree: string;
  let ignoreWorktree: string;
  let nestedWorktree: string;
  let symlinkWorktree: string;
  let sortWorktree: string;
  let outsideDir: string;

  beforeAll(async () => {
    base = await mkdtemp(join(tmpdir(), "wp006-readtree-"));

    // 1) Empty worktree
    emptyWorktree = await realpath(await mkdtempInside(base, "wt-empty-"));

    // 2) Mixed: a file + a non-empty directory + an empty directory
    mixedWorktree = await realpath(await mkdtempInside(base, "wt-mixed-"));
    await writeFile(join(mixedWorktree, "a.txt"), "x\n", "utf8");
    await mkdir(join(mixedWorktree, "b"), { recursive: true });
    await writeFile(join(mixedWorktree, "b", "inner.txt"), "y\n", "utf8");
    await mkdir(join(mixedWorktree, "emptydir"), { recursive: true });

    // 3) Worktree with ignored entries
    ignoreWorktree = await realpath(await mkdtempInside(base, "wt-ignore-"));
    await writeFile(join(ignoreWorktree, "a.txt"), "x\n", "utf8");
    await mkdir(join(ignoreWorktree, "node_modules"), { recursive: true });
    await writeFile(
      join(ignoreWorktree, "node_modules", "pkg.json"),
      "{}\n",
      "utf8",
    );
    await mkdir(join(ignoreWorktree, ".git"), { recursive: true });
    await writeFile(join(ignoreWorktree, ".DS_Store"), "ds\n", "utf8");

    // 4) Nested directories — `src/index.ts`
    nestedWorktree = await realpath(await mkdtempInside(base, "wt-nested-"));
    await mkdir(join(nestedWorktree, "src"), { recursive: true });
    await writeFile(join(nestedWorktree, "src", "index.ts"), "// x\n", "utf8");
    // also a file at root to test reading the root level
    await writeFile(join(nestedWorktree, "root.txt"), "r\n", "utf8");

    // 5) Symlinks (inside + outside)
    symlinkWorktree = await realpath(await mkdtempInside(base, "wt-symlink-"));
    outsideDir = await realpath(await mkdtempInside(base, "out-"));
    // Target file outside the worktree
    await writeFile(join(outsideDir, "secret.txt"), "s\n", "utf8");
    // Target file inside the worktree
    await mkdir(join(symlinkWorktree, "real"), { recursive: true });
    await writeFile(join(symlinkWorktree, "real", "a.txt"), "a\n", "utf8");
    // link-in points to a file inside the worktree
    await symlink(
      join(symlinkWorktree, "real", "a.txt"),
      join(symlinkWorktree, "link-in"),
    );
    // link-out-file points to a file outside the worktree (opaque file)
    await symlink(
      join(outsideDir, "secret.txt"),
      join(symlinkWorktree, "link-out-file"),
    );
    // link-out-dir points to a directory outside the worktree (also opaque file)
    await symlink(outsideDir, join(symlinkWorktree, "link-out-dir"));

    // 6) Sort fixture: a.txt, b/, c.txt, d/
    sortWorktree = await realpath(await mkdtempInside(base, "wt-sort-"));
    await writeFile(join(sortWorktree, "a.txt"), "a\n", "utf8");
    await mkdir(join(sortWorktree, "b"), { recursive: true });
    await writeFile(join(sortWorktree, "c.txt"), "c\n", "utf8");
    await mkdir(join(sortWorktree, "d"), { recursive: true });
  });

  afterAll(async () => {
    await rm(base, { recursive: true, force: true });
  });

  it("returns an empty array for an empty directory", async () => {
    const entries = await readWorktreeTree(emptyWorktree, "");
    expect(entries).toEqual([]);
  });

  it("returns directories first, then files; sets hasChildren correctly", async () => {
    const entries = await readWorktreeTree(mixedWorktree, "");
    // dirs first (alphabetical), then files
    expect(entries.map((e) => e.name)).toEqual(["b", "emptydir", "a.txt"]);

    const b = entries.find((e) => e.name === "b")!;
    expect(b.kind).toBe("directory");
    expect(b.hasChildren).toBe(true);
    expect(b.path).toBe("b");

    const empty = entries.find((e) => e.name === "emptydir")!;
    expect(empty.kind).toBe("directory");
    expect(empty.hasChildren).toBe(false);

    const a = entries.find((e) => e.name === "a.txt")!;
    expect(a.kind).toBe("file");
    expect(a.hasChildren).toBe(false);
    expect(a.path).toBe("a.txt");
  });

  it("skips entries whose name matches the ignore list", async () => {
    const entries = await readWorktreeTree(ignoreWorktree, "");
    const names = entries.map((e) => e.name);
    expect(names).toEqual(["a.txt"]);
    expect(names).not.toContain("node_modules");
    expect(names).not.toContain(".git");
    expect(names).not.toContain(".DS_Store");
  });

  it("reads one level inside a subdirectory", async () => {
    const entries = await readWorktreeTree(nestedWorktree, "src");
    expect(entries.map((e) => e.name)).toEqual(["index.ts"]);
    const indexEntry = entries[0]!;
    expect(indexEntry.kind).toBe("file");
    expect(indexEntry.hasChildren).toBe(false);
    expect(indexEntry.path).toBe("src/index.ts");
  });

  it("treats '/' as the worktree root", async () => {
    const entries = await readWorktreeTree(nestedWorktree, "/");
    expect(entries.map((e) => e.name)).toEqual(["src", "root.txt"]);
  });

  it("classifies a symlink pointing inside the worktree as its target kind", async () => {
    const entries = await readWorktreeTree(symlinkWorktree, "");
    const linkIn = entries.find((e) => e.name === "link-in")!;
    expect(linkIn).toBeDefined();
    // target is a file; link-in surfaces as file
    expect(linkIn.kind).toBe("file");
    expect(linkIn.hasChildren).toBe(false);
  });

  it("classifies a symlink pointing OUTSIDE the worktree as opaque file regardless of target kind", async () => {
    const entries = await readWorktreeTree(symlinkWorktree, "");
    const linkOutFile = entries.find((e) => e.name === "link-out-file")!;
    expect(linkOutFile).toBeDefined();
    expect(linkOutFile.kind).toBe("file");
    expect(linkOutFile.hasChildren).toBe(false);

    const linkOutDir = entries.find((e) => e.name === "link-out-dir")!;
    expect(linkOutDir).toBeDefined();
    // even though the target is a directory, the symlink is presented as opaque file
    expect(linkOutDir.kind).toBe("file");
    expect(linkOutDir.hasChildren).toBe(false);
  });

  it("throws PathOutsideWorktreeError on path traversal via safeJoin", async () => {
    await expect(
      readWorktreeTree(nestedWorktree, "../escape"),
    ).rejects.toBeInstanceOf(PathOutsideWorktreeError);
  });

  it("throws NotADirectoryError when relativePath points at a file", async () => {
    await expect(
      readWorktreeTree(nestedWorktree, "root.txt"),
    ).rejects.toBeInstanceOf(NotADirectoryError);
  });

  it("throws NotFoundError when relativePath does not exist", async () => {
    await expect(
      readWorktreeTree(nestedWorktree, "missing"),
    ).rejects.toBeInstanceOf(NotFoundError);
  });

  it("sorts directories-first then alphabetically (mixed a.txt b/ c.txt d/ → b d a.txt c.txt)", async () => {
    const entries = await readWorktreeTree(sortWorktree, "");
    expect(entries.map((e) => e.name)).toEqual(["b", "d", "a.txt", "c.txt"]);
    expect(entries[0]!.kind).toBe("directory");
    expect(entries[1]!.kind).toBe("directory");
    expect(entries[2]!.kind).toBe("file");
    expect(entries[3]!.kind).toBe("file");
  });
});

/**
 * Create a fresh subdirectory inside `parent` with a name starting with
 * `prefix`. Mirrors mkdtemp's API but lets us put several sibling temp
 * directories inside one umbrella parent (which afterAll() removes
 * recursively at the end of the suite).
 */
async function mkdtempInside(parent: string, prefix: string): Promise<string> {
  return await mkdtemp(join(parent, prefix));
}
