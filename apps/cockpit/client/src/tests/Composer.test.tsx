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
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";

import { Composer } from "../components/Composer";
import type { ChatStreamEvent } from "../../../shared/api-types";
import { renderWithClient } from "./_renderWithClient";

// useChatStream invalidates the transcript/summaries queries on complete, so
// the Composer needs a QueryClient in the tree — provided by the shared helper.
const renderComposer = renderWithClient;

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

// Mid-reply (no "complete"): the dock transient shows WHILE replying, then
// hands off to the conversation on complete — the live-render tests use this.
const MIDSTREAM: ChatStreamEvent[] = [
  { type: "state", state: "replying" },
  { type: "chunk", text: "On it — " },
  { type: "chunk", text: "wiring the brain view." },
];

describe("<Composer /> — the docked write surface (signed contract)", () => {
  it("renders the send box with the slash + Enter/Shift hint (AI-02)", () => {
    renderComposer(<Composer changeId="01CHAT" streamChat={fakeStream([])} />);
    expect(
      screen.getByLabelText(/message this change's agent/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/for commands/i)).toBeInTheDocument();
    expect(screen.getByText(/shift/i)).toBeInTheDocument();
  });

  it("offers suggestion chips (AI-02 dual-mode input)", () => {
    renderComposer(<Composer changeId="01CHAT" streamChat={fakeStream([])} />);
    const chips = screen.getAllByTestId("suggestion-chip");
    expect(chips.length).toBeGreaterThan(0);
  });

  it("sends on Enter and renders the founder's own message in a neutral bubble", async () => {
    renderComposer(<Composer changeId="01CHAT" streamChat={fakeStream(MIDSTREAM)} />);
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
    renderComposer(<Composer changeId="01CHAT" streamChat={stream} />);
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "line one" } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    expect(stream).not.toHaveBeenCalled();
  });

  it("renders the streamed reply live and joins it on complete (FR-17/18)", async () => {
    renderComposer(<Composer changeId="01CHAT" streamChat={fakeStream(MIDSTREAM)} />);
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.keyDown(box, { key: "Enter" });

    await waitFor(() =>
      expect(screen.getByTestId("agent-reply").textContent).toContain(
        "wiring the brain view.",
      ),
    );
  });

  it("disables send while THIS change is streaming (FR-20 one-in-flight)", async () => {
    renderComposer(<Composer
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
    renderComposer(<Composer
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
    renderComposer(<Composer
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
    renderComposer(<Composer
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
    const { container } = renderComposer(<Composer changeId="01CHAT" streamChat={fakeStream([])} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

// WP-004 — the shared status line + the bottom-dock de-collision fix.
//
// The single row directly above the message box is ONE mutually-exclusive slot
// shared by the suggestion chips and the working↔finished status line (the
// shared <ChatStatusLine> from WP-002). On send that row becomes "Sulis is
// working…"; on complete it reads "Finished — over to you", then returns to the
// chips once the founder dismisses it. The chips and the status line are never
// both present.
//
// The de-collision fix: the honest "resumed" note (FR-26) lives ONLY in that
// idle slot and ONLY while state is `ready`/your-turn. The instant a new turn
// starts (`state !== "ready"`) the working line owns the slot and the resumed
// note is gone — NOT stacked under it (the reported overlap bug). Interrupted
// (FR-22) / failed (FR-19) notes render as their own bands ABOVE the slot.
describe("<Composer /> — status line + bottom-dock de-collision (WP-004)", () => {
  it("shows the working line and NO suggestion chips while replying (mutually exclusive)", async () => {
    renderComposer(
      <Composer changeId="01CHAT" streamChat={fakeStream(MIDSTREAM, { hang: true })} />,
    );
    // Idle: the chips own the slot, no working line.
    expect(screen.getAllByTestId("suggestion-chip").length).toBeGreaterThan(0);
    expect(screen.queryByTestId("status-working")).not.toBeInTheDocument();

    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "wire it" } });
    fireEvent.keyDown(box, { key: "Enter" });

    // Replying: the working line owns the slot; the chips are gone (not both).
    await waitFor(() =>
      expect(screen.getByTestId("status-working")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("suggestion-chip")).not.toBeInTheDocument();
  });

  it("reads 'Finished — over to you' on complete, then returns to chips on dismiss (never both)", async () => {
    renderComposer(
      <Composer changeId="01CHAT" streamChat={fakeStream(HAPPY)} />,
    );
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "ship it" } });
    fireEvent.keyDown(box, { key: "Enter" });

    // On a clean complete (replying → ready, a reply was produced this session)
    // the slot reads "Finished — over to you" and the chips are NOT shown.
    const finished = await screen.findByTestId("status-finished");
    expect(finished.textContent).toMatch(/finished — over to you/i);
    expect(screen.queryByTestId("suggestion-chip")).not.toBeInTheDocument();

    // The founder dismisses it → the slot returns to the chips; the finished
    // line is gone (never both at once).
    fireEvent.click(screen.getByTestId("status-finished-dismiss"));
    await waitFor(() =>
      expect(screen.getAllByTestId("suggestion-chip").length).toBeGreaterThan(0),
    );
    expect(screen.queryByTestId("status-finished")).not.toBeInTheDocument();
  });

  it("de-collision: a new send steps the resumed note aside — the working line holds the slot, the resumed note is NOT in the document", async () => {
    // Two turns, one injected funnel: the FIRST send completes cleanly as a
    // RESUME (so the dock returns to idle and the honest resumed note shows in
    // the slot); the SECOND send holds the working line (never resolves) so we
    // can assert the slot at the instant a fresh turn starts.
    const RESUMED_COMPLETE: ChatStreamEvent[] = [
      { type: "state", state: "resuming" },
      { type: "chunk", text: "picked up where it left off" },
      { type: "complete", resumed: true },
    ];
    const WORKING: ChatStreamEvent[] = [{ type: "state", state: "replying" }];
    let call = 0;
    const streamChat = vi.fn(
      async (
        _changeId: string,
        _prompt: string,
        onEvent: (e: ChatStreamEvent) => void,
      ) => {
        const events = call === 0 ? RESUMED_COMPLETE : WORKING;
        call += 1;
        for (const e of events) onEvent(e);
        if (call > 1) await new Promise(() => {}); // 2nd send hangs on "working"
      },
    );

    renderComposer(<Composer changeId="01CHAT" streamChat={streamChat} />);
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "continue" } });
    fireEvent.keyDown(box, { key: "Enter" });

    // The resumed note is shown in the idle slot once the turn is ready.
    await waitFor(() =>
      expect(screen.getByTestId("resumed-note")).toBeInTheDocument(),
    );

    // A NEW send starts a turn → the working line takes the slot and the
    // resumed note is GONE (stepped aside, not buried under it).
    fireEvent.change(box, { target: { value: "now do the next thing" } });
    fireEvent.keyDown(box, { key: "Enter" });

    await waitFor(() =>
      expect(screen.getByTestId("status-working")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("resumed-note")).not.toBeInTheDocument();
  });

  it("interrupted/failed notes render as their own bands ABOVE the slot, never inside the chips/working slot", async () => {
    // Interrupted (FR-22): the band shows; the working line does NOT claim the
    // slot as "finished", and the chips are not shown alongside the band.
    renderComposer(
      <Composer
        changeId="01CHAT"
        streamChat={fakeStream([
          { type: "state", state: "replying" },
          { type: "chunk", text: "partial answer" },
          { type: "state", state: "interrupted" },
        ], { hang: true })}
      />,
    );
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.keyDown(box, { key: "Enter" });

    await waitFor(() =>
      expect(screen.getByTestId("interrupted-note")).toBeInTheDocument(),
    );
    // The slot stays empty on a broken turn — never "finished", never chips
    // crowding the band.
    expect(screen.queryByTestId("status-finished")).not.toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-chip")).not.toBeInTheDocument();
    // The preserved partial is still shown (FR-22).
    expect(screen.getByTestId("agent-reply").textContent).toContain(
      "partial answer",
    );
  });

  it("has no axe a11y violations while the working line holds the slot (WPF-06 / UXD-07)", async () => {
    const { container } = renderComposer(
      <Composer changeId="01CHAT" streamChat={fakeStream(MIDSTREAM, { hang: true })} />,
    );
    const box = screen.getByLabelText(/message this change's agent/i);
    fireEvent.change(box, { target: { value: "hi" } });
    fireEvent.keyDown(box, { key: "Enter" });
    await waitFor(() =>
      expect(screen.getByTestId("status-working")).toBeInTheDocument(),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
