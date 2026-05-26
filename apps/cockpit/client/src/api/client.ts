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

async function readErrorBody(res: Response): Promise<{ code: string | null; message: string }> {
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
