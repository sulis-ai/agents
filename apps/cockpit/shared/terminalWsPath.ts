// WP-006 — the one source of truth for the terminal WS endpoint path.
//
// Both ends of the terminal transport agree on this path with NO drift:
//   - the server sidecar (apps/cockpit/server/adapters/TerminalSidecar.ts)
//     accepts the browser WS upgrade only on this path;
//   - the client transport (apps/cockpit/client/src/terminal/socketWsTransport.ts)
//     derives the same-origin endpoint `ws(s)://<host>${TERMINAL_WS_PATH}`.
//
// It lives in apps/cockpit/shared/ — the intra-package home both the server and
// the client already import from (api-types, ndjsonLineFramer) — so the single
// constant is reachable from both trees without crossing the apps/cockpit/
// boundary (TDD §9, ADR-008).

/** The path the terminal WS endpoint rides on the cockpit's shared HTTP server. */
export const TERMINAL_WS_PATH = "/terminal";
