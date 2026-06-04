// Chat-redesign follow-on — the "Advanced" (operator) view's data + actions.
//
// Surfaces the operational substrate of a change: the branch's GitHub link,
// and the OS processes linked to the change (the agent session, dev/preview
// servers, the web-chat process). Plus the two side-effect actions: reveal a
// folder in the OS file manager, and stop a process.
//
// None of this writes the repo. Reveal/ps/git-remote are read-only-ish OS
// calls; stop is guarded (never the server's own pid).

import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { promisify } from "node:util";

const exec = promisify(execFile);

export type ProcessHealth = "running" | "orphaned" | "defunct";

export interface LinkedProcess {
  pid: number;
  ppid: number;
  /** Raw process state (ps STAT): R running, S sleeping, Z zombie, … */
  state: string;
  kind: "session" | "agent" | "server" | "node" | "other";
  label: string;
  command: string;
  cwd: string | null;
  health: ProcessHealth;
  /** Plain-English "what's needed" hint (empty for healthy/active ones). */
  hint: string;
}

/**
 * Derive a process's health from its ps state + parent pid:
 *   - defunct: a zombie (state Z) — already exited, waiting to be reaped;
 *     it can't be stopped and clears on its own.
 *   - orphaned: parent is init/launchd (ppid 1) — its launcher is gone, so
 *     it's very likely a stray left over from a closed terminal/old run.
 *   - running: a live process with a real parent.
 */
export function processHealth(
  state: string,
  ppid: number,
): { health: ProcessHealth; hint: string } {
  if (state.startsWith("Z"))
    return {
      health: "defunct",
      hint: "Defunct (zombie) — already exited; it clears on its own, nothing to do.",
    };
  if (ppid === 1)
    return {
      health: "orphaned",
      hint: "Orphaned — its launcher is gone, so it's likely a leftover and safe to stop.",
    };
  return { health: "running", hint: "" };
}

/** The GitHub branch URL for a worktree's origin, or null if not GitHub. */
export async function branchUrl(
  worktreePath: string,
  branch: string,
): Promise<string | null> {
  try {
    const { stdout } = await exec(
      "git",
      ["-C", worktreePath, "remote", "get-url", "origin"],
      { timeout: 5000 },
    );
    // git@github.com:owner/repo.git  |  https://github.com/owner/repo(.git)
    const m = stdout
      .trim()
      .match(/github\.com[:/]([^/]+)\/(.+?)(?:\.git)?$/i);
    if (!m) return null;
    return `https://github.com/${m[1]}/${m[2]}/tree/${encodeURIComponent(branch)}`;
  } catch {
    return null;
  }
}

/** Reveal a path in the OS file manager (Finder / Explorer / xdg-open). */
export async function revealInFileManager(
  path: string,
): Promise<{ ok: boolean; error?: string }> {
  if (!path || !existsSync(path)) return { ok: false, error: "Folder not found." };
  try {
    if (process.platform === "darwin") {
      await exec("open", ["-R", path], { timeout: 5000 });
    } else if (process.platform === "win32") {
      // explorer exits non-zero even on success; fire and forget.
      exec("explorer", [path]).catch(() => {});
    } else {
      await exec("xdg-open", [path], { timeout: 5000 });
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: String(e).slice(0, 160) };
  }
}

/** Classify a process command into a plain-English kind + label. */
export function classifyProcess(command: string): {
  kind: LinkedProcess["kind"];
  label: string;
} {
  if (/claude\b[^\n]*--agent\s+sulis/.test(command))
    return { kind: "session", label: "Agent session (your terminal)" };
  if (/claude\b[^\n]*(--resume|--continue|\s-p\b)/.test(command))
    return { kind: "agent", label: "Agent (web chat / background)" };
  if (/\bvite\b/.test(command))
    return { kind: "server", label: "Preview server (the web app)" };
  if (/tsx\b[^\n]*server\/index/.test(command))
    return { kind: "server", label: "App server" };
  if (/npm\b[^\n]*run[^\n]*dev|concurrently/.test(command))
    return { kind: "server", label: "Dev server" };
  if (/claude\b/.test(command))
    return { kind: "agent", label: "Claude process" };
  if (/\bnode\b/.test(command)) return { kind: "node", label: "Node process" };
  return { kind: "other", label: "Process" };
}

/**
 * Processes linked to this change — matched by the change id or the worktree
 * path appearing in the process's command/env (`ps -axeww` appends the env,
 * which carries SULIS_CHANGE_ID + PWD). Best-effort; returns [] on any error.
 */
export async function listChangeProcesses(
  changeId: string,
  worktreePath: string,
): Promise<LinkedProcess[]> {
  try {
    const { stdout } = await exec(
      "ps",
      ["-axeww", "-o", "pid=,ppid=,stat=,command="],
      { timeout: 8000, maxBuffer: 16 * 1024 * 1024 },
    );
    const selfPid = process.pid;
    const seen = new Set<number>();
    const out: LinkedProcess[] = [];
    for (const line of stdout.split("\n")) {
      if (!line.trim()) continue;
      if (!line.includes(changeId) && !line.includes(worktreePath)) continue;
      const m = line.match(/^\s*(\d+)\s+(\d+)\s+(\S+)\s+(.*)$/);
      if (!m) continue;
      const pid = Number(m[1]);
      if (pid === selfPid || seen.has(pid)) continue;
      seen.add(pid);
      const ppid = Number(m[2]);
      const state = m[3]!;
      const cwd = line.match(/\bPWD=([^\s]+)/)?.[1] ?? null;
      // Strip the env tail (KEY=value tokens ps appends) for a clean display.
      const command = m[4].replace(/\s+[A-Z_][A-Z0-9_]*=[^\s]*/g, "").trim();
      const { kind, label } = classifyProcess(command);
      const { health, hint } = processHealth(state, ppid);
      out.push({
        pid,
        ppid,
        state,
        kind,
        label,
        command: command.slice(0, 200),
        cwd,
        health,
        hint,
      });
    }
    return out;
  } catch {
    return [];
  }
}

/** Stop a process by pid. Guarded: never the server's own pid, never pid ≤ 1.
 *
 * Sends SIGTERM, then escalates to SIGKILL after a short grace period if the
 * process is still alive — stale node/vite dev servers routinely ignore
 * SIGTERM, so a polite-only stop silently does nothing (the bug this fixes). */
export function stopProcess(pid: number): { ok: boolean; error?: string } {
  if (!Number.isInteger(pid) || pid <= 1) return { ok: false, error: "Invalid process." };
  if (pid === process.pid)
    return { ok: false, error: "Refusing to stop the app's own server." };
  try {
    process.kill(pid, "SIGTERM");
  } catch (e) {
    return { ok: false, error: String(e).slice(0, 120) };
  }
  // Escalate to SIGKILL if it's still there after a grace period.
  setTimeout(() => {
    try {
      process.kill(pid, 0); // existence check — throws ESRCH if already gone
      process.kill(pid, "SIGKILL");
    } catch {
      /* already exited — nothing to do */
    }
  }, 1200);
  return { ok: true };
}
