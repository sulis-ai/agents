// WP-005 — <ChangeHealthBadge> (RED).
//
// The quieter foot read shown ONLY when the change is not waiting on the
// founder. Word + SHAPE (never colour alone) + an SR reason. Renders all four
// states, data drives which (WP Contract):
//   on-track     → check
//   off-track    → warning triangle
//   worth-a-look → dash / minus (deferred-input carry)
//   unknown      → a NEUTRAL shape + NEUTRAL word "Not assessed yet" (FR-31) —
//                  never styled as on-track or off-track (no green lie, no red
//                  alarm on a change that simply hasn't started).

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import type { ChangeHealth } from "../../../shared/api-types";
import {
  ChangeHealthBadge,
  HEALTH_UNKNOWN_LABEL,
} from "../components/ChangeHealthBadge";

function renderBadge(health: ChangeHealth) {
  return render(<ChangeHealthBadge health={health} />);
}

describe("<ChangeHealthBadge> — word + shape, four states (WP-005)", () => {
  it("ON TRACK: renders the 'On track' word, an on-track shape class, and the SR reason", () => {
    const { container, getByText } = renderBadge({
      state: "on-track",
      reason: "tests green, on plan",
    });
    expect(getByText(/on track/i)).toBeInTheDocument();
    expect(container.querySelector('[data-health-state="on-track"]')).toBeTruthy();
    expect(getByText(/tests green, on plan/i)).toBeInTheDocument();
  });

  it("OFF TRACK: renders the 'Off track' word + off-track shape + SR reason", () => {
    const { container, getByText } = renderBadge({
      state: "off-track",
      reason: "tests failing",
    });
    expect(getByText(/off track/i)).toBeInTheDocument();
    expect(container.querySelector('[data-health-state="off-track"]')).toBeTruthy();
    expect(getByText(/tests failing/i)).toBeInTheDocument();
  });

  it("WORTH A LOOK: renders the 'Worth a look' word + look shape (the carried deferred-input state)", () => {
    const { container, getByText } = renderBadge({
      state: "worth-a-look",
      reason: "missing tests for its stage",
    });
    expect(getByText(/worth a look/i)).toBeInTheDocument();
    expect(
      container.querySelector('[data-health-state="worth-a-look"]'),
    ).toBeTruthy();
  });

  it("UNKNOWN (FR-31 / S-16): renders the NEUTRAL 'Not assessed yet' word, NOT on-track and NOT off-track, with its reason", () => {
    const { container, getByText, queryByText } = renderBadge({
      state: "unknown",
      reason: "no checks have run for this stage yet",
    });
    // The honest neutral wording (the Q-5 default, a swappable constant).
    expect(getByText(new RegExp(HEALTH_UNKNOWN_LABEL, "i"))).toBeInTheDocument();
    expect(container.querySelector('[data-health-state="unknown"]')).toBeTruthy();
    // Never masquerades as the positive or destructive read.
    expect(container.querySelector('[data-health-state="on-track"]')).toBeNull();
    expect(container.querySelector('[data-health-state="off-track"]')).toBeNull();
    expect(queryByText(/^on track$/i)).not.toBeInTheDocument();
    expect(queryByText(/^off track$/i)).not.toBeInTheDocument();
    expect(getByText(/no checks have run/i)).toBeInTheDocument();
  });

  it("the unknown label is a single exported string constant (Q-5 default, swappable)", () => {
    expect(typeof HEALTH_UNKNOWN_LABEL).toBe("string");
    expect(HEALTH_UNKNOWN_LABEL.length).toBeGreaterThan(0);
  });
});
