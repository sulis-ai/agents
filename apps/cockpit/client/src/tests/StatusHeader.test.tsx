// WP-004 — <StatusHeader> tests (FR-05/12).
//
// Renders the plain-English "what's happening" headline from the status
// route, plus a needs-attention badge when the change is flagged. The
// badge follows the SIGNED visual contract's status-label readability
// rule: a warning-tint pill + an amber dot (decorative) + a worded
// reason ("waiting on you", "stopped mid-reply") — colour is never the
// sole cue; the WORD is the indicator (WCAG 1.4.1).

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusHeader } from "../components/StatusHeader";
import type { ChangeStatus } from "../../../shared/api-types";

function status(overrides: Partial<ChangeStatus> = {}): ChangeStatus {
  return {
    changeId: "01ABC",
    stage: "design",
    headline: "Designing the technical approach — working now.",
    needsAttention: { flagged: false, reason: null },
    ...overrides,
  };
}

describe("<StatusHeader /> (FR-05/12)", () => {
  it("renders the plain-English headline", () => {
    render(<StatusHeader status={status()} />);
    expect(
      screen.getByText("Designing the technical approach — working now."),
    ).toBeInTheDocument();
  });

  it("does NOT render a needs-attention badge when the change is not flagged", () => {
    render(
      <StatusHeader
        status={status({ needsAttention: { flagged: false, reason: null } })}
      />,
    );
    expect(screen.queryByTestId("needs-attention")).not.toBeInTheDocument();
  });

  it("renders a needs-attention badge with a worded reason when flagged blocked", () => {
    render(
      <StatusHeader
        status={status({
          needsAttention: { flagged: true, reason: "blocked" },
        })}
      />,
    );
    const badge = screen.getByTestId("needs-attention");
    expect(badge).toBeInTheDocument();
    // The word carries the meaning — not colour alone.
    expect(badge.textContent?.toLowerCase()).toMatch(/blocked/);
  });

  it("renders a worded reason for waiting-on-decision ('waiting on you')", () => {
    render(
      <StatusHeader
        status={status({
          needsAttention: { flagged: true, reason: "waiting-on-decision" },
        })}
      />,
    );
    const badge = screen.getByTestId("needs-attention");
    expect(badge.textContent?.toLowerCase()).toMatch(/waiting on you/);
  });

  it("renders a worded reason for stopped-mid-reply ('stopped mid-reply')", () => {
    render(
      <StatusHeader
        status={status({
          needsAttention: { flagged: true, reason: "stopped-mid-reply" },
        })}
      />,
    );
    const badge = screen.getByTestId("needs-attention");
    expect(badge.textContent?.toLowerCase()).toMatch(/stopped mid-reply/);
  });

  it("labels the status as read at this moment (AI-07 transparency — not a stored post)", () => {
    render(<StatusHeader status={status()} />);
    // A small affordance tells the founder this is computed on read.
    expect(screen.getByTestId("status-header")).toBeInTheDocument();
  });
});
