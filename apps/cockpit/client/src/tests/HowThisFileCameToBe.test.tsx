// WP-P10/P11 — <HowThisFileCameToBe /> tests.
//
// The open-file provenance panel: calls useFileOrigin(changeId, path) and shows
// the worded origin badge + its one-click trace —
//   autonomous → run label + confidence, a jump to the Provenance run log;
//   assisted   → the conversation Turn Card summary + "Open conversation →";
//   unknown    → the plain reason (honest, never a guess).
// Inferred origins show the honest "inferred from timing" note. Collapsible
// (aria-expanded). Loading + a calm error/empty state are handled.
//
// useFileOrigin is mocked so the panel's branching is tested in isolation (the
// hook itself — apiGet over GET …/origin?path= — is WP-P09's concern).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { axe } from "jest-axe";
import type { OriginView } from "../../../shared/api-types";

const useFileOrigin = vi.fn();
vi.mock("../api/useOrigin", () => ({
  useFileOrigin: (changeId: string, path: string) =>
    useFileOrigin(changeId, path),
}));

import { HowThisFileCameToBe } from "../components/HowThisFileCameToBe";

function ok(origin: OriginView["origin"], path = "src/cart.ts") {
  return {
    isLoading: false,
    isError: false,
    data: { changeId: "01XYZ", path, origin } as OriginView,
  };
}

beforeEach(() => {
  useFileOrigin.mockReset();
});

describe("<HowThisFileCameToBe /> — open-file panel (WP-P10/P11)", () => {
  it("shows a loading state while the origin is in flight", () => {
    useFileOrigin.mockReturnValue({ isLoading: true, isError: false, data: undefined });
    render(<HowThisFileCameToBe changeId="01XYZ" path="src/cart.ts" />);
    expect(screen.getByText(/Working out how this file came to be/)).toBeInTheDocument();
  });

  it("falls back calmly when the origin can't be loaded", () => {
    useFileOrigin.mockReturnValue({ isLoading: false, isError: true, data: undefined });
    render(<HowThisFileCameToBe changeId="01XYZ" path="src/cart.ts" />);
    expect(
      screen.getByText(/couldn’t work out how this file came to be/),
    ).toBeInTheDocument();
  });

  it("assisted → Turn Card summary + 'Open conversation' jump + the inferred note", () => {
    const onSelectView = vi.fn();
    useFileOrigin.mockReturnValue(
      ok({
        kind: "assisted",
        conversation: {
          conversationId: "c1",
          turn: 14,
          summary: "Reworked the cart total so discounts apply before tax.",
        },
        attribution: "inferred",
      }),
    );
    render(
      <HowThisFileCameToBe
        changeId="01XYZ"
        path="src/cart.ts"
        onSelectView={onSelectView}
      />,
    );
    expect(screen.getByText("How this file came to be")).toBeInTheDocument();
    // worded badge with the inferred hedge
    expect(screen.getByText("Assisted")).toBeInTheDocument();
    expect(screen.getByText(/· likely/)).toBeInTheDocument();
    // the Turn Card summary
    expect(
      within(screen.getByTestId("origin-trace")).getByText(/discounts apply before tax/),
    ).toBeInTheDocument();
    // honest inferred-from-timing note
    expect(screen.getByTestId("origin-inferred-note")).toBeInTheDocument();
    // the jump
    fireEvent.click(screen.getByTestId("origin-open-conversation"));
    expect(onSelectView).toHaveBeenCalledWith("conversation");
  });

  it("autonomous → run label + confidence + a jump to the run log", () => {
    const onSelectView = vi.fn();
    useFileOrigin.mockReturnValue(
      ok({
        kind: "autonomous",
        run: { runId: "r1", workflow: "Specify pass", outcome: "completed" },
        confidence: 0.88,
        attribution: "inferred",
      }),
    );
    render(
      <HowThisFileCameToBe
        changeId="01XYZ"
        path="src/checkout.ts"
        onSelectView={onSelectView}
      />,
    );
    expect(screen.getByText("Autonomous")).toBeInTheDocument();
    const trace = screen.getByTestId("origin-trace");
    expect(within(trace).getByText("Specify pass")).toBeInTheDocument();
    expect(within(trace).getByText("88% confident")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("origin-open-runlog"));
    expect(onSelectView).toHaveBeenCalledWith("provenance");
  });

  it("recorded autonomous → no inferred note (the badge flips with no UI change)", () => {
    useFileOrigin.mockReturnValue(
      ok({
        kind: "autonomous",
        run: { runId: "r1", workflow: "Specify pass", outcome: "completed" },
        confidence: 0.88,
        attribution: "recorded",
      }),
    );
    render(<HowThisFileCameToBe changeId="01XYZ" path="src/checkout.ts" />);
    expect(screen.queryByTestId("origin-inferred-note")).not.toBeInTheDocument();
  });

  it("unknown → the plain reason, no fabricated guess", () => {
    useFileOrigin.mockReturnValue(
      ok({
        kind: "unknown",
        reason: "We couldn’t match this to a run or a conversation.",
        attribution: "inferred",
      }),
    );
    render(<HowThisFileCameToBe changeId="01XYZ" path="README.md" />);
    expect(screen.getByText("Origin unknown")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("origin-trace")).getByText(
        /couldn’t match this to a run or a conversation/,
      ),
    ).toBeInTheDocument();
  });

  it("is collapsible — the trace hides when the header is toggled", () => {
    useFileOrigin.mockReturnValue(
      ok({
        kind: "unknown",
        reason: "No match.",
        attribution: "inferred",
      }),
    );
    render(<HowThisFileCameToBe changeId="01XYZ" path="README.md" />);
    const toggle = screen.getByTestId("file-origin-toggle");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByTestId("origin-trace")).toBeInTheDocument();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("origin-trace")).not.toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    useFileOrigin.mockReturnValue(
      ok({
        kind: "assisted",
        conversation: { conversationId: "c1", turn: 3, summary: "Did a thing." },
        attribution: "inferred",
      }),
    );
    const { container } = render(
      <HowThisFileCameToBe
        changeId="01XYZ"
        path="src/cart.ts"
        onSelectView={() => {}}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
