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
import type {
  ChatStreamEvent,
  ChatErrorCode,
  ConciergeStreamEvent,
  OnboardingRequest,
  OnboardingStreamEvent,
  StartFromIntentRequest,
  StartFromIntentStreamEvent,
} from "../../../shared/api-types";

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

/**
 * POST helper for the operator-action routes (reveal-in-finder + stop-process,
 * ADR-015). It lives HERE so it stays inside the client `fetch` funnel — the
 * inventory gate allow-lists exactly api/client.ts as a fetch caller. Returns
 * the parsed JSON body on 2xx; throws ApiError on non-2xx (the same error
 * contract as apiGet). `body` is optional (the stop route takes no body).
 */
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const { code, message } = await readErrorBody(res);
    throw new ApiError(res.status, code, message);
  }
  // The reveal route returns no body; tolerate an empty/!json response.
  try {
    return (await res.json()) as T;
  } catch {
    return undefined as T;
  }
}

/**
 * DELETE helper for the settings management routes (WP-007; ADR-019). It lives
 * HERE so it stays inside the client `fetch` funnel — the inventory gate
 * allow-lists exactly api/client.ts as a fetch caller. Returns the parsed JSON
 * body on 2xx (or `undefined` when the route returns no body); throws ApiError
 * on non-2xx (the same error contract as apiGet/apiPost).
 */
export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(path, { method: "DELETE" });
  if (!res.ok) {
    const { code, message } = await readErrorBody(res);
    throw new ApiError(res.status, code, message);
  }
  // A delete route may return `{ ok: true }` or no body; tolerate both.
  try {
    return (await res.json()) as T;
  } catch {
    return undefined as T;
  }
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

/**
 * Read an SSE body to completion, invoking `onEvent` per `data:` frame. Shared
 * by `streamChat` and `streamConciergeQuery` (EP-03 — 2-consumer threshold) so
 * the frame-splitting + malformed-frame skipping lives in exactly one place.
 * The frame JSON is typed by the caller's generic.
 */
async function readSseStream<T>(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: T) => void,
): Promise<void> {
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
        onEvent(JSON.parse(json) as T);
      } catch {
        // Skip a malformed frame; the next decides.
      }
    }
  }
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

  if (!res.body) return;
  await readSseStream<ChatStreamEvent>(res.body, onEvent);
};

// ─── WP-009 — the concierge query funnel (read-only; FR-33; ADR-006) ─────────
//
// `streamConciergeQuery` POSTs the founder's question to the concierge route
// and reads the SSE answer stream, invoking `onEvent` per `ConciergeStreamEvent`.
// It lives HERE alongside `streamChat` so it is one of the only two `fetch`
// callers (the client inventory gate allow-lists exactly api/client.ts). The
// POST verb carries the question body; the PATH is read-only (the server route
// performs no write/mint/start, ADR-006).

/** The signature the ConciergeChat / useConciergeStream inject (testable). */
export type StreamConciergeFn = (
  question: string,
  onEvent: (event: ConciergeStreamEvent) => void,
  productId?: string,
) => Promise<void>;

export const streamConciergeQuery: StreamConciergeFn = async (
  question,
  onEvent,
  productId,
) => {
  const res = await fetch("/api/concierge/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      productId ? { question, product: productId } : { question },
    ),
  });

  if (!res.ok) {
    const { message } = await readErrorBody(res);
    // The concierge's only error code is SESSION_UNREACHABLE (read-only path).
    onEvent({ type: "error", code: "SESSION_UNREACHABLE", message });
    return;
  }

  if (!res.body) return;
  await readSseStream<ConciergeStreamEvent>(res.body, onEvent);
};

// ─── WP-010 — the onboarding funnel (cold-start mint; ADR-007/008) ───────────
//
// `streamOnboarding` POSTs ONE onboarding turn to /api/onboarding/session and
// reads the SSE stream, invoking `onEvent` per `OnboardingStreamEvent`. It
// lives HERE alongside the other two SSE callers so it stays inside the client
// inventory gate's `fetch` allow-list (only api/client.ts). The act is
// confirm-gated server-side (FR-N6); the funnel just carries the turn. A
// pre-stream refusal (scope violation / stale confirm / busy) arrives as a
// non-2xx JSON status, mapped to a single `error` event so the hook has ONE
// event shape to project (parity with the chat/concierge funnels).

/** The signature OnboardingChat / useOnboarding inject (testable). */
export type StreamOnboardingFn = (
  request: OnboardingRequest,
  onEvent: (event: OnboardingStreamEvent) => void,
) => Promise<void>;

function asOnboardingErrorCode(
  code: string | null,
): Extract<OnboardingStreamEvent, { type: "error" }>["code"] {
  if (
    code === "DISCOVERY_SCOPE_VIOLATION" ||
    code === "DISCOVERY_CONFIRM_STALE" ||
    code === "REPO_CREATE_FAILED" ||
    code === "SESSION_BUSY" ||
    code === "SESSION_UNREACHABLE"
  ) {
    return code;
  }
  return "SESSION_UNREACHABLE";
}

export const streamOnboarding: StreamOnboardingFn = async (request, onEvent) => {
  const res = await fetch("/api/onboarding/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const { code, message } = await readErrorBody(res);
    onEvent({ type: "error", code: asOnboardingErrorCode(code), message });
    return;
  }

  if (!res.body) return;
  await readSseStream<OnboardingStreamEvent>(res.body, onEvent);
};

// ─── WP-011 — the start-from-intent funnel (start a change; FR-29/30/34) ─────
//
// `streamStartFromIntent` POSTs ONE start-from-intent turn to
// /api/changes/start-from-intent and reads the SSE stream, invoking `onEvent`
// per `StartFromIntentStreamEvent`. It lives HERE alongside the other SSE
// callers so it stays inside the client inventory gate's `fetch` allow-list
// (only api/client.ts). The change-start act is confirm-gated server-side
// (FR-N6); the funnel just carries the turn. A pre-stream refusal (ambiguous /
// stale / unreachable / busy) arrives as a non-2xx JSON status, mapped to a
// single `error` event so the hook has ONE event shape to project (parity with
// the chat / concierge / onboarding funnels).

/** The signature StartFromIntent / useStartFromIntent inject (testable). */
export type StreamStartFromIntentFn = (
  request: StartFromIntentRequest,
  onEvent: (event: StartFromIntentStreamEvent) => void,
) => Promise<void>;

function asStartErrorCode(
  code: string | null,
): Extract<StartFromIntentStreamEvent, { type: "error" }>["code"] {
  if (
    code === "INTENT_AMBIGUOUS" ||
    code === "START_CONFIRM_STALE" ||
    code === "REPO_UNREACHABLE" ||
    code === "SESSION_BUSY" ||
    code === "SESSION_UNREACHABLE"
  ) {
    return code;
  }
  return "SESSION_UNREACHABLE";
}

export const streamStartFromIntent: StreamStartFromIntentFn = async (
  request,
  onEvent,
) => {
  const res = await fetch("/api/changes/start-from-intent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const { code, message } = await readErrorBody(res);
    onEvent({ type: "error", code: asStartErrorCode(code), message });
    return;
  }

  if (!res.body) return;
  await readSseStream<StartFromIntentStreamEvent>(res.body, onEvent);
};
