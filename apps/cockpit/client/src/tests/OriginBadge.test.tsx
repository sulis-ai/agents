// WP-P10 — <OriginBadge /> tests (signed `origin-badge-and-lens.html`).
//
// The worded change-origin badge: Autonomous (bolt) / Assisted · likely
// (chat-bubble) / Origin unknown (question-mark-circle). Worded, never
// colour-alone (WCAG 1.4.1). The "· likely" hedge appears ONLY for an inferred
// attribution and is dropped when "recorded" (driven by the backend flag — no
// client-side guessing). As a button it carries aria-expanded + a caret
// (progressive disclosure); as a label it is static.

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import type { Origin } from "../../../shared/api-types";
import { OriginBadge } from "../components/OriginBadge";

const autonomous: Origin = {
  kind: "autonomous",
  run: { runId: "run-1", workflow: "Specify pass", outcome: "completed" },
  confidence: 0.88,
  attribution: "inferred",
};
const assistedInferred: Origin = {
  kind: "assisted",
  conversation: { conversationId: "c1", turn: 14, summary: "Reworked the cart total." },
  attribution: "inferred",
};
const assistedRecorded: Origin = { ...assistedInferred, attribution: "recorded" };
const unknown: Origin = {
  kind: "unknown",
  reason: "We couldn’t match this to a run or a conversation.",
  attribution: "inferred",
};

describe("<OriginBadge /> — worded, never colour-alone (WP-P10)", () => {
  it("words autonomous", () => {
    render(<OriginBadge origin={autonomous} />);
    expect(screen.getByText("Autonomous")).toBeInTheDocument();
  });

  it("words assisted with the '· likely' hedge when inferred", () => {
    render(<OriginBadge origin={assistedInferred} />);
    expect(screen.getByText("Assisted")).toBeInTheDocument();
    expect(screen.getByText(/· likely/)).toBeInTheDocument();
  });

  it("drops the '· likely' hedge when the attribution is recorded", () => {
    render(<OriginBadge origin={assistedRecorded} />);
    expect(screen.getByText("Assisted")).toBeInTheDocument();
    expect(screen.queryByText(/· likely/)).not.toBeInTheDocument();
  });

  it("words the unknown origin", () => {
    render(<OriginBadge origin={unknown} />);
    expect(screen.getByText("Origin unknown")).toBeInTheDocument();
  });

  it("renders a static label by default (no button, no aria-expanded)", () => {
    render(<OriginBadge origin={autonomous} />);
    const badge = screen.getByTestId("origin-badge");
    expect(badge.tagName).toBe("SPAN");
    expect(badge).not.toHaveAttribute("aria-expanded");
  });

  it("renders a disclosure button with aria-expanded + controls when onToggle is set", () => {
    const onToggle = vi.fn();
    render(
      <OriginBadge
        origin={assistedInferred}
        onToggle={onToggle}
        expanded={false}
        controls="trace-1"
      />,
    );
    const badge = screen.getByTestId("origin-badge");
    expect(badge.tagName).toBe("BUTTON");
    expect(badge).toHaveAttribute("aria-expanded", "false");
    expect(badge).toHaveAttribute("aria-controls", "trace-1");
    fireEvent.click(badge);
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <>
        <OriginBadge origin={autonomous} />
        <OriginBadge origin={assistedInferred} onToggle={() => {}} controls="t" />
        <OriginBadge origin={unknown} />
      </>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
