// WP-005 — <WaitingOnYou> (RED).
//
// The loud, full-width centered foot read shown ONLY when the change is
// waiting on the founder. Warning-triangle icon + bold "Waiting on you" +
// a short truncating `why`. Stands out by WEIGHT (1.5px warning border + bold
// label) — never colour alone. The `why` truncates first; the icon + label
// never wrap-drop (WP Contract / TDD §5).

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { WaitingOnYou } from "../components/WaitingOnYou";

describe("<WaitingOnYou> — the loud single foot read (WP-005)", () => {
  it("renders the bold 'Waiting on you' label", () => {
    const { getByText } = render(<WaitingOnYou why="picking an approach" />);
    expect(getByText(/waiting on you/i)).toBeInTheDocument();
  });

  it("renders the why text", () => {
    const { getByText } = render(<WaitingOnYou why="picking an approach" />);
    expect(getByText(/picking an approach/i)).toBeInTheDocument();
  });

  it("renders a (decorative, aria-hidden) warning-triangle icon — state by shape, not colour alone", () => {
    const { container } = render(<WaitingOnYou why="x" />);
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("carries the truncating-why class so a long why ellipsises (icon + label never drop)", () => {
    const { container } = render(
      <WaitingOnYou why="a very long reason that must truncate before it ever wraps the foot line" />,
    );
    const why = container.querySelector('[data-waiting-why]');
    expect(why).toBeTruthy();
    expect((why as HTMLElement).className).toMatch(/why/);
  });

  it("renders even when why is empty (icon + label still present)", () => {
    const { getByText, container } = render(<WaitingOnYou why="" />);
    expect(getByText(/waiting on you/i)).toBeInTheDocument();
    expect(container.querySelector("svg")).toBeTruthy();
  });
});
