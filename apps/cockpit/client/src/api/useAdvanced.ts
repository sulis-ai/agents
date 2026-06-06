// Advanced (operator) view — data + side-effect actions.
//
// GET /api/changes/:id/advanced → { branchUrl, processes }. Processes are
// live, so this polls. Reveal + stop are POST actions (the app's local, so
// these OS-side calls are fine; stop is guarded server-side).

import { useQuery } from "@tanstack/react-query";
import { ApiError, apiGet, apiPost } from "./client";

export type ProcessHealth = "running" | "orphaned" | "defunct";

export interface LinkedProcess {
  pid: number;
  ppid: number;
  state: string;
  kind: "session" | "agent" | "server" | "node" | "other";
  label: string;
  command: string;
  cwd: string | null;
  health: ProcessHealth;
  hint: string;
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
  // Through the single client fetch funnel (apiPost) so the inventory gate's
  // "only api/client.ts calls fetch" guarantee holds.
  await apiPost<void>(
    `/api/changes/${changeId}/reveal`,
    path ? { path } : {},
  );
}

/** Stop a linked process by pid (guarded server-side). */
export async function stopLinkedProcess(
  changeId: string,
  pid: number,
): Promise<{ ok: boolean; error?: string }> {
  try {
    return await apiPost<{ ok: boolean; error?: string }>(
      `/api/changes/${changeId}/processes/${pid}/stop`,
    );
  } catch (err) {
    // The funnel throws ApiError on non-2xx; surface it as the {ok,error}
    // shape the caller already handles (parity with the previous behaviour).
    if (err instanceof ApiError) {
      return { ok: false, error: err.message };
    }
    return { ok: false };
  }
}
