// WP-004 — SulisChangeRecreator: the production RecreateRunner adapter
// (TDD §3, §5; ADR-001/004).
//
// Composes the already-shipped `sulis-change recreate --change-id
// <changeId>` CLI to re-materialise a tidied change's worktree. It does
// NOT re-implement worktree materialisation — `cmd_recreate` (#56) already
// attaches to the branch if it still exists, else checks out detached at
// `shipped_sha`, and is idempotent ("worktree already exists" → no-op
// success). This adapter only drives it.
//
// The seam is keyed by the UNIQUE `change_id`, not the non-unique 6-char
// handle (ADR-001 — the `--change-id` selector WP-001 added). The cockpit
// reads the record by its id and carries that id straight across the seam,
// so the recreate resolves the exact change rather than re-resolving a
// collision-prone handle.
//
// CONTRACT (the cockpit's subprocess discipline — TDD §3, mirrors
// SulisChangeStoreReader / gitShow):
//   - child_process.spawn — never exec, never execSync, never execFile.
//   - Arguments are an argv `string[]` — never concatenated into a
//     command line, never shell-wrapped. `shell: false` is set
//     explicitly (the recreate-on-demand source-hygiene test greps for
//     the absence of `shell: true`).
//   - The change_id is SHAPE-GUARDED (`isSafeChangeHandle`) before the
//     spawn — defence-in-depth against a corrupt record carrying a
//     leading-hyphen (argparse flag-confusion) or traversal/glob shape. A
//     malformed id degrades to a typed SPAWN_FAIL, never a spawn.
//   - The ONLY subcommand is `recreate` (the source-hygiene test asserts
//     no mutating git verb token — add/commit/reset/checkout — appears,
//     keeping read-only-gate parity).
//   - A bounded per-call timeout (default 30000ms — recreate does git
//     I/O, so its budget is larger than the 5s read-path budget) is
//     enforced by setTimeout + child.kill("SIGKILL"); on timeout the
//     typed outcome reports reason "TIMEOUT".
//   - Non-zero exit → { ok: false, reason: "EXEC_FAIL" } with stderr.
//   - spawn error (ENOENT / EACCES) → { ok: false, reason: "SPAWN_FAIL" }.
//   - Clean exit → { ok: true, alreadyPresent } — alreadyPresent sniffed
//     from the CLI's idempotent marker on stdout/stderr (defaults false).
//
// It NEVER throws across the seam: every failure is a typed
// RecreateOutcome so the serving path degrades to a plain note rather
// than hanging or 500-ing a request (TDD §3 bounded recreate).

import { spawn } from "node:child_process";

import { isSafeChangeHandle } from "../lib/changeHandleGuard";
import type { RecreateOutcome, RecreateRunner } from "../ports/RecreateRunner";

export type SulisChangeRecreatorConfig = {
  /**
   * Path (or bare name resolved on PATH) of the `sulis-change` CLI.
   * Defaults to `"sulis-change"` (resolved on the spawned process PATH).
   */
  binPath?: string;
  /** Per-call timeout in ms. Defaults to 30000 (recreate does git I/O). */
  timeoutMs?: number;
};

const DEFAULT_BIN = "sulis-change";
const DEFAULT_TIMEOUT_MS = 30_000;

// The `sulis-change recreate` idempotent path prints an "already exists"
// notice on a clean exit. We sniff for it to set `alreadyPresent`; a miss
// just defaults to false (a fresh materialisation), which is safe — the
// resolver treats both as success.
const ALREADY_PRESENT_MARKER = /already\s+exists/i;

export class SulisChangeRecreator implements RecreateRunner {
  private readonly binPath: string;
  private readonly timeoutMs: number;

  constructor(config: SulisChangeRecreatorConfig = {}) {
    this.binPath = config.binPath ?? DEFAULT_BIN;
    this.timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  recreate(changeId: string): Promise<RecreateOutcome> {
    // Shape-guard the id BEFORE the spawn (defence-in-depth — a corrupt
    // record could carry a leading-hyphen flag-confusion shape or a
    // traversal/glob/metachar id). The guard's charset already matches the
    // ULID; a malformed id degrades to a typed failure, never a spawn.
    if (!isSafeChangeHandle(changeId)) {
      return Promise.resolve({
        ok: false,
        reason: "SPAWN_FAIL",
        detail: `refused to recreate: unsafe change_id ${JSON.stringify(changeId)}`,
      });
    }

    // argv array ONLY — no string command line, no shell. The change_id is
    // a structured argument the CLI parses, not a shell would.
    const args: string[] = ["recreate", "--change-id", changeId];

    return new Promise<RecreateOutcome>((resolve) => {
      const child = spawn(this.binPath, args, {
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
      });

      const stdoutChunks: Buffer[] = [];
      const stderrChunks: Buffer[] = [];
      let settled = false;

      const settle = (outcome: RecreateOutcome): void => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(outcome);
      };

      const timer = setTimeout(() => {
        try {
          if (!child.killed) {
            // SIGKILL — recreate blew its budget; harvest the pid hard
            // rather than negotiate a graceful exit. The cockpit's HTTP
            // surface needs a firm upper bound on response latency.
            child.kill("SIGKILL");
          }
        } catch {
          // ignore — process may already be dead.
        }
        settle({
          ok: false,
          reason: "TIMEOUT",
          detail: `recreate exceeded ${this.timeoutMs}ms timeout: ${this.binPath} ${args.join(" ")}`,
        });
      }, this.timeoutMs);

      child.on("error", (err) => {
        // ENOENT / EACCES — spawn itself failed (the CLI is missing or
        // not executable).
        settle({
          ok: false,
          reason: "SPAWN_FAIL",
          detail: `failed to spawn recreate: ${err.message}`,
        });
      });

      child.stdout?.on("data", (chunk: Buffer) => {
        stdoutChunks.push(chunk);
      });
      child.stderr?.on("data", (chunk: Buffer) => {
        stderrChunks.push(chunk);
      });

      child.on("close", (code) => {
        if (settled) return;
        const stdout = Buffer.concat(stdoutChunks).toString("utf8");
        const stderr = Buffer.concat(stderrChunks).toString("utf8");
        if (code !== 0) {
          settle({
            ok: false,
            reason: "EXEC_FAIL",
            detail: `recreate exited with code ${code}: ${stderr.trim() || "(no stderr)"}`,
          });
          return;
        }
        const alreadyPresent =
          ALREADY_PRESENT_MARKER.test(stdout) ||
          ALREADY_PRESENT_MARKER.test(stderr);
        settle({ ok: true, alreadyPresent });
      });
    });
  }
}
