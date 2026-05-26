// WP-005 — Liveness probe (TDD §8, §14.4; ADR-005).
//
// Reads the per-change session.json under {sulisStateDir}/changes/{id}/
// and asks the kernel whether the recorded pid still exists. The probe
// uses `process.kill(pid, 0)` — quoting ADR-005 verbatim:
//
//   "A probe with signal 0 sends no actual signal; it just asks the
//    kernel 'does this pid exist and could I signal it?' The running
//    claude is undisturbed."
//
// Side-effect-free. No signals sent. No files written. No subprocesses.

import { promises as fs } from "node:fs";
import path from "node:path";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { Liveness } from "../../shared/api-types";

export type SessionJson = {
  change_id: string;
  pid: number | null;
  pid_kind: "session" | "terminal" | null;
  script_path: string;
  spawned_at: string;
  terminal_app_used?: string;
  tty?: string;
};

type ProbeResult = Liveness & { pidKind?: SessionJson["pid_kind"] };

/**
 * Reads `{sulisStateDir}/changes/{changeId}/session.json` and probes
 * the recorded pid with signal 0 per ADR-005. Returns a `Liveness`
 * shape (TDD §5.1) extended with the optional `pidKind` so callers
 * can flag the terminal-pid ambiguity (TDD §14.4).
 *
 * Behaviour matrix:
 *   - session.json missing            → unknown / "no session record"
 *   - session.json malformed JSON     → unknown / "malformed session record"
 *   - pid === null                    → unknown / "no pid recorded"
 *   - process.kill(pid, 0) no throw   → running, pid
 *   - throws ESRCH                    → not-running
 *   - throws EPERM                    → running, pid    // exists; cannot signal
 *   - throws anything else            → unknown / err.code ?? "probe failed"
 *
 * Side-effect-free. No signals sent. No files written. No subprocesses.
 */
export async function probeLiveness(
  sulisStateDir: string,
  changeId: string,
): Promise<ProbeResult> {
  const sessionPath = path.join(
    sulisStateDir,
    "changes",
    changeId,
    "session.json",
  );

  let raw: string;
  try {
    raw = await fs.readFile(sessionPath, "utf8");
  } catch {
    return { status: "unknown", reason: "no session record" };
  }

  let parsed: SessionJson;
  try {
    parsed = JSON.parse(raw) as SessionJson;
  } catch {
    return { status: "unknown", reason: "malformed session record" };
  }

  const pid = parsed.pid;
  if (pid === null || pid === undefined) {
    return { status: "unknown", reason: "no pid recorded" };
  }

  const withPidKind = (base: ProbeResult): ProbeResult =>
    parsed.pid_kind ? { ...base, pidKind: parsed.pid_kind } : base;

  try {
    // Signal 0 — POSIX existence probe. Sends nothing. ADR-005.
    process.kill(pid, 0);
    return withPidKind({ status: "running", pid });
  } catch (err) {
    const code = (err as NodeJS.ErrnoException).code;
    if (code === "ESRCH") {
      return { status: "not-running" };
    }
    if (code === "EPERM") {
      // Process exists; we lack permission to signal it. For our
      // purposes that still counts as "alive" per ADR-005.
      return withPidKind({ status: "running", pid });
    }
    return {
      status: "unknown",
      reason: code ?? "probe failed",
    };
  }
}
