// WP-011 — single fetch funnel for the cockpit client.
//
// Every HTTP call in the client goes through apiGet(); no other module
// is allowed to call fetch() directly (enforced by the inventory test
// at client/src/tests/inventory.test.ts). The funnel exists so that
// the JSON-shape error contract is honoured in exactly one place:
//
//   - Non-2xx → throw ApiError with status + code (from { error, code }
//     JSON body when available) + message.
//   - 2xx → parse JSON, return typed result.
//
// References:
//   - WP-011 Contract (API client section).
//   - TDD §5 (HTTP surface — error-shape contract).
//
// WP-005 — the funnel also owns the ONE write path: `streamChat`, the chat
// relay's SSE reader (ADR-001/003). Keeping it here is what lets the client
// inventory gate allow exactly api/client.ts to call `fetch`.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ChatStreamEvent, ChatErrorCode } from "../../../shared/api-types";

/**
 * ApiError is the only error type any caller has to handle. A failed
 * fetch (non-2xx, or network failure) surfaces as this type; the
 * status code + machine-readable `code` field let callers branch
 * (e.g. 404 → "no such change", 422 → "no base_sha recorded").
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly code: string | null;

  constructor(status: number, code: string | null, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function buildUrl(path: string, params?: Record<string, string>): string {
  if (!params || Object.keys(params).length === 0) return path;
  const query = new URLSearchParams(params).toString();
  return `${path}?${query}`;
}

async function readErrorBody(
  res: Response,
): Promise<{ code: string | null; message: string }> {
  // Best-effort parse: the server may return { error, code } JSON
  // (TDD §5 error envelope) or a plain text body (e.g. for unexpected
  // 500s). Either way, the caller gets a non-throwing summary.
  try {
    const body = (await res.json()) as { error?: unknown; code?: unknown };
    const message =
      typeof body?.error === "string" && body.error.length > 0
        ? body.error
        : `HTTP ${res.status}`;
    const code = typeof body?.code === "string" ? body.code : null;
    return { code, message };
  } catch {
    return { code: null, message: `HTTP ${res.status}` };
  }
}

/**
 * GET helper. Throws ApiError on non-2xx; returns parsed JSON on 2xx.
 *
 * @example
 *   const changes = await apiGet<Change[]>("/api/changes");
 *   const file = await apiGet<FileContents>("/api/changes/abc/file",
 *     { path: "src/main.tsx" });
 */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string>,
): Promise<T> {
  const url = buildUrl(path, params);
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) {
    const { code, message } = await readErrorBody(res);
    throw new ApiError(res.status, code, message);
  }
  return (await res.json()) as T;
}

// ─── WP-005 — the chat relay funnel (the ONE write path; ADR-001/003) ────────
//
// `streamChat` POSTs the founder's prompt to the relay and reads the SSE reply
// stream, invoking `onEvent` per `ChatStreamEvent`. It lives HERE so it is the
// only other `fetch` caller alongside `apiGet`. The relay's typed-error
// envelope: a pre-stream refusal arrives as a non-2xx JSON status (mapped to a
// single `error` event so the hook has ONE event shape to project, FR-19/20/21);
// an in-stream error / interrupt arrives as an SSE frame (FR-22).

/** The signature the Composer / useChatStream inject (so they can be tested). */
export type StreamChatFn = (
  changeId: string,
  prompt: string,
  onEvent: (event: ChatStreamEvent) => void,
) => Promise<void>;

function asChatErrorCode(code: string | null): ChatErrorCode {
  if (
    code === "SESSION_BUSY" ||
    code === "SESSION_CHANGE_MISMATCH" ||
    code === "SESSION_UNREACHABLE"
  ) {
    return code;
  }
  return "SESSION_UNREACHABLE";
}

export const streamChat: StreamChatFn = async (changeId, prompt, onEvent) => {
  const res = await fetch(`/api/changes/${changeId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });

  if (!res.ok) {
    const { code, message } = await readErrorBody(res);
    onEvent({ type: "error", code: asChatErrorCode(code), message });
    return;
  }

  const body = res.body;
  if (!body) return;
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by a blank line; each carries `data: <json>`.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const json = dataLine.slice("data:".length).trim();
      if (json === "") continue;
      try {
        onEvent(JSON.parse(json) as ChatStreamEvent);
      } catch {
        // Skip a malformed frame; the next decides.
      }
    }
  }
};
