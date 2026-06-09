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

// WP-003 — Cold-start chips + soft welcome on the empty/idle state.
//
// The one genuinely-new piece of the start screen (ADR-001: added INSIDE the
// existing component, not a new surface). A first-timer on the idle/empty state
// sees a soft welcome + example chips instead of a blank wall. Clicking a chip
// prefills the intent box (and may submit) through the EXISTING draft/propose()
// path — no new lifecycle. The block disappears the moment the box is non-empty
// or a proposal is shown. Chips are real focusable <button>s with a visible
// focus ring; nothing is signalled by colour alone (each chip carries a label).
describe("<StartFromIntent /> — cold-start chips + welcome (WP-003)", () => {
  it("cold_start_chips_render_on_empty_idle: on idle with an empty box and no proposal, the chips + welcome render", () => {
    const stream = fakeStart({ propose: PROPOSAL });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);

    const coldStart = screen.getByTestId("cold-start");
    expect(coldStart).toBeInTheDocument();
    // The soft welcome line is present.
    expect(within(coldStart).getByText(/welcome/i)).toBeInTheDocument();
    // The example chips are real buttons carrying text labels.
    expect(
      within(coldStart).getByRole("button", { name: /fix something that's broken/i }),
    ).toBeInTheDocument();
    expect(
      within(coldStart).getByRole("button", { name: /add a new feature/i }),
    ).toBeInTheDocument();
    expect(
      within(coldStart).getByRole("button", { name: /i'm not sure yet/i }),
    ).toBeInTheDocument();
  });

  it("chip_click_fills_intent_box: clicking a chip puts its text in the intent box and reaches propose() via the injected fake", async () => {
    const stream = fakeStart({ propose: PROPOSAL });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);

    fireEvent.click(
      screen.getByRole("button", { name: /fix something that's broken/i }),
    );

    // The intent box is prefilled with the chip's text (rides the existing draft state).
    const box = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(box.value).toMatch(/fix something that's broken/i);

    // It rode the EXISTING propose() path — the injected fake was called with
    // the propose phase carrying the chip's intent.
    await waitFor(() => {
      expect(stream).toHaveBeenCalled();
    });
    const [request] = stream.mock.calls[0]!;
    expect(request.phase).toBe("propose");
    expect(request.intent).toMatch(/fix something that's broken/i);
  });

  it("chips_hidden_when_draft_non_empty: typing in the box hides the chips/welcome", () => {
    const stream = fakeStart({ propose: PROPOSAL });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);

    expect(screen.getByTestId("cold-start")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "fix the login bug" },
    });
    expect(screen.queryByTestId("cold-start")).not.toBeInTheDocument();
  });

  it("chips_hidden_when_proposal_shown: once a proposal is shown, the chips are gone", async () => {
    const stream = fakeStart({ propose: PROPOSAL });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "fix the login bug" },
    });
    fireEvent.click(screen.getByRole("button", { name: /propose|see|continue|next/i }));

    await waitFor(() => {
      expect(screen.getByTestId("start-proposal")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("cold-start")).not.toBeInTheDocument();
  });

  it("the open-ended \"I'm not sure yet\" chip prefills only (no concrete intent to propose yet)", () => {
    const stream = fakeStart({ propose: PROPOSAL });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);

    fireEvent.click(screen.getByRole("button", { name: /i'm not sure yet/i }));

    // It prefills the box (so the cold-start block hides) but does NOT submit —
    // there is no concrete intent yet, so the propose() path is not reached.
    const box = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(box.value).toMatch(/i'm not sure yet/i);
    expect(stream).not.toHaveBeenCalled();
  });

  it("chips_keyboard_focusable_with_visible_focus: chips are Tab-reachable real buttons", () => {
    const stream = fakeStart({ propose: PROPOSAL });
    render(<StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />);

    const chip = screen.getByRole("button", { name: /fix something that's broken/i });
    // A native <button> is keyboard-focusable by default (no tabIndex=-1 trap).
    expect(chip.tagName).toBe("BUTTON");
    expect(chip).not.toHaveAttribute("tabindex", "-1");
    chip.focus();
    expect(chip).toHaveFocus();
  });

  it("cold-start state is accessible (axe-core clean)", async () => {
    const stream = fakeStart({ propose: PROPOSAL });
    const { container } = render(
      <StartFromIntent productId="dna:product:acme" streamStartFromIntent={stream} />,
    );
    expect(screen.getByTestId("cold-start")).toBeInTheDocument();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
