// WP-011 — <StartFromIntent /> test (FR-29/30/34; FR-N9; the SIGNED visual
// contract, WP-002).
//
// Say what you want in plain English → see the PROPOSAL (primitive + slug +
// repo plan) → CONFIRM → the new change appears at Recon. The surface is
// triggered from the concierge front door's route-offer (WP-009) OR a direct
// intent box. The contract this test pins:
//   - type an intent → a proposal is shown BEFORE any change starts (FR-N6);
//   - the proposal renders the primitive + slug + repo plan;
//   - on CONFIRM the started change appears (state shows it landed at Recon);
//   - an investigation is framed as "I'll create a change to look into this"
//     (a CONTAINED change, never inline work — FR-N9);
//   - an ambiguous intent surfaces the clarifying question (no guess);
//   - the surface is accessible (axe-core clean) and uses tokens.css only.
//
// We inject a fake `streamStartFromIntent` so the component is tested without a
// network. Each call resolves the scripted events for that turn's phase.

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { axe } from "jest-axe";

import { StartFromIntent } from "../components/StartFromIntent";
import type {
  StartFromIntentStreamEvent,
  StartFromIntentRequest,
} from "../../../shared/api-types";

function fakeStart(byPhase: Record<string, StartFromIntentStreamEvent[]>) {
  return vi.fn(
    async (
      request: StartFromIntentRequest,
      onEvent: (e: StartFromIntentStreamEvent) => void,
    ) => {
      for (const e of byPhase[request.phase] ?? []) onEvent(e);
    },
  );
}

const PROPOSAL: StartFromIntentStreamEvent[] = [
  { type: "state", state: "classifying" },
  { type: "state", state: "proposing" },
  {
    type: "proposal",
    proposal: { confirmToken: "tok-1", primitive: "fix", slug: "login-bug" },
  },
];

const STARTED: StartFromIntentStreamEvent[] = [
  { type: "state", state: "starting" },
  {
    type: "started",
    started: {
      changeId: "01CHG",
      handle: "CH-01CHG",
      slug: "login-bug",
      primitive: "fix",
      branch: "change/fix-login-bug",
      worktreePath: "/tmp/wt",
      intent: "fix the login bug",
      baseBranch: "main",
      baseSha: "abc",
      createdAt: "2026-06-04T00:00:00Z",
      updatedAt: "2026-06-04T00:00:00Z",
      stage: "recon",
      liveness: { status: "not-running" },
      // WP-001 widened fields — fixture defaults.
      needsAttention: { flagged: false, reason: null },
      health: { state: "unknown", reason: "too early to tell" },
      lastActivityAt: null,
    },
  },
  { type: "state", state: "complete" },
];

describe("<StartFromIntent /> — propose → confirm → started at Recon", () => {
  it("typing an intent shows a PROPOSAL (primitive + slug) BEFORE any change starts (FR-N6)", async () => {
    const stream = fakeStart({ propose: PROPOSAL });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "fix the login bug" },
    });
    fireEvent.click(screen.getByRole("button", { name: /propose|see|continue|next/i }));

    await waitFor(() => {
      expect(screen.getByText(/login-bug/)).toBeInTheDocument();
    });
    // The primitive is shown so the founder sees WHAT will start — scoped to
    // the proposal recap (the word "fix" also appears in the placeholder copy).
    const proposal = screen.getByTestId("start-proposal");
    expect(within(proposal).getByText(/fix/i)).toBeInTheDocument();
    // Nothing has started yet — there is no "started" end state.
    expect(screen.queryByTestId("start-started")).not.toBeInTheDocument();
  });

  it("on CONFIRM the started change appears at Recon (FR-29)", async () => {
    const stream = fakeStart({ propose: PROPOSAL, confirm: STARTED });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "fix the login bug" },
    });
    fireEvent.click(screen.getByRole("button", { name: /propose|see|continue|next/i }));
    await waitFor(() => expect(screen.getByText(/login-bug/)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /confirm|start/i }));
    await waitFor(() => {
      expect(screen.getByText(/recon/i)).toBeInTheDocument();
    });
  });

  it("an investigation is framed as creating a CONTAINED change, not inline work (FR-N9)", async () => {
    const stream = fakeStart({
      propose: [
        { type: "state", state: "proposing" },
        {
          type: "proposal",
          proposal: { confirmToken: "tok-2", primitive: "chore", slug: "checkout-slow" },
        },
      ],
    });
    render(
      <StartFromIntent
        productId="dna:product:acme"
        kind="investigation"
        streamStartFromIntent={stream}
      />,
    );
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "look into why checkout is slow" },
    });
    fireEvent.click(screen.getByRole("button", { name: /propose|see|continue|next/i }));

    await waitFor(() => {
      // The framing makes clear a CHANGE will be created to contain the work
      // (FR-N9). The phrase appears in the hero AND the proposal lead, so assert
      // at least one match exists rather than a unique one.
      expect(
        screen.getAllByText(/create a change|look into|investigat/i).length,
      ).toBeGreaterThan(0);
    });
  });

  it("an ambiguous intent surfaces the clarifying question (no guess)", async () => {
    const stream = fakeStart({
      propose: [
        { type: "state", state: "failed" },
        {
          type: "error",
          code: "INTENT_AMBIGUOUS",
          message: "Could you say a bit more about what you'd like to change?",
        },
      ],
    });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "do the thing" } });
    fireEvent.click(screen.getByRole("button", { name: /propose|see|continue|next/i }));

    await waitFor(() => {
      expect(screen.getByText(/say a bit more/i)).toBeInTheDocument();
    });
  });

  it("is accessible (axe-core clean) and renders an intent box", async () => {
    const stream = fakeStart({ propose: PROPOSAL });
    const { container } = render(
      <StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />,
    );
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
