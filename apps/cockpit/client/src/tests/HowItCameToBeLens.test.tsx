// WP-P10 — <HowItCameToBeLens /> tests (signed `origin-badge-and-lens.html`).
//
// The Provenance "How it came to be" lens: the change's files grouped under
// "⚡ Autonomous (N)" / "💬 Assisted · likely (N)" / "Origin unknown (N)" with a
// one-line honesty banner. Light by design (group + count at the glance, expand
// a row to its trace — progressive disclosure). The "· likely" group hedge is
// driven by the backend attribution. Worded status never colour-alone.

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { axe } from "jest-axe";
import type { ChangeOriginView } from "../../../shared/api-types";
import { HowItCameToBeLens } from "../components/HowItCameToBeLens";

function view(overrides: Partial<ChangeOriginView> = {}): ChangeOriginView {
  return {
    changeId: "01XYZ",
    files: [
      {
        path: "src/checkout/checkout.ts",
        origin: {
          kind: "autonomous",
          run: { runId: "r1", workflow: "Specify pass", outcome: "completed" },
          confidence: 0.88,
          attribution: "inferred",
        },
      },
      {
        path: "src/checkout/pricing.ts",
        origin: {
          kind: "autonomous",
          run: { runId: "r1", workflow: "Specify pass", outcome: "completed" },
          confidence: 0.88,
          attribution: "inferred",
        },
      },
      {
        path: "src/checkout/cart.ts",
        origin: {
          kind: "assisted",
          conversation: {
            conversationId: "c1",
            turn: 14,
            summary: "Reworked the cart total so discounts apply before tax.",
          },
          attribution: "inferred",
        },
      },
      {
        path: "config.json",
        origin: {
          kind: "unknown",
          reason: "No run or conversation matched this change — we won’t guess.",
          attribution: "inferred",
        },
      },
    ],
    ...overrides,
  };
}

describe("<HowItCameToBeLens /> — grouped origins (WP-P10)", () => {
  it("shows the one-line honesty banner", () => {
    render(<HowItCameToBeLens view={view()} />);
    expect(
      screen.getByText(/Origins are inferred from timing/),
    ).toBeInTheDocument();
  });

  it("groups files by origin with counts", () => {
    render(<HowItCameToBeLens view={view()} />);
    expect(screen.getByTestId("lens-count-autonomous").textContent).toBe("2");
    expect(screen.getByTestId("lens-count-assisted").textContent).toBe("1");
    expect(screen.getByTestId("lens-count-unknown").textContent).toBe("1");
  });

  it("words each group; assisted carries the '· likely' hedge while inferred", () => {
    render(<HowItCameToBeLens view={view()} />);
    expect(
      within(screen.getByTestId("lens-group-autonomous")).getByText("Autonomous"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("lens-group-assisted")).getByText("Assisted · likely"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("lens-group-unknown")).getByText("Origin unknown"),
    ).toBeInTheDocument();
  });

  it("drops the assisted hedge when the rows are recorded", () => {
    const recorded = view({
      files: [
        {
          path: "src/cart.ts",
          origin: {
            kind: "assisted",
            conversation: { conversationId: "c1", turn: 14, summary: "Reworked." },
            attribution: "recorded",
          },
        },
      ],
    });
    render(<HowItCameToBeLens view={recorded} />);
    const group = screen.getByTestId("lens-group-assisted");
    expect(within(group).getByText("Assisted")).toBeInTheDocument();
    expect(within(group).queryByText("Assisted · likely")).not.toBeInTheDocument();
  });

  it("keeps it light — a row's trace is hidden until the row is expanded", () => {
    render(<HowItCameToBeLens view={view()} />);
    expect(screen.queryByTestId("lens-detail")).not.toBeInTheDocument();
    const assistedRow = within(screen.getByTestId("lens-group-assisted")).getByTestId(
      "lens-row",
    );
    fireEvent.click(assistedRow);
    const detail = screen.getByTestId("lens-detail");
    expect(within(detail).getByText(/discounts apply before tax/)).toBeInTheDocument();
  });

  it("jumps to the conversation from an expanded assisted row", () => {
    const onSelectView = vi.fn();
    render(<HowItCameToBeLens view={view()} onSelectView={onSelectView} />);
    fireEvent.click(
      within(screen.getByTestId("lens-group-assisted")).getByTestId("lens-row"),
    );
    fireEvent.click(screen.getByTestId("origin-open-conversation"));
    expect(onSelectView).toHaveBeenCalledWith("conversation");
  });

  it("shows the honest empty state when there are no changed files", () => {
    render(<HowItCameToBeLens view={view({ files: [] })} />);
    expect(screen.getByText(/No changed files to trace yet/)).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<HowItCameToBeLens view={view()} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
