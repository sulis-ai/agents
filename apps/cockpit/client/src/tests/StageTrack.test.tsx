// WP-004 — <StageTrack> tests (FR-04).
//
// The thread's "where am I" track: the six lifecycle stages in order
// (recon→specify→design→implement→review→ship) with the change's current
// stage marked, earlier stages shown done, later stages pending (FR-04).
//
// Colour is decorative reinforcement only — each stage step carries a
// text label AND a state word (done / now / pending), so the track is
// fully legible without colour (WCAG 1.4.1; the SIGNED visual contract's
// colour-independent status rule). State is exposed via data-state +
// aria-current for assertion + a11y.

import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StageTrack } from "../components/StageTrack";

describe("<StageTrack /> (FR-04)", () => {
  it("renders all six lifecycle stages in order", () => {
    render(<StageTrack stage="design" />);
    const steps = screen.getAllByTestId("stage-step");
    expect(steps).toHaveLength(6);
    expect(steps.map((s) => s.getAttribute("data-stage"))).toEqual([
      "recon",
      "specify",
      "design",
      "implement",
      "review",
      "ship",
    ]);
  });

  it("marks the current stage as 'now' with aria-current", () => {
    render(<StageTrack stage="design" />);
    const steps = screen.getAllByTestId("stage-step");
    const current = steps.find(
      (s) => s.getAttribute("data-stage") === "design",
    )!;
    expect(current.getAttribute("data-state")).toBe("now");
    expect(current.getAttribute("aria-current")).toBe("step");
    // Carries a visible state word, not colour alone.
    expect(within(current).getByText(/now/i)).toBeInTheDocument();
  });

  it("marks stages before the current one as 'done'", () => {
    render(<StageTrack stage="design" />);
    const steps = screen.getAllByTestId("stage-step");
    const recon = steps.find((s) => s.getAttribute("data-stage") === "recon")!;
    const specify = steps.find(
      (s) => s.getAttribute("data-stage") === "specify",
    )!;
    expect(recon.getAttribute("data-state")).toBe("done");
    expect(specify.getAttribute("data-state")).toBe("done");
  });

  it("marks stages after the current one as 'pending'", () => {
    render(<StageTrack stage="design" />);
    const steps = screen.getAllByTestId("stage-step");
    const implement = steps.find(
      (s) => s.getAttribute("data-stage") === "implement",
    )!;
    const ship = steps.find((s) => s.getAttribute("data-stage") === "ship")!;
    expect(implement.getAttribute("data-state")).toBe("pending");
    expect(ship.getAttribute("data-state")).toBe("pending");
  });

  it("shows the human stage name on each step", () => {
    render(<StageTrack stage="recon" />);
    expect(screen.getByText("Recon")).toBeInTheDocument();
    expect(screen.getByText("Implement")).toBeInTheDocument();
    expect(screen.getByText("Ship")).toBeInTheDocument();
  });

  it("treats a terminal 'shipped' change as all-six-done (the workflow is complete)", () => {
    render(<StageTrack stage="shipped" />);
    const steps = screen.getAllByTestId("stage-step");
    expect(steps).toHaveLength(6);
    for (const s of steps) {
      expect(s.getAttribute("data-state")).toBe("done");
    }
  });
});
