// Advanced (operator) view — data + side-effect actions.
//
// GET /api/changes/:id/advanced → { branchUrl, processes }. Processes are
// live, so this polls. Reveal + stop are POST actions (the app's local, so
// these OS-side calls are fine; stop is guarded server-side).

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";

export interface LinkedProcess {
  pid: number;
  kind: "session" | "agent" | "server" | "node" | "other";
  label: string;
  command: string;
  cwd: string | null;
}

export interface AdvancedData {
  branchUrl: string | null;
  processes: LinkedProcess[];
}

export function useAdvanced(changeId: string) {
  return useQuery({
    queryKey: ["advanced", changeId],
    queryFn: () => apiGet<AdvancedData>(`/api/changes/${changeId}/advanced`),
    enabled: changeId.length > 0,
    refetchInterval: 5000, // processes are live
  });
}

/** Reveal a folder in the OS file manager (default: the change's worktree). */
export async function revealPath(changeId: string, path?: string): Promise<void> {
  await fetch(`/api/changes/${changeId}/reveal`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(path ? { path } : {}),
  });
}

/** Stop a linked process by pid (guarded server-side). */
export async function stopLinkedProcess(
  changeId: string,
  pid: number,
): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch(`/api/changes/${changeId}/processes/${pid}/stop`, {
    method: "POST",
  });
  try {
    return (await res.json()) as { ok: boolean; error?: string };
  } catch {
    return { ok: res.ok };
  }
}
