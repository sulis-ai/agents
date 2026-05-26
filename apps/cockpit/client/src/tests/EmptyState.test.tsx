// WP-012 — <EmptyState> tests.
//
// Per WP Contract + TDD §6.2: when zero changes exist, the dashboard
// shows founder-readable copy telling them how to start one.

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { EmptyState } from "../components/EmptyState";

describe("<EmptyState>", () => {
  it("renders the 'nothing in flight' headline", () => {
    const { getByText } = render(<EmptyState />);
    expect(getByText(/nothing in flight/i)).toBeInTheDocument();
  });

  it("includes the /sulis:change start command pointer", () => {
    const { container } = render(<EmptyState />);
    // The full command lives in a <code> block; assert substring on the
    // rendered text so quoting style is not load-bearing.
    expect(container.textContent).toContain("/sulis:change start");
  });
});
