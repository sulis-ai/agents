// WP-001 — the per-product chat-scope vocabulary + validator (ADR-002).
//
// This is the SINGLE home for the chat scope vocabulary (CL-05, one vocabulary):
//   - the bare scope sentinels `__all__` / `__unassigned__`;
//   - the `product:` wire prefix;
//   - `parseChatScope`, the inbound-string validator the server (WP-002) and the
//     client funnel (WP-003) both run before trusting a string as a `ChatScope`.
//
// It lives in `shared/` (the lowest layer both client and server import) so the
// vocabulary has exactly one source and the dependency direction holds: the
// client's `lib/productCounts.ts` re-uses `UNASSIGNED_SCOPE`/`ALL_SCOPE` FROM
// here (shared ← client), never the reverse.
//
// The wire scope (ADR-002) is `product:{id}` | `product:__all__` |
// `product:__unassigned__`. A real product id is colon-bearing
// (`dna:product:<ulid>`), so the validator accepts colons inside the id while
// rejecting anything that could traverse out of the on-disk thread root
// (`/`, `\`, `.`-only / `..` segments, whitespace, control chars). The backend
// (WP-002) derives a `validate_store_id`-safe key from the scope; THIS guard is
// the wire-level gate that rejects a hostile string before it is keyed.

import type { ChatScope } from "./api-types";

/**
 * The "All products" overview scope sentinel (bare). `product:__all__` is the
 * cross-product overview chat (ADR-002). Defined here so the switcher row id and
 * the chat scope share one token (no second source).
 */
export const ALL_SCOPE = "__all__" as const;

/**
 * The reserved "Unassigned" triage scope sentinel (bare). `product:__unassigned__`
 * is reserved for the Phase-2 triage chat — the key is reserved now so the store
 * layout doesn't fork later (ADR-002). The client's `productCounts.ts` re-uses
 * this constant for its board sentinel (one vocabulary).
 */
export const UNASSIGNED_SCOPE = "__unassigned__" as const;

/** The wire prefix every chat scope carries (`product:{...}`). */
const SCOPE_PREFIX = "product:";

/**
 * A safe scope-id body: one-or-more of letters, digits, `-`, `_`, or `:` (the
 * `:` admits the colon-bearing real product id `dna:product:<ulid>`). Anchored
 * full-string with `RegExp`-`test` against a single line, so it cannot contain a
 * path separator, a `.` (no `..` traversal), whitespace, or a newline.
 */
const SCOPE_BODY = /^[A-Za-z0-9_:-]+$/;

/**
 * Validate an inbound string as a `ChatScope`, or return `null` if it is not a
 * safe one. Accepts exactly the three forms — `product:{id}` (id colon-bearing),
 * `product:__all__`, `product:__unassigned__` — and rejects path traversal
 * (`..`, `/`, `\`), embedded newlines, whitespace, an empty id, and any non-
 * `product:` prefix. A deterministic refusal (returns `null`, never throws) so
 * the caller decides the response (CF-03).
 */
export function parseChatScope(input: string): ChatScope | null {
  if (!input.startsWith(SCOPE_PREFIX)) return null;
  const body = input.slice(SCOPE_PREFIX.length);
  if (body.length === 0) return null;
  if (!SCOPE_BODY.test(body)) return null;
  // `.` is already excluded by SCOPE_BODY (no `.` in the char class), so a `..`
  // traversal segment cannot survive the regex. This explicit guard documents
  // the traversal intent for the next reader and is a backstop if SCOPE_BODY is
  // ever widened.
  if (body.includes("..")) return null;
  return input as ChatScope;
}
