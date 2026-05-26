// WP-006 — worktree tree reader.
//
// Returns ONE LEVEL of the worktree's file/folder tree at `relativePath`.
// Children of subdirectories are fetched on expand (TDD §2.1 step 2,
// §5.2, §13.6) — never recurse here.
//
// Path safety: `relativePath` is always run through `safeJoin` (WP-004)
// before any I/O. `safeJoin` is the only path-resolution call in this
// module; there is no raw `path.join` against user-supplied input.
//
// Symlinks:
//   - Symlinks whose target resolves INSIDE the worktree are surfaced
//     as their target's kind (file → "file", dir → "directory").
//     `hasChildren` is computed for inside-directory targets.
//   - Symlinks whose target resolves OUTSIDE the worktree are surfaced
//     as `kind: "file"` with `hasChildren: false`, regardless of what
//     the target actually is. This is a deliberate UX choice — the
//     cockpit does not reveal anything about paths outside the
//     worktree — and matches the WP Contract spec.
//
// Sort order: directories first (alphabetical by name), then files
// (alphabetical by name). The `Intl.Collator` here would be overkill;
// plain string comparison is what `git ls-files` and most file
// explorers use.

import { readdir, stat, realpath } from "node:fs/promises";
import { join, posix, sep } from "node:path";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { TreeNode } from "../../shared/api-types";

import { safeJoin } from "./safeJoin";
import { NotADirectoryError, NotFoundError } from "./errors";
import { DEFAULT_IGNORE } from "./ignoreList";

/**
 * Returns the immediate children of `relativePath` inside
 * `worktreeRoot`, sorted directories-first then alphabetically.
 *
 * @param worktreeRoot absolute path to the worktree root (trusted —
 *   comes from the change store).
 * @param relativePath worktree-relative path. `""` or `"/"` means
 *   the worktree root itself.
 *
 * @throws PathOutsideWorktreeError — `relativePath` escapes the
 *   worktree (delegated to `safeJoin`).
 * @throws NotFoundError — the resolved path does not exist.
 * @throws NotADirectoryError — the resolved path is a file (or other
 *   non-directory).
 */
export async function readWorktreeTree(
  worktreeRoot: string,
  relativePath: string,
): Promise<TreeNode[]> {
  const resolvedDir = await resolveTreeRoot(worktreeRoot, relativePath);

  let dirents;
  try {
    dirents = await readdir(resolvedDir, { withFileTypes: true });
  } catch (err) {
    if (isErrnoException(err) && err.code === "ENOTDIR") {
      // safeJoin returned a path that exists but is a file — readdir
      // failed with ENOTDIR. Surface as NotADirectoryError so the
      // route handler can translate to a 400.
      throw new NotADirectoryError(`path is not a directory: ${relativePath}`);
    }
    throw err;
  }

  const entries: TreeNode[] = [];

  for (const dirent of dirents) {
    if (DEFAULT_IGNORE.has(dirent.name)) {
      continue;
    }

    // Build the worktree-relative path for this entry. Use posix
    // joiner so the wire shape uses `/` separators regardless of host
    // OS — the client receives the same shape on macOS / Linux /
    // Windows.
    const childRelative = joinRelative(relativePath, dirent.name);
    const node = await classifyChild(
      worktreeRoot,
      resolvedDir,
      dirent,
      childRelative,
    );
    entries.push(node);
  }

  // Sort: directories first, then files; alphabetical within each
  // bucket. Avoids a custom Intl.Collator — plain string compare is
  // what file explorers and `git ls-files` use.
  entries.sort((a, b) => {
    if (a.kind !== b.kind) {
      return a.kind === "directory" ? -1 : 1;
    }
    return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
  });

  return entries;
}

/**
 * Resolve `relativePath` to an absolute, in-worktree directory.
 * Throws `NotFoundError` if the path doesn't exist and
 * `NotADirectoryError` if the path exists but is not a directory.
 * Delegates all path-safety checks to `safeJoin`.
 */
async function resolveTreeRoot(
  worktreeRoot: string,
  relativePath: string,
): Promise<string> {
  // `""` and `"/"` both denote the worktree root. We can't pass `""`
  // to `safeJoin` (which rejects empty paths as a defensive measure),
  // so short-circuit to the worktree root after a single `realpath`
  // to normalise the macOS /var → /private/var symlink.
  if (relativePath === "" || relativePath === "/") {
    return await realpath(worktreeRoot);
  }

  // safeJoin throws PathOutsideWorktreeError for any unsafe input;
  // we let that bubble up unchanged so the route handler can map it
  // to a 400.
  const resolved = await safeJoin(worktreeRoot, relativePath);

  let st;
  try {
    st = await stat(resolved);
  } catch (err) {
    if (isErrnoException(err) && err.code === "ENOENT") {
      throw new NotFoundError(`path not found: ${relativePath}`);
    }
    throw err;
  }

  if (!st.isDirectory()) {
    throw new NotADirectoryError(`path is not a directory: ${relativePath}`);
  }

  return resolved;
}

/**
 * Build a TreeNode for one dirent. The dirent tells us what the entry
 * is as it sits on disk (file / dir / symlink). For symlinks we
 * realpath the target and check whether it lands inside the worktree:
 * inside → surface as target kind; outside → surface as opaque file.
 */
async function classifyChild(
  worktreeRoot: string,
  parentResolved: string,
  dirent: {
    name: string;
    isDirectory(): boolean;
    isFile(): boolean;
    isSymbolicLink(): boolean;
  },
  childRelative: string,
): Promise<TreeNode> {
  const absoluteChild = join(parentResolved, dirent.name);

  if (dirent.isSymbolicLink()) {
    return await classifySymlink(
      worktreeRoot,
      absoluteChild,
      dirent.name,
      childRelative,
    );
  }

  if (dirent.isDirectory()) {
    return {
      name: dirent.name,
      path: childRelative,
      kind: "directory",
      hasChildren: await directoryHasChildren(absoluteChild),
    };
  }

  return {
    name: dirent.name,
    path: childRelative,
    kind: "file",
    hasChildren: false,
  };
}

/**
 * Symlinks: surface inside-worktree targets as the target's kind;
 * outside-worktree targets as opaque files (kind: "file",
 * hasChildren: false). We use the project's own `safeJoin`-style
 * realpath check rather than calling safeJoin itself, because the
 * symlink lives at a known-good absolute path already; we just need
 * to know whether its target stays inside.
 */
async function classifySymlink(
  worktreeRoot: string,
  absoluteChild: string,
  name: string,
  childRelative: string,
): Promise<TreeNode> {
  const rootReal = await realpath(worktreeRoot);

  let targetReal: string;
  try {
    targetReal = await realpath(absoluteChild);
  } catch {
    // Broken / dangling symlink — surface as opaque file.
    return {
      name,
      path: childRelative,
      kind: "file",
      hasChildren: false,
    };
  }

  const isInside =
    targetReal === rootReal || targetReal.startsWith(rootReal + sep);

  if (!isInside) {
    // Symlink target is outside the worktree — opaque file.
    return {
      name,
      path: childRelative,
      kind: "file",
      hasChildren: false,
    };
  }

  // Inside the worktree — surface as the target's kind.
  let targetStat;
  try {
    targetStat = await stat(targetReal);
  } catch {
    return {
      name,
      path: childRelative,
      kind: "file",
      hasChildren: false,
    };
  }

  if (targetStat.isDirectory()) {
    return {
      name,
      path: childRelative,
      kind: "directory",
      hasChildren: await directoryHasChildren(targetReal),
    };
  }

  return {
    name,
    path: childRelative,
    kind: "file",
    hasChildren: false,
  };
}

/**
 * Returns `true` if `absoluteDir` contains at least one entry that
 * is NOT in the ignore list. Used to set `hasChildren` on directory
 * tree nodes so the UI knows whether to render an expand affordance.
 *
 * Cost: one extra `readdir` per directory child at the current level.
 * The MVP scope (TDD §13.6) accepts this; if it becomes a bottleneck
 * a future WP can substitute an opendir + first-entry sniff.
 */
async function directoryHasChildren(absoluteDir: string): Promise<boolean> {
  let names;
  try {
    names = await readdir(absoluteDir);
  } catch {
    // Permission denied / vanished between readdir-parent and this
    // call — treat as no children rather than failing the whole tree
    // request.
    return false;
  }
  return names.some((n) => !DEFAULT_IGNORE.has(n));
}

/**
 * Join a worktree-relative parent and a child name into a single
 * worktree-relative path with `/` as separator (wire shape is posix
 * regardless of host OS).
 */
function joinRelative(parent: string, childName: string): string {
  if (parent === "" || parent === "/") {
    return childName;
  }
  // Normalise the parent's separators to posix before joining so the
  // result is always `parent/child` with forward slashes.
  const parentPosix = parent.split(/[\\/]/).filter(Boolean).join("/");
  return posix.join(parentPosix, childName);
}

function isErrnoException(err: unknown): err is NodeJS.ErrnoException {
  return (
    err instanceof Error &&
    typeof (err as NodeJS.ErrnoException).code === "string"
  );
}
