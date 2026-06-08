// WP-006 — <BrainView> tests (FR-06/07).
//
// The right-panel "Brain" section: the entities the agent created for a
// change, GROUPED by kind, each with a count and a readable detail per
// item (FR-06/07). An empty brain shows a plain note (not a broken/empty
// shell). The component is presentational — it takes a BrainView prop
// (the data-fetch lives in useBrain) exactly like StageTrack/StatusHeader.
//
// Colour is decorative only: each group carries a text kind label + a
// numeric count, and each item a text title + a kind line, so the panel
// is fully legible without colour (the SIGNED visual contract's
// colour-independent rule; matches the contract's `.bgroup`/`.bitem`).

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { axe } from "jest-axe";
import type { BrainView as BrainViewModel } from "../../../shared/api-types";
import { BrainView } from "../components/BrainView";

function model(overrides: Partial<BrainViewModel> = {}): BrainViewModel {
  return {
    changeId: "01XYZ",
    groups: [
      {
        kind: "requirement",
        items: [
          {
            id: "dna:requirement:01R1",
            kind: "requirement",
            title: "Board lists changes in stage columns",
            detail: { id: "dna:requirement:01R1", state: "active" },
          },
          {
            id: "dna:requirement:01R2",
            kind: "requirement",
            title: "Send a message to a change's agent",
            detail: { id: "dna:requirement:01R2" },
          },
        ],
      },
      {
        kind: "decision",
        items: [
          {
            id: "dna:decision:01D1",
            kind: "decision",
            title: "Path A — canonical-as-spec",
            detail: {
              id: "dna:decision:01D1",
              decision: "Adopt Path A for v1.",
            },
          },
        ],
      },
    ],
    ...overrides,
  };
}

describe("<BrainView /> (FR-06/07)", () => {
  it("renders one group per kind with the kind label and item count", () => {
    render(<BrainView view={model()} />);
    const groups = screen.getAllByTestId("brain-group");
    expect(groups).toHaveLength(2);

    const req = groups.find(
      (g) => g.getAttribute("data-kind") === "requirement",
    )!;
    // The group head shows the kind label.
    const head = within(req).getByRole("heading");
    expect(head).toHaveTextContent(/requirement/i);
    // The count of items in the group is visible (the contract's "· 6").
    expect(within(req).getByText(/\b2\b/)).toBeInTheDocument();
    expect(within(req).getAllByTestId("brain-item")).toHaveLength(2);
  });

  it("shows each item's readable title", () => {
    render(<BrainView view={model()} />);
    expect(
      screen.getByText("Board lists changes in stage columns"),
    ).toBeInTheDocument();
    expect(screen.getByText("Path A — canonical-as-spec")).toBeInTheDocument();
  });

  it("opens a readable detail when an item is activated (FR-07)", () => {
    render(<BrainView view={model()} />);
    // Detail is not shown until the item is opened.
    expect(screen.queryByText(/Adopt Path A for v1\./)).not.toBeInTheDocument();
    const toggle = screen.getByRole("button", {
      name: /Path A — canonical-as-spec/,
    });
    fireEvent.click(toggle);
    expect(screen.getByText(/Adopt Path A for v1\./)).toBeInTheDocument();
  });

  it("shows a plain empty note when the brain has no entities", () => {
    render(<BrainView view={model({ groups: [] })} />);
    expect(screen.getByTestId("brain-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("brain-group")).not.toBeInTheDocument();
  });

  it("has no axe violations in the populated state", async () => {
    const { container } = render(<BrainView view={model()} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
