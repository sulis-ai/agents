// WP-012 — client-side config constants.
//
// The MVP's only tunable today is the liveness-poll interval (ADR-007).
// LIVENESS_POLL_MS is the one polling exception to "manual refresh
// only" — the dashboard and sidebar poll /api/changes every 10 seconds
// so the founder sees the "session running" indicator update without
// clicking refresh.
//
// Overridable at build time via the Vite-standard VITE_-prefixed env
// var; tests use a small value (e.g. 50ms) so they don't have to wait
// a real 10 seconds.

const FALLBACK_LIVENESS_POLL_MS = 10_000;

function readLivenessPollOverride(): number | null {
  // `import.meta.env` is the Vite-standard way to read env vars in
  // client code (CP-01 — established convention for the bundler we
  // already use). The defensive shape works in both the production
  // build (where the var is statically replaced) and in tests where
  // `import.meta.env` may be undefined.
  const raw = (import.meta as { env?: Record<string, string | undefined> }).env
    ?.VITE_LIVENESS_POLL_MS;
  if (raw === undefined || raw === "") return null;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

export const LIVENESS_POLL_MS: number =
  readLivenessPollOverride() ?? FALLBACK_LIVENESS_POLL_MS;
