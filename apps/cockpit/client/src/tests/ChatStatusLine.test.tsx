// WP-002 — <ChatStatusLine> tests (TDD §2.1 + §3, ADR-002 + ADR-004).
//
// The shared, presentational status line above the message box. It derives one
// of three mutually-exclusive slots from the EXISTING hook lifecycle + a "reply
// produced this session" flag + a presentational "dismissed" latch — it adds NO
// state to useChatStream / useProductChat (ADR-002):
//
//   - working  when state ∈ {replying, resuming, spawning}
//   - finished when replyProduced && state === "ready" && not yet dismissed
//   - chips    otherwise (idle / your-turn, or after dismissal)
//   - interrupted / failed → render NOTHING in the slot (the caller owns those
//     bands above the slot) — the line never claims "finished" on a broken or
//     failed turn (FR-19/FR-22 preserved).
//
// Exactly one of {chips, working, finished} renders at any time (mutual
// exclusivity). The line is a live region (role="status" aria-live="polite")
// so the working→finished transition is announced (WCAG); working vs finished
// differ by icon AND wording, never by colour alone (WCAG 1.4.1).
//
// These tests fail today — the component does not exist yet.

import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import type { ChatLifecycle } from "../api/useChatStream";
import {
  ChatStatusLine,
  statusSlot,
  type ChatStatusKind,
} from "../components/ChatStatusLine";

const CHIPS = (
  <div data-testid="caller-chips">
    <button type="button" data-testid="suggestion-chip">
      Suggest something
    </button>
  </div>
);

/** Render helper: the line with caller-supplied chips. */
function renderLine(
  state: ChatLifecycle,
  replyProduced: boolean,
  onDismissFinished?: () => void,
) {
  return render(
    <ChatStatusLine
      state={state}
      replyProduced={replyProduced}
      chips={CHIPS}
      onDismissFinished={onDismissFinished}
    />,
  );
}

describe("statusSlot (pure derivation)", () => {
  it("replying → working", () => {
    expect(statusSlot("replying", false, false)).toBe<ChatStatusKind>(
      "working",
    );
  });

  it("resuming / spawning → working (honest waking/starting sub-states)", () => {
    expect(statusSlot("resuming", false, false)).toBe<ChatStatusKind>(
      "working",
    );
    expect(statusSlot("spawning", false, false)).toBe<ChatStatusKind>(
      "working",
    );
  });

  it("ready + replyProduced + not dismissed → finished", () => {
    expect(statusSlot("ready", true, false)).toBe<ChatStatusKind>("finished");
  });

  it("ready + replyProduced + dismissed → chips (returns to chips once read)", () => {
    expect(statusSlot("ready", true, true)).toBe<ChatStatusKind>("chips");
  });

  it("ready + !replyProduced → chips (idle / your-turn)", () => {
    expect(statusSlot("ready", false, false)).toBe<ChatStatusKind>("chips");
  });

  it("interrupted / failed → neither working nor finished (caller owns the band)", () => {
    // Even with a reply produced, a broken/failed turn must NOT read finished.
    expect(statusSlot("interrupted", true, false)).not.toBe<ChatStatusKind>(
      "finished",
    );
    expect(statusSlot("interrupted", true, false)).not.toBe<ChatStatusKind>(
      "working",
    );
    expect(statusSlot("failed", true, false)).not.toBe<ChatStatusKind>(
      "finished",
    );
    expect(statusSlot("failed", true, false)).not.toBe<ChatStatusKind>(
      "working",
    );
  });
});

describe("<ChatStatusLine>", () => {
  it("replying → working line, no chips", () => {
    const { queryByTestId, getByText } = renderLine("replying", false);
    expect(queryByTestId("status-working")).toBeInTheDocument();
    expect(getByText(/Sulis is working/i)).toBeInTheDocument();
    expect(queryByTestId("status-finished")).not.toBeInTheDocument();
    expect(queryByTestId("caller-chips")).not.toBeInTheDocument();
  });

  it("resuming and spawning also show the working line", () => {
    for (const state of ["resuming", "spawning"] as const) {
      const { queryByTestId, unmount } = renderLine(state, false);
      expect(queryByTestId("status-working")).toBeInTheDocument();
      expect(queryByTestId("caller-chips")).not.toBeInTheDocument();
      unmount();
    }
  });

  it("ready + replyProduced → finished line, no chips, no working", () => {
    const { queryByTestId, getByText } = renderLine("ready", true);
    expect(queryByTestId("status-finished")).toBeInTheDocument();
    expect(getByText(/Finished — over to you/i)).toBeInTheDocument();
    expect(queryByTestId("status-working")).not.toBeInTheDocument();
    expect(queryByTestId("caller-chips")).not.toBeInTheDocument();
  });

  it("ready + !replyProduced → chips slot (idle / your-turn)", () => {
    const { queryByTestId } = renderLine("ready", false);
    expect(queryByTestId("caller-chips")).toBeInTheDocument();
    expect(queryByTestId("status-working")).not.toBeInTheDocument();
    expect(queryByTestId("status-finished")).not.toBeInTheDocument();
  });

  it("interrupted → neither working nor finished line in the slot (and no chips)", () => {
    const { queryByTestId } = renderLine("interrupted", true);
    expect(queryByTestId("status-working")).not.toBeInTheDocument();
    expect(queryByTestId("status-finished")).not.toBeInTheDocument();
    expect(queryByTestId("caller-chips")).not.toBeInTheDocument();
  });

  it("failed → neither working nor finished line in the slot (and no chips)", () => {
    const { queryByTestId } = renderLine("failed", true);
    expect(queryByTestId("status-working")).not.toBeInTheDocument();
    expect(queryByTestId("status-finished")).not.toBeInTheDocument();
    expect(queryByTestId("caller-chips")).not.toBeInTheDocument();
  });

  it("renders exactly one of {chips, working, finished} across every lifecycle state (mutual exclusivity)", () => {
    const cases: Array<[ChatLifecycle, boolean]> = [
      ["ready", false],
      ["ready", true],
      ["resuming", false],
      ["spawning", false],
      ["replying", false],
      ["replying", true],
      ["interrupted", true],
      ["failed", true],
    ];
    for (const [state, replyProduced] of cases) {
      const { queryByTestId, unmount } = renderLine(state, replyProduced);
      const shown = [
        queryByTestId("caller-chips"),
        queryByTestId("status-working"),
        queryByTestId("status-finished"),
      ].filter(Boolean);
      // interrupted/failed legitimately show ZERO; everything else shows EXACTLY
      // one. Never two — that is the de-collision invariant.
      expect(shown.length).toBeLessThanOrEqual(1);
      if (state !== "interrupted" && state !== "failed") {
        expect(shown.length).toBe(1);
      }
      unmount();
    }
  });

  it("the finished line dismisses to chips on founder interaction (onDismissFinished)", () => {
    const onDismiss = vi.fn();
    const { queryByTestId, getByTestId } = renderLine("ready", true, onDismiss);
    expect(queryByTestId("status-finished")).toBeInTheDocument();
    // Acting on the inline "Got it" affordance dismisses it back to chips.
    fireEvent.click(getByTestId("status-finished-dismiss"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
    // After dismissal the slot returns to the chips.
    expect(queryByTestId("caller-chips")).toBeInTheDocument();
    expect(queryByTestId("status-finished")).not.toBeInTheDocument();
  });

  it("is a polite live region (role=status aria-live=polite) when it shows a status", () => {
    const { getByRole } = renderLine("replying", false);
    const region = getByRole("status");
    expect(region.getAttribute("aria-live")).toBe("polite");
  });

  it("working vs finished differ by icon AND wording, never by colour alone (WCAG 1.4.1)", () => {
    const working = renderLine("replying", false);
    const workingIcon = working.getByTestId("status-icon-working");
    const workingText = working.getByText(/Sulis is working/i).textContent;
    working.unmount();

    const finished = renderLine("ready", true);
    const finishedIcon = finished.getByTestId("status-icon-finished");
    const finishedText = finished.getByText(
      /Finished — over to you/i,
    ).textContent;

    // Distinct icons (different test ids) AND distinct wording.
    expect(workingIcon).toBeTruthy();
    expect(finishedIcon).toBeTruthy();
    expect(workingText).not.toBe(finishedText);
  });

  it("has no axe violations in the working state", async () => {
    const { container } = renderLine("replying", false);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no axe violations in the finished state", async () => {
    const { container } = renderLine("ready", true);
    expect(await axe(container)).toHaveNoViolations();
  });
});
