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

import { TimeoutError } from "./errors";

/** Default subprocess timeout. TDD §13.6 mandates a 5-second bound. */
const DEFAULT_TIMEOUT_MS = 5_000;

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
export function gitShow(opts: GitShowOptions): Promise<GitShowResult> {
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

  return new Promise<GitShowResult>((resolve, reject) => {
    const child = spawn("git", args, {
      // shell:false is the explicit defence-in-depth — Node defaults
      // to false for spawn(), but writing it here keeps the invariant
      // visible to readers and to the gitShow.test.ts grep guard.
      shell: false,
      // stdio is the default; we capture stdout/stderr below.
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
      reject(
        new TimeoutError(
          `git show timed out after ${timeoutMs}ms (sha=${opts.sha} path=${opts.relativePath})`,
        ),
      );
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
