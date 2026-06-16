// WP-011 — SulisChangeStarter: the deterministic server-side change-start.
//
// THE LESSON FROM WP-010, applied: start-from-intent's consequential act
// (creating a change) is a deterministic SERVER action, not an agent turn. The
// WP-010 agent-delegated mint ran 167s and created nothing; start-from-intent
// does NOT repeat that. This adapter invokes `sulis-change start` (+ `git clone`
// for the local-first FR-30 path) DIRECTLY via child_process — reliable, fast,
// observable.
//
// This is the THIRD sanctioned process-start site in the cockpit (after the
// SessionBridge prod adapter + the SpineEmitterMinter). The read-only gate's
// per-file process-start rule (2b) allow-lists THIS file by path; the
// orchestration lib (lib/discovery/startFromIntent.ts) depends only on the
// StartChangeRunner port and stays process-free.
//
// Process discipline (mirrors SpineEmitterMinter / SulisChangeStoreReader):
// execFile with a string[] argv (never a shell string), shell:false, a bounded
// timeout, SULIS_STATE_DIR honoured via env (the supported test/CI seam — so a
// temp state dir + temp repo drive a REAL change-start WITHOUT polluting the
// real ~/.sulis), and a typed failure on non-zero exit / timeout.
//
// The change-start landing stage is always `recon` (the script seeds it); the
// adapter maps `sulis-change start`'s JSON envelope onto the cockpit's `Change`
// shape so the board reads the new change exactly like any other.

import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

import type {
  StartChangeRunner,
  StartInput,
  StartResult,
  CloneInput,
  CloneResult,
} from "../ports/StartChangeRunner";
import { resolvePluginScriptsDir } from "./resolvePluginScripts";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { Change } from "../../shared/api-types";

/** The bounded budget for one `sulis-change start` / `git clone` call. */
const DEFAULT_TIMEOUT_MS = 30_000;

export interface SulisChangeStarterOptions {
  /** Absolute path to the `sulis-change` script (resolveSulisChangeScript by default). */
  scriptPath: string;
  /** The active state dir — the change lands under `<sulisStateDir>/changes`. */
  sulisStateDir: string;
  /** Per-call timeout (ms). Defaults to 30s. */
  timeoutMs?: number;
}

/** One captured exec result. */
interface ExecResult {
  ok: boolean;
  stdout: string;
  stderr: string;
}

export class SulisChangeStarter implements StartChangeRunner {
  private readonly scriptPath: string;
  private readonly sulisStateDir: string;
  private readonly timeoutMs: number;

  constructor(opts: SulisChangeStarterOptions) {
    this.scriptPath = opts.scriptPath;
    this.sulisStateDir = opts.sulisStateDir;
    this.timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  /**
   * LOCAL-FIRST (FR-30): clone an absent Project repo from its source before
   * starting. A clone failure ⇒ REPO_UNREACHABLE so the orchestrator starts NO
   * change (all-or-nothing). `git clone` is a non-mutating-porcelain verb (not
   * one of add/commit/reset/checkout), so the read-only gate's git-verb rule is
   * satisfied; this adapter is the sanctioned process-start site for it.
   */
  async clone(input: CloneInput): Promise<CloneResult> {
    const cloned = await this.exec(
      "git",
      ["clone", input.sourceRepo, input.targetPath],
      // cwd is irrelevant for a clone with absolute paths; use the state dir.
      this.sulisStateDir,
    );
    if (!cloned.ok || !existsSync(path.join(input.targetPath, ".git"))) {
      return {
        ok: false,
        code: "REPO_UNREACHABLE",
        message:
          "I couldn't get a copy of that repository — nothing was started.",
      };
    }
    return { ok: true, path: input.targetPath };
  }

  /**
   * Start a change via `sulis-change start` so it lands at Recon (FR-29). The
   * change record is written under `<sulisStateDir>/changes` (the env override
   * is honoured), so a temp state dir keeps the real brain clean.
   */
  async start(input: StartInput): Promise<StartResult> {
    if (!existsSync(this.scriptPath)) {
      return {
        ok: false,
        code: "START_FAILED",
        message: `sulis-change not found: ${this.scriptPath}`,
      };
    }
    const result = await this.exec(
      "python3",
      [
        this.scriptPath,
        "start",
        "--repo-root", input.repoRoot,
        "--primitive", input.primitive,
        "--slug", input.slug,
        "--intent", input.intent,
        "--base", "main",
      ],
      input.repoRoot,
    );
    if (!result.ok) {
      return {
        ok: false,
        code: "START_FAILED",
        message: `couldn't start the change: ${result.stderr.trim() || "(no detail)"}`,
      };
    }

    const change = parseStartedChange(result.stdout, input);
    if (change === null) {
      return {
        ok: false,
        code: "START_FAILED",
        message: "the change-start produced no recognisable result",
      };
    }
    return { ok: true, change };
  }

  /** execFile with a string[] argv (no shell), bounded timeout, captured I/O. */
  private exec(cmd: string, args: string[], cwd: string): Promise<ExecResult> {
    const env: NodeJS.ProcessEnv = {
      ...process.env,
      SULIS_STATE_DIR: this.sulisStateDir,
    };
    return new Promise((resolve) => {
      execFile(
        cmd,
        args,
        { cwd, timeout: this.timeoutMs, shell: false, env },
        (error, stdout, stderr) => {
          if (error) {
            resolve({ ok: false, stdout: stdout ?? "", stderr: stderr || String(error) });
            return;
          }
          resolve({ ok: true, stdout: stdout ?? "", stderr: stderr ?? "" });
        },
      );
    });
  }
}

// ─── pure helpers ────────────────────────────────────────────────────────────

/**
 * Map `sulis-change start`'s `{ok, data}` JSON envelope onto the cockpit's
 * `Change` shape. The script always seeds stage `recon`; the started change
 * carries the resolved primitive + slug. Returns null on a malformed envelope.
 */
function parseStartedChange(stdout: string, input: StartInput): Change | null {
  let parsed: {
    ok?: boolean;
    data?: {
      change_id?: string;
      handle?: string;
      branch?: string;
      primitive?: string;
      slug?: string;
      worktree_path?: string;
      base_branch?: string;
      base_sha?: string;
    };
  };
  try {
    parsed = JSON.parse(stdout);
  } catch {
    return null;
  }
  if (parsed.ok !== true || !parsed.data) return null;
  const d = parsed.data;
  if (typeof d.change_id !== "string" || typeof d.handle !== "string") return null;

  const now = new Date().toISOString().replace(/\.\d+Z$/, "Z");
  return {
    changeId: d.change_id,
    handle: d.handle,
    slug: typeof d.slug === "string" ? d.slug : input.slug,
    primitive: typeof d.primitive === "string" ? d.primitive : input.primitive,
    branch: typeof d.branch === "string" ? d.branch : `change/${input.primitive}-${input.slug}`,
    worktreePath: typeof d.worktree_path === "string" ? d.worktree_path : "",
    intent: input.intent,
    baseBranch: typeof d.base_branch === "string" ? d.base_branch : "main",
    baseSha: typeof d.base_sha === "string" && d.base_sha.length > 0 ? d.base_sha : null,
    createdAt: now,
    updatedAt: now,
    // The script seeds the initial stage as `recon` — the change lands there.
    stage: "recon",
    liveness: { status: "not-running" },
    // WP-001 placeholders for a just-started change: nothing waits on the
    // founder yet, health is honestly `unknown` ("too early to tell" at recon),
    // and the only recency is the create moment. WP-002 derives these on read.
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
    lastActivityAt: now,
  };
}

/**
 * Resolve the absolute `sulis-change` script path. Delegates the env-override →
 * in-repo → latest-plugin-cache search to the shared `resolvePluginScriptsDir`
 * (the 2-consumer primitive shared with SpineEmitterMinter), then joins the
 * script onto the resolved dir. Honours `SULIS_CHANGE_SCRIPT` (which may name
 * the scripts dir OR the script file). Returns "" when unresolved.
 */
export function resolveSulisChangeScript(): string {
  const dir = resolvePluginScriptsDir({
    scriptName: "sulis-change",
    envOverride: process.env.SULIS_CHANGE_SCRIPT,
  });
  if (dir === "") return "";
  return path.join(dir, "sulis-change");
}
