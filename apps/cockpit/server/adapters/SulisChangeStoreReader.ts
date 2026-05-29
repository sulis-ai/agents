// WP-003 — SulisChangeStoreReader: the cockpit's one in-tree adapter
// over the change store (TDD §2.3, §9, §13.3; ADR-008).
//
// CONTRACT (the prose form of TDD §13.3):
//   - Shells out via child_process.spawn — never exec, never execSync,
//     never execFile.
//   - Arguments are passed as a `string[]` to spawn — never concatenated
//     into a command line; never wrapped by a shell.
//   - The spawn options pass shell=false explicitly (no shell wrapping).
//     The shell-true option is never set anywhere in this file —
//     the contract test inventory-greps for that string and the grep
//     must return zero matches in active code.
//   - A configurable per-call timeout (default 5000ms per TDD §13.6)
//     is enforced by setTimeout + child.kill(); on timeout the typed
//     error reports code "TIMEOUT".
//   - Non-zero exit → ChangeStoreReaderError with code "EXEC_FAIL"
//     carrying the captured stderr and exit code.
//   - JSON parse failure on stdout → ChangeStoreReaderError with code
//     "PARSE_ERROR" carrying the raw stdout slice.
//   - snake_case fields from the Python helper are translated to
//     camelCase via one shared helper function (no inline translation
//     scattered across the methods — DRY per TDD §12 / EP-03).
//
// This file is the ONE place inside apps/cockpit/ that imports from
// node:child_process. The contract test inventory-greps it to confirm
// that.

import { spawn } from "node:child_process";

import type {
  ChangeStoreReader,
  ChangeStoreRecord,
  WorkflowStage,
} from "../ports/ChangeStoreReader";

// ─── Typed error ───────────────────────────────────────────────────────

export type ChangeStoreReaderErrorCode = "EXEC_FAIL" | "TIMEOUT" | "PARSE_ERROR";

/**
 * Single typed error class for every failure mode the adapter can
 * surface. Code-on-the-instance keeps `instanceof` narrow-able and
 * lets route handlers translate to HTTP status without instanceof
 * chains.
 */
export class ChangeStoreReaderError extends Error {
  readonly code: ChangeStoreReaderErrorCode;
  readonly stderr: string;
  readonly exitCode: number | null;

  constructor(
    code: ChangeStoreReaderErrorCode,
    message: string,
    opts: { stderr?: string; exitCode?: number | null } = {},
  ) {
    super(message);
    this.name = "ChangeStoreReaderError";
    this.code = code;
    this.stderr = opts.stderr ?? "";
    this.exitCode = opts.exitCode ?? null;
  }
}

// ─── Config ────────────────────────────────────────────────────────────

export type SulisChangeStoreReaderConfig = {
  /** Absolute path to the sulis-list-changes helper (WP-002). */
  helperPath: string;
  /**
   * Override for `~/.sulis` resolution; honoured by the helper.
   * Defaults to the helper's own resolution (which reads SULIS_STATE_DIR
   * from the spawned process's env if set, else falls back to `~/.sulis`).
   */
  sulisStateDir?: string;
  /** Per-call timeout in ms. Defaults to 5000 (TDD §13.6). */
  timeoutMs?: number;
};

const DEFAULT_TIMEOUT_MS = 5000;

// Change IDs are ULIDs (Crockford base32, 26 chars). The store also
// tolerates legacy hex / underscore forms. The validator below is
// deliberately permissive (alphanumerics + underscore + hyphen): tight
// enough to refuse `..`, `/`, glob chars, and shell metacharacters, but
// not tight enough to second-guess the store's id scheme. Defense-in-
// depth — the spawn-with-argv-array path already prevents shell
// injection; this rejects path-traversal shapes before the Python
// helper has to.
const CHANGE_ID_PATTERN = /^[A-Za-z0-9_-]+$/;

// ─── snake_case → camelCase translation (shared by all methods) ────────

/**
 * Translate one persisted change record (snake_case as written by
 * `_change_state.py`) into the camelCase shape consumers see. Centralised
 * here so adding a field is one edit, not three.
 *
 * `updated_at` is sourced from the state.json overlay when the helper
 * writes one; the helper currently overlays only `stage`, not
 * `updated_at`, so we fall back to `created_at` for now. A future
 * helper change can extend this without altering the consumer shape.
 */
type RawChangeRecord = {
  change_id?: unknown;
  handle?: unknown;
  slug?: unknown;
  primitive?: unknown;
  branch?: unknown;
  worktree_path?: unknown;
  intent?: unknown;
  base_branch?: unknown;
  base_sha?: unknown;
  shipped_sha?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
  stage?: unknown;
};

function toRecord(raw: RawChangeRecord): ChangeStoreRecord {
  const str = (v: unknown, fallback = ""): string =>
    typeof v === "string" ? v : fallback;
  const strOrNull = (v: unknown): string | null =>
    typeof v === "string" && v.length > 0 ? v : null;

  const createdAt = str(raw.created_at);
  const updatedAt = str(raw.updated_at, createdAt);

  return {
    changeId: str(raw.change_id),
    handle: str(raw.handle),
    slug: str(raw.slug),
    primitive: str(raw.primitive),
    branch: str(raw.branch),
    worktreePath: str(raw.worktree_path),
    intent: str(raw.intent),
    baseBranch: str(raw.base_branch),
    baseSha: strOrNull(raw.base_sha),
    // WP-004: the pin a tidied shipped change's worktree is recreated
    // from (ADR-004). Same null-on-absent shape as base_sha.
    shippedSha: strOrNull(raw.shipped_sha),
    createdAt,
    updatedAt,
    stage: str(raw.stage, "recon") as WorkflowStage,
  };
}

// ─── The adapter ───────────────────────────────────────────────────────

export class SulisChangeStoreReader implements ChangeStoreReader {
  private readonly helperPath: string;
  private readonly sulisStateDir: string | undefined;
  private readonly timeoutMs: number;

  constructor(config: SulisChangeStoreReaderConfig) {
    this.helperPath = config.helperPath;
    this.sulisStateDir = config.sulisStateDir;
    this.timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  async listAllChanges(): Promise<ChangeStoreRecord[]> {
    const payload = await this.runHelper(["list"]);
    if (!Array.isArray(payload)) {
      throw new ChangeStoreReaderError(
        "PARSE_ERROR",
        "expected JSON array from 'list', got: " + typeof payload,
      );
    }
    return payload.map((row) => toRecord(row as RawChangeRecord));
  }

  async readChangeRecord(changeId: string): Promise<ChangeStoreRecord | null> {
    if (!CHANGE_ID_PATTERN.test(changeId)) {
      // Reject path-traversal-shaped ids before they reach the helper.
      // A clean `null` here mirrors the "unknown id" branch — the
      // contract test asserts unknown ids return null, and an
      // unparseable id is, by definition, unknown.
      return null;
    }
    // The Python helper's `get` returns the raw change.json without
    // the state.json overlay (only `list` overlays). Apply the overlay
    // here so callers see the same live stage they'd get from
    // listAllChanges() for the same id — parity is part of the
    // contract.
    //
    // The two helper invocations are independent (one reads change.json,
    // the other reads state.json) so we run them in parallel. For a
    // single-record fetch this halves the wall-clock; for a chain of
    // calls the savings compound.
    const [payload, overlay] = await Promise.all([
      this.runHelper(["get", changeId]),
      this.readStageOverlay(changeId),
    ]);
    if (payload === null) {
      return null;
    }
    const record = toRecord(payload as RawChangeRecord);
    if (overlay !== null) {
      record.stage = overlay;
    }
    return record;
  }

  async readChangeStage(changeId: string): Promise<WorkflowStage | null> {
    if (!CHANGE_ID_PATTERN.test(changeId)) {
      return null;
    }
    // Same composition as readChangeRecord: state.json overlay first,
    // then fall back to change.json's seed stage. The contract requires
    // parity with listAllChanges, which overlays-then-falls-back.
    const overlay = await this.readStageOverlay(changeId);
    if (overlay !== null) {
      return overlay;
    }
    const payload = await this.runHelper(["get", changeId]);
    if (payload === null) {
      return null;
    }
    const seed = (payload as RawChangeRecord).stage;
    return typeof seed === "string" && seed.length > 0
      ? (seed as WorkflowStage)
      : null;
  }

  /**
   * Helper for the overlay-then-fallback composition used by
   * `readChangeRecord` and `readChangeStage`. Returns the state.json
   * stage when present, else null.
   */
  private async readStageOverlay(
    changeId: string,
  ): Promise<WorkflowStage | null> {
    const payload = await this.runHelper(["stage", changeId]);
    if (payload === null) {
      return null;
    }
    if (typeof payload !== "string") {
      throw new ChangeStoreReaderError(
        "PARSE_ERROR",
        "expected JSON string from 'stage', got: " + typeof payload,
      );
    }
    return payload as WorkflowStage;
  }

  /**
   * Spawn the helper with the given subcommand args, honour the per-
   * call timeout, parse stdout as JSON. The single seam through which
   * every method talks to the helper — failure modes are typed and
   * funneled here.
   *
   * Per TDD §13.3:
   *   - `spawn(helperPath, args, { env, shell: false })` — args[] only.
   *   - No string concatenation of arguments into a command line.
   *   - Hard timeout via setTimeout + child.kill().
   */
  private runHelper(args: string[]): Promise<unknown> {
    return new Promise((resolve, reject) => {
      // Inherit the parent env so PATH, HOME, etc. flow through; then
      // overlay SULIS_STATE_DIR if the constructor was given one. The
      // overlay is the supported test seam (`_change_state.sulis_state_base`
      // honours SULIS_STATE_DIR identically).
      const env: NodeJS.ProcessEnv = { ...process.env };
      if (this.sulisStateDir !== undefined) {
        env.SULIS_STATE_DIR = this.sulisStateDir;
      }

      const child = spawn(this.helperPath, args, {
        env,
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
      });

      const stdoutChunks: Buffer[] = [];
      const stderrChunks: Buffer[] = [];
      let settled = false;

      const settleReject = (err: ChangeStoreReaderError): void => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        try {
          // Best-effort: kill the child if it's still running. SIGTERM
          // is the convention; the timeout path uses SIGKILL because
          // the helper has already proven unresponsive.
          if (!child.killed) {
            child.kill("SIGTERM");
          }
        } catch {
          // ignore — process may already be dead.
        }
        reject(err);
      };

      const settleResolve = (payload: unknown): void => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(payload);
      };

      const timer = setTimeout(() => {
        try {
          if (!child.killed) {
            // SIGKILL — the helper exceeded its budget; harvest the
            // pid immediately rather than negotiate a graceful exit.
            child.kill("SIGKILL");
          }
        } catch {
          // ignore
        }
        settleReject(
          new ChangeStoreReaderError(
            "TIMEOUT",
            `helper exceeded ${this.timeoutMs}ms timeout: ${this.helperPath} ${args.join(" ")}`,
          ),
        );
      }, this.timeoutMs);

      child.on("error", (err) => {
        // ENOENT / EACCES / etc. — spawn itself failed.
        settleReject(
          new ChangeStoreReaderError(
            "EXEC_FAIL",
            `failed to spawn helper: ${err.message}`,
          ),
        );
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
          settleReject(
            new ChangeStoreReaderError(
              "EXEC_FAIL",
              `helper exited with code ${code}: ${stderr.trim() || "(no stderr)"}`,
              { stderr, exitCode: code },
            ),
          );
          return;
        }
        let parsed: unknown;
        try {
          parsed = JSON.parse(stdout);
        } catch (err) {
          settleReject(
            new ChangeStoreReaderError(
              "PARSE_ERROR",
              `failed to parse helper JSON: ${(err as Error).message}; stdout=${stdout.slice(0, 200)}`,
              { stderr, exitCode: code },
            ),
          );
          return;
        }
        settleResolve(parsed);
      });
    });
  }
}
