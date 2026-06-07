// WP-013 — <Chat /> tests.
//
// Renders the chronological transcript from useTranscript(changeId).
//
//   - Loading → "Loading conversation..."
//   - Error → "Could not load the conversation" + retry button.
//   - Empty → <EmptyTranscript /> with the spec copy.
//   - Non-empty → vertical list of <ChatMessage />s in array order.
//   - Auto-scroll to bottom on initial load (mocked scrollIntoView).
//
// References: WP-013 Contract (<Chat> shape), TDD §6.2 (empty state).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { TranscriptMessage } from "../../../shared/api-types";
import { Chat } from "../components/Chat";

function freshClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function renderInsideClient(ui: React.ReactElement) {
  const client = freshClient();
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("<Chat />", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
    // jsdom doesn't ship scrollIntoView — install a no-op so the
    // Chat's auto-scroll effect doesn't crash on first render. The
    // scroll-asserting test below replaces it with a spy.
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      writable: true,
      value: () => {},
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders 'Loading conversation...' while fetching", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      () => new Promise(() => {}),
    );
    renderInsideClient(<Chat changeId="abc" />);
    expect(screen.getByText(/Loading conversation/i)).toBeInTheDocument();
  });

  it("renders the error state with a retry button on a fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(500, { error: "boom" }),
    );
    renderInsideClient(<Chat changeId="abc" />);
    await waitFor(() =>
      expect(
        screen.getByText(/Could not load the conversation/i),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /retry/i }),
    ).toBeInTheDocument();
  });

  it("renders <EmptyTranscript /> with the spec copy when no messages", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
    renderInsideClient(<Chat changeId="abc" />);
    await waitFor(() =>
      expect(screen.getByTestId("empty-transcript")).toBeInTheDocument(),
    );
    expect(
      screen.getByText("This change hasn't had a Claude session yet."),
    ).toBeInTheDocument();
  });

  it("groups the transcript into a user bubble + an agent Turn Card (chat-B2)", async () => {
    const messages: TranscriptMessage[] = [
      {
        kind: "user",
        uuid: "u1",
        timestamp: "2026-05-26T10:00:00Z",
        text: "do the thing",
      },
      {
        kind: "assistant",
        uuid: "a1",
        timestamp: "2026-05-26T10:01:00Z",
        blocks: [
          { kind: "text", text: "On it." },
          { kind: "tool-use", toolName: "Read", input: { path: "x.ts" } },
        ],
      },
      {
        // Agent-lifecycle meta — folded out of the founder-facing card stream.
        kind: "system",
        uuid: "s1",
        timestamp: "2026-05-26T10:02:00Z",
        subtype: "info",
        text: "Session resumed.",
      },
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, messages),
    );
    renderInsideClient(<Chat changeId="abc" />);

    await waitFor(() =>
      expect(screen.getByTestId("chat-message-user")).toBeInTheDocument(),
    );
    // The agent turn renders as ONE Turn Card, headed by its summary.
    expect(screen.getByTestId("turn-card")).toBeInTheDocument();
    expect(screen.getByText("On it.")).toBeInTheDocument();
    // The single tool call is folded behind a "1 step" disclosure.
    expect(screen.getByTestId("turn-steps-toggle").textContent).toMatch(
      /1 step\b/,
    );
    // System meta is NOT shown as its own message in the card stream.
    expect(screen.queryByTestId("system-chip")).not.toBeInTheDocument();

    // Order: the founder's bubble first, then the agent Turn Card.
    const list = screen.getByTestId("chat-list");
    const children = within(list).getAllByTestId(/^(chat-message-user|turn-card)$/);
    expect(children[0]).toHaveAttribute("data-testid", "chat-message-user");
    expect(children[1]).toHaveAttribute("data-testid", "turn-card");
  });

  it("scrolls the bottom sentinel into view on initial load", async () => {
    const messages: TranscriptMessage[] = [
      {
        kind: "user",
        uuid: "u1",
        timestamp: "2026-05-26T10:00:00Z",
        text: "hi",
      },
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, messages),
    );
    // jsdom doesn't ship scrollIntoView — install it as a spy.
    const scrollSpy = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      writable: true,
      value: scrollSpy,
    });

    renderInsideClient(<Chat changeId="abc" />);

    await waitFor(() =>
      expect(screen.getByTestId("chat-message-user")).toBeInTheDocument(),
    );
    // The bottom sentinel triggers scrollIntoView once on first paint.
    expect(scrollSpy).toHaveBeenCalled();
  });
});
