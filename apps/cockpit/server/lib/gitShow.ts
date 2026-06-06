// WP-008 — the single git boundary in the cockpit.
//
// The cockpit is **strictly read-only** across every data source
// (TDD §13.7, ADR-005). The only acceptable interaction with git is
// `git show <sha>:<path>` to retrieve historic file contents for the
// diff reader. THIS MODULE IS THE ONLY PLACE THAT SPAWNS `git`.
// Any new git call elsewhere violates the cockpit's read-only
// guarantee — the WP-001 CI grep enforces this invariant; if you find
// yourself needing another git operation, route it through here (or
// challenge the read-only constraint in an ADR).
//
// Subprocess hygiene (TDD §13.3, §13.6):
//   - `spawn` (not `exec`), `args: string[]` (not a string command
//     line), `shell: false` — no shell expansion, no string concat,
//     no opportunity for argument injection.
//   - Hard timeout (default 5s); the child is SIGKILLed on timeout;
//     `TimeoutError` is thrown so callers can surface a clean error
//     rather than a generic 500.
//   - stdout captured as `Buffer` (NOT string) so the caller can run
//     binary detection on the raw bytes; stderr captured as utf-8
//     string for the caller's pattern-matching.
//
// `git show` is itself read-only (no working-tree or index mutation),
// so the choice is safe with respect to the read-only constraint.

import { spawn } from "node:child_process";

import { GitError, TimeoutError } from "./errors";

/** Default subprocess timeout. TDD §13.6 mandates a 5-second bound. */
const DEFAULT_TIMEOUT_MS = 5_000;

/** Raw result of one `git` invocation: exit code + captured streams. */
interface RunGitResult {
  /** Child's exit code; 0 on success, non-zero on git error. */
  exitCode: number;
  /** Raw stdout bytes — caller decides whether to UTF-8 decode. */
  stdout: Buffer;
  /** UTF-8-decoded stderr — caller pattern-matches it. */
  stderr: string;
}

/**
 * The single low-level `git` spawn site for the cockpit. Every git
 * boundary in this module (`gitShow`, `gitDiffNameStatus`,
 * `gitDiffNumstat`) routes through here so the subprocess-hygiene
 * invariants (TDD §13.3, §13.6) are written once:
 *   - `spawn` (not `exec`), `args: string[]`, `shell: false` — no shell
 *     expansion, no string concatenation, no argument-injection surface.
 *   - hard timeout; the child is SIGKILLed and `TimeoutError` thrown.
 *   - stdout captured as `Buffer` (binary-safe); stderr as utf-8 string.
 *
 * Does NOT throw on non-zero exit — that decision belongs to the caller
 * (some non-zero exits are expected, e.g. `git show` of a path absent at
 * the base commit). `label` is used only in the TimeoutError message.
 */
function runGit(
  args: string[],
  timeoutMs: number,
  label: string,
): Promise<RunGitResult> {
  return new Promise<RunGitResult>((resolve, reject) => {
    const child = spawn("git", args, {
      // shell:false is the explicit defence-in-depth — Node defaults
      // to false for spawn(), but writing it here keeps the invariant
      // visible to readers and to the gitShow.test.ts grep guard.
      shell: false,
    });

    const stdoutChunks: Buffer[] = [];
    let stderrText = "";
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      // SIGKILL — git is a well-behaved child but we don't want to
      // depend on it honouring SIGTERM, and the cockpit's HTTP surface
      // needs a hard upper bound on response latency.
      child.kill("SIGKILL");
      reject(new TimeoutError(`${label} timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    child.stdout.on("data", (chunk: Buffer) => {
      stdoutChunks.push(chunk);
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderrText += chunk.toString("utf8");
    });

    child.on("error", (err) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      reject(err);
    });

    child.on("close", (code) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      resolve({
        exitCode: code ?? -1,
        stdout: Buffer.concat(stdoutChunks),
        stderr: stderrText,
      });
    });
  });
}

export interface GitShowOptions {
  /** Directory to invoke `git -C <cwd>` in — the worktree root. */
  cwd: string;
  /** Commit-ish to read from. Callers validate shape (40-char-ish hex). */
  sha: string;
  /** Path within the repo, relative to its root. */
  relativePath: string;
  /** Override the default 5-second timeout (tests use a tiny value). */
  timeoutMs?: number;
}

export interface GitShowResult {
  /** Child's exit code; 0 on success, non-zero on git error. */
  exitCode: number;
  /** Raw stdout bytes — caller decides whether to UTF-8 decode. */
  stdout: Buffer;
  /** UTF-8-decoded stderr — caller pattern-matches for "not in <sha>" etc. */
  stderr: string;
}

/**
 * Run `git -C <cwd> show <sha>:<relativePath>` and return the child's
 * exit code + captured stdout (Buffer) + stderr (string).
 *
 * Does NOT throw on non-zero exit — the caller (`readFileDiff`)
 * pattern-matches stderr to distinguish "file did not exist at this
 * sha" (mapped to `base: null`) from a genuine git error (mapped to
 * `GitError`).
 *
 * Throws `TimeoutError` if the child exceeds `timeoutMs`. The child
 * is SIGKILLed before the rejection so no zombie process remains.
 */
export async function gitShow(opts: GitShowOptions): Promise<GitShowResult> {
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  // Build the args array EXPLICITLY — every value is a literal or a
  // sanitised input. No string concatenation, no template interpolation
  // into a command line. `git`'s argv parser receives sha and path as
  // separate, structured arguments inside the show selector
  // `<sha>:<path>` (which git itself parses, not a shell).
  const args: string[] = [
    "-C",
    opts.cwd,
    "show",
    `${opts.sha}:${opts.relativePath}`,
  ];

  const { exitCode, stdout, stderr } = await runGit(
    args,
    timeoutMs,
    `git show (sha=${opts.sha} path=${opts.relativePath})`,
  );
  return { exitCode, stdout, stderr };
}

// ─── WP-P02 — per-file diff data for the changed-files set (ADR-010) ──────────
//
// Both helpers below run `git diff <baseSha> --` against the worktree
// (the base commit → working tree), through the same `runGit` spawn
// site as `gitShow`. `git diff` is read-only — it inspects the index +
// working tree, never mutates either — so it is safe under the cockpit's
// read-only guarantee (TDD §13.7, ADR-003/010). Both throw `GitError`
// on a non-zero exit and `TimeoutError` on timeout.

/** One name-status entry from `git diff --name-status <baseSha>`. */
export interface GitDiffNameStatusEntry {
  /** Path relative to the repo root. */
  path: string;
  /** Worded status; A → new, M → edited, D → removed (others map to edited). */
  status: "new" | "edited" | "removed";
}

export interface GitDiffOptions {
  /** Directory to invoke `git -C <cwd>` in — the worktree root. */
  cwd: string;
  /** The base commit-ish to diff the worktree against. */
  baseSha: string;
  /** Override the default 5-second timeout (tests use a tiny value). */
  timeoutMs?: number;
}

/**
 * Run `git -C <cwd> diff --name-status --no-renames <baseSha> --` and
 * parse each `\t`-separated `status\tpath` line into a worded
 * `{ path, status }`. `--no-renames` keeps the output to single-path
 * lines (a rename would otherwise emit `R100\told\tnew`).
 *
 * Throws `GitError` on a non-zero exit; `TimeoutError` on timeout.
 */
export async function gitDiffNameStatus(
  opts: GitDiffOptions,
): Promise<GitDiffNameStatusEntry[]> {
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const args: string[] = [
    "-C",
    opts.cwd,
    "diff",
    "--name-status",
    "--no-renames",
    opts.baseSha,
    "--",
  ];

  const { exitCode, stdout, stderr } = await runGit(
    args,
    timeoutMs,
    `git diff --name-status (sha=${opts.baseSha})`,
  );
  if (exitCode !== 0) {
    throw new GitError(
      `git diff --name-status failed (exitCode=${exitCode}, sha=${opts.baseSha}): ${stderr.trim()}`,
    );
  }

  const entries: GitDiffNameStatusEntry[] = [];
  for (const line of stdout.toString("utf8").split("\n")) {
    if (line === "") {
      continue;
    }
    // `status\tpath` — the status column may carry a score suffix we
    // don't need (e.g. `M100`); only its first letter matters here.
    const tab = line.indexOf("\t");
    if (tab === -1) {
      continue;
    }
    const code = line.slice(0, tab).charAt(0);
    const path = line.slice(tab + 1);
    entries.push({ path, status: wordStatus(code) });
  }
  return entries;
}

/** Map a git status letter to the wire's worded status. */
function wordStatus(code: string): GitDiffNameStatusEntry["status"] {
  if (code === "A") {
    return "new";
  }
  if (code === "D") {
    return "removed";
  }
  // M (modified), and any other change (T type-change, etc.) read as an
  // edit for the UI's purposes.
  return "edited";
}

/** One numstat entry: added/removed line counts (null = binary). */
export interface GitDiffNumstatEntry {
  /** Path relative to the repo root. */
  path: string;
  /** Added lines; null when git reported the file as binary (`-`). */
  added: number | null;
  /** Removed lines; null when git reported the file as binary (`-`). */
  removed: number | null;
}

/**
 * Run `git -C <cwd> diff --numstat --no-renames <baseSha> --` and parse
 * each `\t`-separated `added\tremoved\tpath` line. Git emits `-` in both
 * count columns for a binary file; that maps to `{ added: null,
 * removed: null }`. `--no-renames` keeps each line to a single path.
 *
 * Returns `[]` for an empty diff. Throws `GitError` on a non-zero exit;
 * `TimeoutError` on timeout.
 */
export async function gitDiffNumstat(
  opts: GitDiffOptions,
): Promise<GitDiffNumstatEntry[]> {
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const args: string[] = [
    "-C",
    opts.cwd,
    "diff",
    "--numstat",
    "--no-renames",
    opts.baseSha,
    "--",
  ];

  const { exitCode, stdout, stderr } = await runGit(
    args,
    timeoutMs,
    `git diff --numstat (sha=${opts.baseSha})`,
  );
  if (exitCode !== 0) {
    throw new GitError(
      `git diff --numstat failed (exitCode=${exitCode}, sha=${opts.baseSha}): ${stderr.trim()}`,
    );
  }

  const entries: GitDiffNumstatEntry[] = [];
  for (const line of stdout.toString("utf8").split("\n")) {
    if (line === "") {
      continue;
    }
    // `added\tremoved\tpath`. The path may itself contain no tabs (we
    // pass --no-renames, so there is exactly one path column), so split
    // on the first two tabs and keep the remainder as the path.
    const firstTab = line.indexOf("\t");
    const secondTab = line.indexOf("\t", firstTab + 1);
    if (firstTab === -1 || secondTab === -1) {
      continue;
    }
    const addedRaw = line.slice(0, firstTab);
    const removedRaw = line.slice(firstTab + 1, secondTab);
    const path = line.slice(secondTab + 1);
    // A `-` in EITHER count column signals a binary file; git emits
    // `-\t-` for binaries. Treat either `-` as the binary signal and
    // null BOTH counts so the wire shape is unambiguous.
    const binary = addedRaw === "-" || removedRaw === "-";
    entries.push({
      path,
      added: binary ? null : Number.parseInt(addedRaw, 10),
      removed: binary ? null : Number.parseInt(removedRaw, 10),
    });
  }
  return entries;
}
