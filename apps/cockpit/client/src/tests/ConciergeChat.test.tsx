// WP-009 — <ConciergeChat /> test (FR-33/34/N8/N9; ADR-006; the SIGNED contract).
//
// The concierge front door: the founder asks a plain-English question and the
// read-only answer streams back (REUSING the chat composer idiom + the SSE
// client). It points at /api/concierge/query, NOT a parallel UI (EP-03).
//
//   - ask → streamed read-only answer (state → chunk* → complete);
//   - the answer wears a "read-only — I only looked" honesty tag (the front
//     door performs no write/mint/start itself, FR-33/N8);
//   - on a `route` hint the front door OFFERS the confirm-gated next step
//     (onboarding / start-from-intent) and does NOT act inline (FR-N9);
//   - a bridge-unreachable answer shows a clear failure;
//   - an empty world (route=onboarding) prompts onboarding (UC-09→UC-07);
//   - no write/mint/start is performed from this surface.
//
// We inject a fake `streamQuery` so the component is tested without a network.

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";

import { ConciergeChat } from "../components/ConciergeChat";
import type { ConciergeStreamEvent } from "../../../shared/api-types";

function fakeStream(events: ConciergeStreamEvent[]) {
  return vi.fn(
    async (
      _question: string,
      onEvent: (e: ConciergeStreamEvent) => void,
      _productId?: string,
    ) => {
      for (const e of events) onEvent(e);
    },
  );
}

const READONLY_ANSWER: ConciergeStreamEvent[] = [
  { type: "state", state: "thinking" },
  { type: "state", state: "replying" },
  { type: "chunk", text: "Found it — " },
  { type: "chunk", text: "fix-login-redirect is in Implement." },
  { type: "complete", route: null },
];

const INVESTIGATE_ROUTE: ConciergeStreamEvent[] = [
  { type: "state", state: "replying" },
  { type: "chunk", text: "That's a piece of work — I'll give it its own change." },
  { type: "complete", route: "start-from-intent" },
];

const ONBOARDING_ROUTE: ConciergeStreamEvent[] = [
  { type: "state", state: "replying" },
  { type: "chunk", text: "Let's get you set up." },
  { type: "complete", route: "onboarding" },
];

const UNREACHABLE: ConciergeStreamEvent[] = [
  {
    type: "error",
    code: "SESSION_UNREACHABLE",
    message: "couldn't reach the concierge",
  },
];

function ask(question: string) {
  const box = screen.getByLabelText(/ask the concierge/i);
  fireEvent.change(box, { target: { value: question } });
  fireEvent.keyDown(box, { key: "Enter" });
}

describe("<ConciergeChat /> — the read-only front door (FR-33; signed contract)", () => {
  it("renders the ask box with the front-door hero + slash hint", () => {
    render(<ConciergeChat streamQuery={fakeStream([])} />);
    expect(screen.getByLabelText(/ask the concierge/i)).toBeInTheDocument();
    expect(screen.getByText(/for commands/i)).toBeInTheDocument();
  });

  it("offers suggestion chips (What needs my attention? / in flight / start)", () => {
    render(<ConciergeChat streamQuery={fakeStream([])} />);
    const chips = screen.getAllByTestId("concierge-chip");
    expect(chips.length).toBeGreaterThan(0);
  });

  it("asks → streams a read-only answer and wears the read-only honesty tag", async () => {
    render(<ConciergeChat streamQuery={fakeStream(READONLY_ANSWER)} />);
    ask("which change was the login fix in?");

    const answer = await screen.findByTestId("concierge-answer");
    expect(answer.textContent).toContain("fix-login-redirect is in Implement.");
    // The read-only honesty tag: it looked, it did not act.
    expect(screen.getByTestId("readonly-tag")).toBeInTheDocument();
  });

  it("a read-only answer OFFERS no act affordance (route=null → no buttons)", async () => {
    render(<ConciergeChat streamQuery={fakeStream(READONLY_ANSWER)} />);
    ask("what have I got in flight?");
    await screen.findByTestId("concierge-answer");
    expect(screen.queryByTestId("route-offer")).not.toBeInTheDocument();
  });
});

describe("<ConciergeChat /> — consequential intent is OFFERED, never done inline (FR-N9)", () => {
  it("an investigation answer OFFERS a confirm-gated start-from-intent step (does not act)", async () => {
    const onRoute = vi.fn();
    render(
      <ConciergeChat streamQuery={fakeStream(INVESTIGATE_ROUTE)} onRoute={onRoute} />,
    );
    ask("look into why sign-ups dropped");

    const offer = await screen.findByTestId("route-offer");
    expect(offer.textContent?.toLowerCase()).toContain("change");
    // The offer is a CTA — nothing was acted on yet (FR-N9 containment).
    expect(onRoute).not.toHaveBeenCalled();

    // Only when the founder confirms does the route fire (confirm-gated).
    fireEvent.click(screen.getByTestId("route-confirm"));
    expect(onRoute).toHaveBeenCalledWith("start-from-intent");
  });

  it("an empty-world answer OFFERS onboarding (UC-09→UC-07), confirm-gated", async () => {
    const onRoute = vi.fn();
    render(
      <ConciergeChat streamQuery={fakeStream(ONBOARDING_ROUTE)} onRoute={onRoute} />,
    );
    ask("set me up");

    const offer = await screen.findByTestId("route-offer");
    expect(offer.textContent?.toLowerCase()).toMatch(/set you up|get started|onboard/);
    expect(onRoute).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("route-confirm"));
    expect(onRoute).toHaveBeenCalledWith("onboarding");
  });
});

describe("<ConciergeChat /> — failure is honest (FR-19)", () => {
  it("shows a clear failure when the bridge is unreachable", async () => {
    render(<ConciergeChat streamQuery={fakeStream(UNREACHABLE)} />);
    ask("anything?");
    const err = await screen.findByTestId("concierge-error");
    expect(err).toHaveAttribute("role", "alert");
    expect(err.textContent?.toLowerCase()).toContain("reach");
  });
});

describe("<ConciergeChat /> — a11y (axe)", () => {
  it("has no axe violations on the front door", async () => {
    const { container } = render(<ConciergeChat streamQuery={fakeStream([])} />);
    await waitFor(async () => {
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
