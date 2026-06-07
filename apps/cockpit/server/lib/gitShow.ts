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
import { trailerValueFromMessage } from "./originAttribution/recorded";

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

// ─── WP-P09 — last-changing commit for a path (ADR-012) ──────────────────────
//
// `git log -1 -- <path>` reads the most-recent commit that touched a path —
// the input to origin correlation (who authored it, when, and the message). It
// is read-only (`git log` inspects history; it never mutates the tree or
// index), so it rides the SAME single git boundary as `git show` / `git diff`.
// Adding origin-inference here keeps the cockpit's "git lives in exactly one
// file" invariant intact (the read-only gate proves no git spawn elsewhere).

/** The last-changing commit for a path, as origin correlation consumes it. */
export interface GitLastCommit {
  /** Abbreviated commit sha. */
  sha: string;
  /** Author identity line: `Name <email>`. */
  author: string;
  /** Author timestamp, ISO 8601 (strict). */
  at: string;
  /** Full commit message — subject + body + trailers (for the run-id grep). */
  message: string;
}

export interface GitLogLastCommitOptions {
  /** Directory to invoke `git -C <cwd>` in — the worktree root. */
  cwd: string;
  /** Path within the repo, relative to its root. */
  relativePath: string;
  /** Override the default 5-second timeout (tests use a tiny value). */
  timeoutMs?: number;
}

// A record separator git itself never emits inside the fields — lets us split
// the four `%x1f`-joined fields unambiguously even when the message has tabs /
// newlines.
const FIELD_SEP = "\x1f";

/**
 * Run `git -C <cwd> log -1 --format=<sha|author|date|body> -- <relativePath>`
 * and parse the most-recent commit that changed `relativePath`.
 *
 * Returns `null` when the path has no commit history (a brand-new untracked
 * file, or a path absent from history) — fail-soft, so the caller maps it to
 * `unknown` rather than an error (DoD: "a file with no resolvable commit →
 * unknown"). Throws `TimeoutError` on timeout (the only hard failure).
 *
 * The args array is built EXPLICITLY (no string concat / interpolation into a
 * command line); `git`'s argv parser receives the path as a separate, structured
 * argument after `--`. `git log` is read-only.
 */
export async function gitLogLastCommit(
  opts: GitLogLastCommitOptions,
): Promise<GitLastCommit | null> {
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const args: string[] = [
    "-C",
    opts.cwd,
    "log",
    "-1",
    `--format=%h${FIELD_SEP}%an <%ae>${FIELD_SEP}%aI${FIELD_SEP}%B`,
    "--",
    opts.relativePath,
  ];

  const { exitCode, stdout, stderr } = await runGit(
    args,
    timeoutMs,
    `git log -1 (path=${opts.relativePath})`,
  );

  // A non-zero exit OR empty stdout both mean "no commit for this path". `git
  // log` exits 0 with empty output for an untracked path, and non-zero only for
  // a genuine error (e.g. not a repo) — either way the file has no resolvable
  // commit, which is the fail-soft `null` the caller turns into `unknown`. We
  // deliberately do NOT throw here (unlike git diff) because an unresolvable
  // path is an expected, normal condition for origin inference.
  const text = stdout.toString("utf8").trim();
  if (exitCode !== 0 || text === "") {
    void stderr; // kept for symmetry; not surfaced — null is the soft signal
    return null;
  }

  const [sha = "", author = "", at = "", message = ""] = text.split(FIELD_SEP);
  if (sha === "") return null;
  return { sha, author, at, message: message.trim() };
}

// ─── WP-P13 — read the recorded `Sulis-Origin:` trailer for a path (ADR-013) ──
//
// The recorded origin (WP-P12 stamps it as a commit trailer) is read back here
// through the SAME single git boundary as everything else — it reuses
// `gitLogLastCommit` (the read-only `git log -1`, which already returns the full
// message INCLUDING trailers), so NO new git spawn is added and the read-only
// gate stays green. This is the ONE site that knows how to pull a stamp off a
// commit; `RecordedOriginAttribution` calls it and maps the value to an Origin.

/** The recorded `Sulis-Origin:` stamp on a file's last-changing commit. */
export interface GitTrailerResult {
  /** Abbreviated sha of that commit (the sidecar key when the trailer is absent). */
  sha: string;
  /** The trailer value (everything after `Sulis-Origin:`), or null if absent. */
  originTrailer: string | null;
}

/**
 * Read the `Sulis-Origin:` trailer (if any) from a path's last-changing commit,
 * plus that commit's sha (so the caller can look up a sidecar keyed by sha when
 * the trailer is absent). Returns null when the path has no commit history.
 *
 * The trailer-shape parse lives in ONE place — `trailerValueFromMessage` in
 * `originAttribution/recorded.ts` (the module that owns the trailer key + parse,
 * EP-03). This site only fetches the commit message; it does not re-implement
 * the regex/key.
 *
 * Read-only — it composes `gitLogLastCommit` (the sanctioned `git log` read);
 * it spawns no new process. Fail-soft: a git failure throws `TimeoutError` only
 * (the caller treats any other failure as "no recorded origin").
 */
export async function gitOriginTrailer(
  opts: GitLogLastCommitOptions,
): Promise<GitTrailerResult | null> {
  const commit = await gitLogLastCommit(opts);
  if (commit === null) return null;
  return {
    sha: commit.sha,
    originTrailer: trailerValueFromMessage(commit.message),
  };
}
