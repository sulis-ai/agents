// WP-005 — <Composer /> test (FR-16..23/26; AI-02/03; the SIGNED contract).
//
// The docked write surface: suggestion chips + free text + a slash-command
// hint (AI-02), Enter sends / Shift+Enter newlines, a live streaming reply
// render with a caret, pause/stop run-controls while replying (AI-03), the
// founder's own message in a NEUTRAL bubble (signed contract), honest
// lifecycle states in plain English (FR-23), send disabled while THIS change
// streams (FR-20), a mid-stream break shows "reply was interrupted" +
// preserves the partial (FR-22), an unreachable session shows a clear failure
// and does NOT show delivered (FR-19), and on resume an honest "resumed"
// indication (FR-26).
//
// We inject a fake `streamChat` so the component is tested without a network.

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";

import { Composer } from "../components/Composer";
import type { ChatStreamEvent } from "../../../shared/api-types";

function fakeStream(events: ChatStreamEvent[], opts: { hang?: boolean } = {}) {
  return vi.fn(
    async (
      _changeId: string,
      _prompt: string,
      onEvent: (e: ChatStreamEvent) => void,
    ) => {
      for (const e of events) onEvent(e);
      if (opts.hang) await new Promise(() => {}); // never resolves
    },
  );
}

const HAPPY: ChatStreamEvent[] = [
  { type: "state", state: "replying" },
  { type: "chunk", text: "On it — " },
  { type: "chunk", text: "wiring the brain view." },
  { type: "complete", resumed: false },
];

describe("<Composer /> — the docked write surface (signed contract)", () => {
  it("renders the send box with the slash + Enter/Shift hint (AI-02)", () => {
    render(<Composer changeId="01CHAT" streamChat={fakeStream([])} />);
    expect(
      screen.getByLabelText(/message this change's agent/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/for commands/i)).toBeInTheDocument();
    expect(screen.getByText(/shift/i)).toBeInTheDocument();
  });

  it("offers suggestion chips (AI-02 dual-mode input)", () => {
    render(<Composer changeId="01CHAT" streamChat={fakeStream([])} />);
    const chips = screen.getAllByTestId("suggestion-chip");
    expect(chips.length).toBeGreaterThan(0);
  });

  it("sends on Enter and renders the founder's own message in a neutral bubble", async () => {
    render(<Composer changeId="01CHAT" streamChat={fakeStream(HAPPY)} />);
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "Now wire the brain view." } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: false });

    const mine = await screen.findByTestId("user-message");
    expect(mine.textContent).toContain("Now wire the brain view.");
    // The neutral bubble class is the signed-contract idiom (alignment, not
    // a brand fill); we assert the data hook rather than the colour.
    expect(mine.getAttribute("data-sender")).toBe("you");
  });

  it("does NOT send on Shift+Enter (newline instead)", () => {
    const stream = fakeStream(HAPPY);
    render(<Composer changeId="01CHAT" streamChat={stream} />);
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "line one" } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    expect(stream).not.toHaveBeenCalled();
  });

  it("renders the streamed reply live and joins it on complete (FR-17/18)", async () => {
    render(<Composer changeId="01CHAT" streamChat={fakeStream(HAPPY)} />);
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.keyDown(box, { key: "Enter" });

    await waitFor(() =>
      expect(screen.getByTestId("agent-reply").textContent).toContain(
        "wiring the brain view.",
      ),
    );
  });

  it("shows pause/stop run-controls while the agent is replying (AI-03)", async () => {
    render(
      <Composer
        changeId="01CHAT"
        streamChat={fakeStream(HAPPY, { hang: true })}
      />,
    );
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.keyDown(box, { key: "Enter" });

    await waitFor(() =>
      expect(screen.getByTestId("run-controls")).toBeInTheDocument(),
    );
    expect(screen.getByLabelText(/pause the agent/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/stop the agent/i)).toBeInTheDocument();
  });

  it("disables send while THIS change is streaming (FR-20 one-in-flight)", async () => {
    render(
      <Composer
        changeId="01CHAT"
        streamChat={fakeStream(HAPPY, { hang: true })}
      />,
    );
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.keyDown(box, { key: "Enter" });

    const send = await screen.findByRole("button", { name: /^send$/i });
    await waitFor(() => expect(send).toBeDisabled());
  });

  it("reflects plain-English lifecycle states (FR-23): waking-the-change-up on resume", async () => {
    render(
      <Composer
        changeId="01CHAT"
        streamChat={fakeStream([
          { type: "state", state: "resuming" },
          { type: "chunk", text: "back" },
          { type: "complete", resumed: true },
        ])}
      />,
    );
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "continue" } });
    fireEvent.keyDown(box, { key: "Enter" });
    // On resume, an honest "resumed" indication (FR-26) — never "silently continued".
    await waitFor(() =>
      expect(
        screen.getByTestId("resumed-note").textContent?.toLowerCase(),
      ).toMatch(/resumed/),
    );
  });

  it("shows 'reply was interrupted' + preserves the partial on a mid-stream break (FR-22)", async () => {
    render(
      <Composer
        changeId="01CHAT"
        streamChat={fakeStream([
          { type: "state", state: "replying" },
          { type: "chunk", text: "partial answer" },
          { type: "state", state: "interrupted" },
        ])}
      />,
    );
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.keyDown(box, { key: "Enter" });
    await waitFor(() =>
      expect(screen.getByTestId("interrupted-note")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("agent-reply").textContent).toContain(
      "partial answer",
    );
  });

  it("shows a clear failure and does NOT show delivered when unreachable (FR-19)", async () => {
    render(
      <Composer
        changeId="01CHAT"
        streamChat={fakeStream([
          {
            type: "error",
            code: "SESSION_UNREACHABLE",
            message: "couldn't reach it",
          },
        ])}
      />,
    );
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.keyDown(box, { key: "Enter" });
    await waitFor(() =>
      expect(screen.getByTestId("chat-error")).toBeInTheDocument(),
    );
    // No agent reply bubble — nothing was delivered.
    expect(screen.queryByTestId("agent-reply")).not.toBeInTheDocument();
  });

  it("has no axe a11y violations in its idle state (WPF-06 / UXD-07)", async () => {
    const { container } = render(
      <Composer changeId="01CHAT" streamChat={fakeStream([])} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
