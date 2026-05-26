// WP-005 — probeLiveness behaviour matrix (TDD §8, §14.4; ADR-005).
//
// All cases use real temp directories and (where needed) real spawned
// processes, so the test exercises the actual POSIX path. The probe
// MUST send no signals (signal 0 only). To enforce that, the test
// monkey-patches `process.kill` and asserts every call uses `0`.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawnSync } from "node:child_process";

import { probeLiveness } from "../lib/probeLiveness";

function mkStateDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "wp005-state-"));
}

function writeSessionJson(
  stateDir: string,
  changeId: string,
  payload: unknown | string,
): void {
  const dir = path.join(stateDir, "changes", changeId);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, "session.json");
  if (typeof payload === "string") {
    fs.writeFileSync(file, payload, "utf8");
  } else {
    fs.writeFileSync(file, JSON.stringify(payload), "utf8");
  }
}

describe("probeLiveness — TDD §8 behaviour matrix", () => {
  let stateDir: string;
  const changeId = "01TESTCHANGE";

  beforeEach(() => {
    stateDir = mkStateDir();
  });

  afterEach(() => {
    fs.rmSync(stateDir, { recursive: true, force: true });
  });

  it("returns unknown/no-session-record when session.json is missing", async () => {
    const result = await probeLiveness(stateDir, changeId);
    expect(result).toEqual({
      status: "unknown",
      reason: "no session record",
    });
  });

  it("returns unknown/malformed-session-record when JSON is invalid", async () => {
    writeSessionJson(stateDir, changeId, "{ not json");
    const result = await probeLiveness(stateDir, changeId);
    expect(result).toEqual({
      status: "unknown",
      reason: "malformed session record",
    });
  });

  it("returns unknown/no-pid-recorded when pid is null", async () => {
    writeSessionJson(stateDir, changeId, {
      change_id: changeId,
      pid: null,
      pid_kind: null,
      script_path: "/tmp/launch.sh",
      spawned_at: "2026-05-26T14:14:06Z",
    });
    const result = await probeLiveness(stateDir, changeId);
    expect(result).toEqual({
      status: "unknown",
      reason: "no pid recorded",
    });
  });

  it("returns running with pid when the pid is alive (process.pid)", async () => {
    writeSessionJson(stateDir, changeId, {
      change_id: changeId,
      pid: process.pid,
      pid_kind: "session",
      script_path: "/tmp/launch.sh",
      spawned_at: "2026-05-26T14:14:06Z",
    });
    const result = await probeLiveness(stateDir, changeId);
    expect(result.status).toBe("running");
    if (result.status === "running") {
      expect(result.pid).toBe(process.pid);
    }
  });

  it("returns not-running for a freshly-reaped child pid (ESRCH)", async () => {
    // Spawn a child that exits immediately; capture its pid; wait for
    // exit; probe the dead pid. macOS retains the pid for a moment
    // after wait(), but the kernel reports ESRCH once it's reaped.
    const child = spawnSync(process.execPath, ["-e", ""], { stdio: "ignore" });
    const deadPid = child.pid as number;
    expect(typeof deadPid).toBe("number");
    // Give the OS a moment to reap.
    await new Promise((r) => setTimeout(r, 50));
    writeSessionJson(stateDir, changeId, {
      change_id: changeId,
      pid: deadPid,
      pid_kind: "session",
      script_path: "/tmp/launch.sh",
      spawned_at: "2026-05-26T14:14:06Z",
    });
    const result = await probeLiveness(stateDir, changeId);
    expect(result).toEqual({ status: "not-running" });
  });

  it("returns running for pid=1 (EPERM path) when not root", async () => {
    if (process.getuid && process.getuid() === 0) {
      // Running as root would actually be able to signal pid 1, which
      // would put us in the "running" branch via no-throw instead of
      // EPERM. Both paths converge on status=running, but the EPERM
      // branch is what we want to exercise; skip on root.
      return;
    }
    writeSessionJson(stateDir, changeId, {
      change_id: changeId,
      pid: 1,
      pid_kind: "session",
      script_path: "/tmp/launch.sh",
      spawned_at: "2026-05-26T14:14:06Z",
    });
    const result = await probeLiveness(stateDir, changeId);
    expect(result.status).toBe("running");
    if (result.status === "running") {
      expect(result.pid).toBe(1);
    }
  });

  it("surfaces pidKind for pid_kind=terminal + alive pid", async () => {
    writeSessionJson(stateDir, changeId, {
      change_id: changeId,
      pid: process.pid,
      pid_kind: "terminal",
      script_path: "/tmp/launch.sh",
      spawned_at: "2026-05-26T14:14:06Z",
      terminal_app_used: "Terminal.app",
      tty: "/dev/ttys052",
    });
    const result = await probeLiveness(stateDir, changeId);
    expect(result.status).toBe("running");
    expect(result.pidKind).toBe("terminal");
  });

  it("is side-effect-free — no file writes during a normal probe", async () => {
    // Snapshot the state directory's tree (it has only session.json).
    writeSessionJson(stateDir, changeId, {
      change_id: changeId,
      pid: process.pid,
      pid_kind: "session",
      script_path: "/tmp/launch.sh",
      spawned_at: "2026-05-26T14:14:06Z",
    });
    const before = JSON.stringify(
      fs.readdirSync(path.join(stateDir, "changes", changeId)).sort(),
    );

    await probeLiveness(stateDir, changeId);

    const after = JSON.stringify(
      fs.readdirSync(path.join(stateDir, "changes", changeId)).sort(),
    );
    expect(after).toBe(before);
  });

  // Per ADR-005, the probe MUST NOT spawn subprocesses. We can't
  // monkey-patch a `node:child_process` export under ESM (the module
  // namespace is not configurable). Instead, statically assert the
  // source file never imports child_process and never references
  // `spawn` / `exec` / `fork`. This is a stronger guarantee than a
  // runtime spy: it's enforced at the source level for every code
  // path, not just the one the test happens to exercise.
  it("source contains no child_process / spawn / exec / fork references (ADR-005)", async () => {
    const src = await fs.promises.readFile(
      path.resolve(__dirname, "../lib/probeLiveness.ts"),
      "utf8",
    );
    expect(src).not.toMatch(/child_process/);
    expect(src).not.toMatch(/\bspawn\b/);
    expect(src).not.toMatch(/\bexec\b/);
    expect(src).not.toMatch(/\bfork\b/);
  });

  it("sends signal 0 only — never a non-zero signal (ADR-005)", async () => {
    writeSessionJson(stateDir, changeId, {
      change_id: changeId,
      pid: process.pid,
      pid_kind: "session",
      script_path: "/tmp/launch.sh",
      spawned_at: "2026-05-26T14:14:06Z",
    });

    const originalKill = process.kill.bind(process);
    const signals: Array<number | string | undefined> = [];
    const killSpy = vi.spyOn(process, "kill").mockImplementation(((
      pid: number,
      signal?: number | string,
    ) => {
      signals.push(signal);
      return originalKill(pid, signal as number);
    }) as typeof process.kill);

    try {
      await probeLiveness(stateDir, changeId);
    } finally {
      killSpy.mockRestore();
    }

    expect(signals.length).toBeGreaterThan(0);
    for (const sig of signals) {
      // Per ADR-005: only signal 0 — the POSIX existence probe.
      expect(sig).toBe(0);
    }
  });
});
