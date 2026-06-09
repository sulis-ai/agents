// WP-005 — <LivenessProbe> (RED).
//
// The stripped-down liveness read on the card's top line: JUST a probe dot
// + a bare relative time, no state word visible. The probe carries its state
// by FILL / MOTION / SHAPE (never colour alone) plus a screen-reader-only
// label. Four states (TDD §5 + WP Contract):
//   working  → filled + pulse  (recent activity, the only motion on the card)
//   live     → solid filled, steady (session running but quiet)
//   idle     → hollow / outline ring
//   unknown  → a DISTINCT dashed "?" ring (FR-41) — never confused with idle
// + no-recency (FR-42): lastActivityAt === null renders "—", never "now".
// + reduced-motion (S-30): the pulse drops but the SR label survives.

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import type { Change } from "../../../shared/api-types";
import { LivenessProbe } from "../components/LivenessProbe";

// A fixed "now" so the working/live split (recency) is deterministic.
const NOW = new Date("2026-06-09T12:00:00Z");

function iso(msAgo: number): string {
  return new Date(NOW.getTime() - msAgo).toISOString();
}

const SECOND = 1_000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;

function renderProbe(props: {
  liveness: Change["liveness"];
  lastActivityAt: string | null;
}) {
  return render(
    <LivenessProbe
      liveness={props.liveness}
      lastActivityAt={props.lastActivityAt}
      now={NOW}
    />,
  );
}

describe("<LivenessProbe> — four states by fill/motion/shape (WP-005)", () => {
  it("WORKING: running + very recent activity → working state, filled pulse, 'actively working' SR label, recency text", () => {
    const { container, getByText } = renderProbe({
      liveness: { status: "running", pid: 42 },
      lastActivityAt: iso(5 * SECOND), // < 60s window → working
    });
    const probe = container.querySelector('[data-probe-state="working"]');
    expect(probe).toBeTruthy();
    // SR label names the state (the visible word is dropped).
    expect(getByText(/actively working/i)).toBeInTheDocument();
    // The bare relative time shows (the only visible text of the probe).
    expect(getByText(/now|just now/i)).toBeInTheDocument();
  });

  it("LIVE: running but quiet (activity older than the working window) → live state, steady fill, 'session live' SR label", () => {
    const { container, getByText } = renderProbe({
      liveness: { status: "running", pid: 42 },
      lastActivityAt: iso(10 * MINUTE), // running but not recent → live
    });
    expect(container.querySelector('[data-probe-state="live"]')).toBeTruthy();
    expect(getByText(/session live/i)).toBeInTheDocument();
  });

  it("IDLE: not-running → idle state, hollow ring, 'idle, not running' SR label", () => {
    const { container, getByText } = renderProbe({
      liveness: { status: "not-running" },
      lastActivityAt: iso(2 * HOUR),
    });
    expect(container.querySelector('[data-probe-state="idle"]')).toBeTruthy();
    expect(getByText(/idle, not running/i)).toBeInTheDocument();
  });

  it("UNKNOWN (FR-41): unknown liveness → unknown state with its OWN shape class, 'liveness unknown' SR label", () => {
    const { container, getByText } = renderProbe({
      liveness: { status: "unknown", reason: "no session record" },
      lastActivityAt: iso(3 * HOUR),
    });
    expect(container.querySelector('[data-probe-state="unknown"]')).toBeTruthy();
    expect(getByText(/liveness unknown/i)).toBeInTheDocument();
  });

  it("UNKNOWN is VISUALLY DISTINCT from IDLE (S-17): different state class + different dot class", () => {
    const idle = renderProbe({
      liveness: { status: "not-running" },
      lastActivityAt: iso(2 * HOUR),
    });
    const idleDot = idle.container.querySelector('[data-probe-state="idle"] [data-probe-dot]');
    idle.unmount();

    const unknown = renderProbe({
      liveness: { status: "unknown", reason: "x" },
      lastActivityAt: iso(2 * HOUR),
    });
    const unknownDot = unknown.container.querySelector('[data-probe-state="unknown"] [data-probe-dot]');

    expect(idleDot).toBeTruthy();
    expect(unknownDot).toBeTruthy();
    // The dot's own class set differs — the shape (hollow ring vs dashed "?")
    // is carried in CSS keyed off distinct classes, so greyscale tells them apart.
    expect((idleDot as HTMLElement).className).not.toEqual(
      (unknownDot as HTMLElement).className,
    );
  });

  it("NO-RECENCY (FR-42 / S-18): lastActivityAt null → renders an em-dash, NEVER 'now' or a bogus age, and the probe still renders", () => {
    const { container, getByText, queryByText } = renderProbe({
      liveness: { status: "unknown", reason: "no session" },
      lastActivityAt: null,
    });
    // The probe still renders its liveness state.
    expect(container.querySelector('[data-probe-state="unknown"]')).toBeTruthy();
    // The time slot is an em-dash, not a fabricated value.
    expect(getByText("—")).toBeInTheDocument();
    expect(queryByText(/^now$/i)).not.toBeInTheDocument();
    expect(queryByText(/ago/i)).not.toBeInTheDocument();
  });

  it("REDUCED MOTION (S-30): the static-ring fallback drops the pulse class but keeps the SR state label", () => {
    // The component exposes a `reducedMotion` flag (jsdom can't evaluate the
    // media query). With it set, a working probe must not carry the pulsing
    // modifier, yet still announce its state to assistive tech.
    const { container, getByText } = render(
      <LivenessProbe
        liveness={{ status: "running", pid: 1 }}
        lastActivityAt={iso(5 * SECOND)}
        now={NOW}
        reducedMotion
      />,
    );
    const probe = container.querySelector('[data-probe-state="working"]');
    expect(probe).toBeTruthy();
    expect((probe as HTMLElement).dataset.reducedMotion).toBe("true");
    // SR label still names the state even with motion suppressed.
    expect(getByText(/actively working/i)).toBeInTheDocument();
  });
});
