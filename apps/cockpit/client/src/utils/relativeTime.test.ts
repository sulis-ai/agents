// WP-012 — relative-time util tests.
//
// Bucket coverage: "just now", seconds, minutes, hours, "yesterday",
// days, weeks. We avoid date-fns (CP-01 — boring default for a half-
// dozen buckets is hand-rolled, no new dep).

import { describe, it, expect } from "vitest";
import { formatRelativeTime, formatShippedRecency } from "./relativeTime";

function isoOffset(ms: number, now: Date): string {
  return new Date(now.getTime() - ms).toISOString();
}

describe("formatRelativeTime", () => {
  const NOW = new Date("2026-05-26T12:00:00Z");

  it("renders 'just now' for sub-30-second deltas", () => {
    expect(formatRelativeTime(isoOffset(5_000, NOW), NOW)).toBe("just now");
    expect(formatRelativeTime(isoOffset(29_000, NOW), NOW)).toBe("just now");
  });

  it("renders seconds for 30s..59s", () => {
    expect(formatRelativeTime(isoOffset(45_000, NOW), NOW)).toBe(
      "45 seconds ago",
    );
  });

  it("renders minutes for 1m..59m", () => {
    expect(formatRelativeTime(isoOffset(60_000, NOW), NOW)).toBe(
      "1 minute ago",
    );
    expect(formatRelativeTime(isoOffset(3 * 60_000, NOW), NOW)).toBe(
      "3 minutes ago",
    );
  });

  it("renders hours for 1h..23h", () => {
    expect(formatRelativeTime(isoOffset(60 * 60_000, NOW), NOW)).toBe(
      "1 hour ago",
    );
    expect(formatRelativeTime(isoOffset(5 * 60 * 60_000, NOW), NOW)).toBe(
      "5 hours ago",
    );
  });

  it("renders 'yesterday' for the 24h..48h bucket", () => {
    expect(formatRelativeTime(isoOffset(25 * 60 * 60_000, NOW), NOW)).toBe(
      "yesterday",
    );
  });

  it("renders days for 2d..6d", () => {
    expect(formatRelativeTime(isoOffset(3 * 24 * 60 * 60_000, NOW), NOW)).toBe(
      "3 days ago",
    );
  });

  it("renders weeks for 7d+", () => {
    expect(formatRelativeTime(isoOffset(10 * 24 * 60 * 60_000, NOW), NOW)).toBe(
      "1 week ago",
    );
    expect(formatRelativeTime(isoOffset(21 * 24 * 60 * 60_000, NOW), NOW)).toBe(
      "3 weeks ago",
    );
  });

  it("renders 'in the future' defensively for negative deltas", () => {
    // Server clock drift could produce a future timestamp; render
    // something readable rather than "-3 minutes ago".
    expect(formatRelativeTime(isoOffset(-60_000, NOW), NOW)).toBe(
      "in the future",
    );
  });

  it("renders 'unknown' for invalid ISO strings", () => {
    expect(formatRelativeTime("not-a-date", NOW)).toBe("unknown");
  });
});

// WP-012 — the SHIPPED-RECENCY wording (Q-7 default "shipped Nd ago"). The
// archival phrase REUSES the compact bucket from formatCompactRelativeTime
// (EP-03 — one bucketing source), so we only assert the wrapping wording + a
// representative day/week/hour bucket and the defensive "—" fall-through.
describe("formatShippedRecency (WP-012, Q-7)", () => {
  const NOW = new Date("2026-06-09T12:00:00Z");

  it("renders 'shipped Nd ago' for a days-old shipped time", () => {
    expect(
      formatShippedRecency(isoOffset(5 * 24 * 60 * 60_000, NOW), NOW),
    ).toBe("shipped 5d ago");
  });

  it("renders 'shipped Nw ago' for a weeks-old shipped time", () => {
    expect(
      formatShippedRecency(isoOffset(14 * 24 * 60 * 60_000, NOW), NOW),
    ).toBe("shipped 2w ago");
  });

  it("renders 'shipped Nh ago' for an hours-old shipped time", () => {
    expect(formatShippedRecency(isoOffset(3 * 60 * 60_000, NOW), NOW)).toBe(
      "shipped 3h ago",
    );
  });

  it("falls through to the defensive '—' token for an invalid shipped time", () => {
    // A malformed payload must not print a bogus age; the compact formatter's
    // "—" guard flows through the wrapping wording.
    expect(formatShippedRecency("not-a-date", NOW)).toBe("shipped — ago");
  });
});
