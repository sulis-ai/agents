// WP-012 — relative-time formatter.
//
// Hand-rolled bucket formatter — CP-01: a six-bucket "just now/seconds/
// minutes/hours/yesterday/days/weeks" formatter is small enough that
// pulling in date-fns is the bespoke option. Exported via /utils/ so
// WP-013 can reuse it for transcript timestamps (WP Blue checklist).

const SECOND_MS = 1_000;
const MINUTE_MS = 60 * SECOND_MS;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const WEEK_MS = 7 * DAY_MS;

/**
 * Format an ISO-8601 timestamp as a founder-readable relative phrase.
 *
 * Falsy / invalid inputs render as "unknown" so a malformed server
 * payload never crashes the UI.
 *
 * @param iso  ISO-8601 timestamp string (e.g. "2026-05-26T11:55:00Z").
 * @param now  optional "now" override; defaults to `new Date()` (tests
 *             pass a fixed Date for deterministic bucket coverage).
 */
export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const past = new Date(iso);
  if (Number.isNaN(past.getTime())) return "unknown";

  const deltaMs = now.getTime() - past.getTime();
  if (deltaMs < 0) return "in the future";

  if (deltaMs < 30 * SECOND_MS) return "just now";
  if (deltaMs < MINUTE_MS) {
    const s = Math.round(deltaMs / SECOND_MS);
    return `${s} seconds ago`;
  }
  if (deltaMs < HOUR_MS) {
    const m = Math.floor(deltaMs / MINUTE_MS);
    return `${m} ${m === 1 ? "minute" : "minutes"} ago`;
  }
  if (deltaMs < DAY_MS) {
    const h = Math.floor(deltaMs / HOUR_MS);
    return `${h} ${h === 1 ? "hour" : "hours"} ago`;
  }
  if (deltaMs < 2 * DAY_MS) return "yesterday";
  if (deltaMs < WEEK_MS) {
    const d = Math.floor(deltaMs / DAY_MS);
    return `${d} days ago`;
  }
  const weeks = Math.floor(deltaMs / WEEK_MS);
  return `${weeks} ${weeks === 1 ? "week" : "weeks"} ago`;
}
