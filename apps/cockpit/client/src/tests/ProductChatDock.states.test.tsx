// WP-003 — the dock's three honest states (loading · empty · error) per the
// SIGNED visual contract. Empty is a fresh chat; error is "can't reach the
// chat" said plainly with one clear retry; loading is a skeleton.

import { describe, it, expect, vi, afterEach } from "vitest";
import { fireEvent, waitFor } from "@testing-library/react";
import type {
  ChatScope,
  ChatStreamEvent,
  ChatThreadResponse,
} from "../../../shared/api-types";
import { ProductChatDock } from "../components/ProductChatDock";
import { renderWithClient } from "./_renderWithClient";
import { ActiveProductProvider } from "../api/activeProduct";

const CLINICS = "dna:product:01CLINIC0000000000000000000";
const PRODUCTS = [{ productId: CLINICS, name: "Clinics", active: true }];

function renderDock(
  fetchChatThread: () => Promise<ChatThreadResponse>,
  streamProductChat: (
    scope: ChatScope,
    prompt: string,
    onEvent: (e: ChatStreamEvent) => void,
  ) => Promise<void> = async () => {},
) {
  return renderWithClient(
    <ActiveProductProvider initialActiveProductId={CLINICS}>
      <ProductChatDock
        products={PRODUCTS}
        fetchChatThread={fetchChatThread}
        streamProductChat={streamProductChat}
        putChatProvider={async () => ({ provider: "pty", applied: "new-work" })}
        streamStartFromIntent={async () => {}}
      />
    </ActiveProductProvider>,
  );
}

afterEach(() => {
  delete document.documentElement.dataset.theme;
});

describe("<ProductChatDock> three honest states", () => {
  it("loading — shows a skeleton while the thread loads", () => {
    // A never-resolving fetch keeps the dock in the loading state.
    const { getByTestId } = renderDock(() => new Promise(() => {}));
    expect(getByTestId("chat-loading")).toBeTruthy();
  });

  it("empty — a fresh chat invites the founder to start", async () => {
    const { findByTestId } = renderDock(async () => ({
      messages: [],
      provider: "pty",
      productId: CLINICS,
    }));
    const empty = await findByTestId("chat-empty");
    expect(empty.textContent).toMatch(/clinics/i);
  });

  it("error — says it plainly with one clear retry that refetches", async () => {
    let attempt = 0;
    const fetchChatThread = vi.fn(async () => {
      attempt += 1;
      if (attempt === 1) throw new Error("network down");
      return { messages: [], provider: "pty" as const, productId: CLINICS };
    });
    const { findByTestId, getByTestId } = renderDock(fetchChatThread);

    const err = await findByTestId("chat-error");
    expect(err.getAttribute("role")).toBe("alert");
    expect(err.textContent).toMatch(/couldn't reach/i);

    // The one clear retry refetches the thread.
    fireEvent.click(getByTestId("chat-error-retry"));
    await waitFor(() =>
      expect(fetchChatThread.mock.calls.length).toBeGreaterThanOrEqual(2),
    );
  });
});

describe("<ProductChatDock> the composer sends a chat message (ADR-001/003)", () => {
  it("Send streams a reply for the typed message (distinct from Start work)", async () => {
    const stream = vi.fn(
      async (
        _s: ChatScope,
        _p: string,
        onEvent: (e: ChatStreamEvent) => void,
      ) => {
        onEvent({ type: "chunk", text: "On it." });
        onEvent({ type: "complete", resumed: false });
      },
    );
    const { getByTestId, findByTestId, findByText } = renderDock(
      async () => ({ messages: [], provider: "pty", productId: CLINICS }),
      stream,
    );
    // Empty state first; type a message and Send.
    await findByTestId("chat-empty");
    fireEvent.change(getByTestId("chat-intent-input"), {
      target: { value: "hello" },
    });
    fireEvent.click(getByTestId("chat-send"));

    await waitFor(() =>
      expect(stream).toHaveBeenCalledWith(
        `product:${CLINICS}`,
        "hello",
        expect.any(Function),
      ),
    );
    // The streamed reply renders.
    await findByText(/On it\./);
  });

  it("Enter sends; the message funnel is the chat relay, not start-from-intent", async () => {
    const stream = vi.fn(async () => {});
    const { getByTestId, findByTestId } = renderDock(
      async () => ({ messages: [], provider: "pty", productId: CLINICS }),
      stream,
    );
    await findByTestId("chat-empty");
    const input = getByTestId("chat-intent-input");
    fireEvent.change(input, { target: { value: "ping" } });
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() =>
      expect(stream).toHaveBeenCalledWith(
        `product:${CLINICS}`,
        "ping",
        expect.any(Function),
      ),
    );
  });
});

// WP-005 — the shared <ChatStatusLine> mounts in the dock's chips row, sharing
// ONE mutually-exclusive slot with the suggestion chips (TDD §2.1, ADR-002,
// signed visual contract). At parity with the in-change Composer (contract
// CL-05): idle → chips; while streaming → "Sulis is working…"; on complete →
// "Finished — over to you", then back to chips once read. The line and the
// chips are NEVER both present. The dock HEADER agent-status chip is a separate
// surface and is asserted untouched in ProductChatDock.axe.test.tsx.
describe("<ProductChatDock> status line in the chips row (WP-005)", () => {
  // A stream that emits a chunk then HOLDS (the returned promise never
  // resolves), parking the dock in `replying` so the working line is on screen.
  function holdingStream() {
    return vi.fn(
      (_s: ChatScope, _p: string, onEvent: (e: ChatStreamEvent) => void) =>
        new Promise<void>(() => {
          onEvent({ type: "chunk", text: "Working on it…" });
        }),
    );
  }

  // A stream that emits a chunk then completes — drives `replying → ready` with
  // a reply produced this session, which is the "finished" derivation.
  function completingStream() {
    return vi.fn(
      async (
        _s: ChatScope,
        _p: string,
        onEvent: (e: ChatStreamEvent) => void,
      ) => {
        onEvent({ type: "chunk", text: "All done." });
        onEvent({ type: "complete", resumed: false });
      },
    );
  }

  it("idle — the chips are shown and the working/finished line is not", async () => {
    const { findByTestId, queryByTestId, queryAllByTestId } = renderDock(
      async () => ({ messages: [], provider: "pty", productId: CLINICS }),
      vi.fn(async () => {}),
    );
    await findByTestId("chat-empty");
    // The suggestion chips occupy the slot at rest.
    expect(queryAllByTestId("chat-chip").length).toBeGreaterThan(0);
    expect(queryByTestId("status-working")).toBeNull();
    expect(queryByTestId("status-finished")).toBeNull();
  });

  it("streaming — the working line holds the slot and the chips are gone", async () => {
    const { getByTestId, findByTestId, queryAllByTestId } = renderDock(
      async () => ({ messages: [], provider: "pty", productId: CLINICS }),
      holdingStream(),
    );
    await findByTestId("chat-empty");
    fireEvent.change(getByTestId("chat-intent-input"), {
      target: { value: "hello" },
    });
    fireEvent.click(getByTestId("chat-send"));

    // The working line appears…
    const working = await findByTestId("status-working");
    expect(working.textContent).toMatch(/working/i);
    expect(working.getAttribute("role")).toBe("status");
    expect(working.getAttribute("aria-live")).toBe("polite");
    // …and the suggestion chips are NOT present in the slot at the same time.
    expect(queryAllByTestId("chat-chip")).toHaveLength(0);
  });

  it("complete — the finished line shows, then returns to chips once read", async () => {
    const { getByTestId, findByTestId, queryByTestId, queryAllByTestId } =
      renderDock(
        async () => ({ messages: [], provider: "pty", productId: CLINICS }),
        completingStream(),
      );
    await findByTestId("chat-empty");
    fireEvent.change(getByTestId("chat-intent-input"), {
      target: { value: "hi" },
    });
    fireEvent.click(getByTestId("chat-send"));

    // "Finished — over to you" takes the slot; the chips are gone meanwhile.
    const finished = await findByTestId("status-finished");
    expect(finished.textContent).toMatch(/finished — over to you/i);
    expect(queryAllByTestId("chat-chip")).toHaveLength(0);

    // Reading it (the "Got it" affordance) returns the slot to the chips.
    fireEvent.click(getByTestId("status-finished-dismiss"));
    await waitFor(() => expect(queryByTestId("status-finished")).toBeNull());
    expect(queryAllByTestId("chat-chip").length).toBeGreaterThan(0);
  });

  it("the chips and the status line are never both present", async () => {
    const { getByTestId, findByTestId, queryAllByTestId, queryByTestId } =
      renderDock(
        async () => ({ messages: [], provider: "pty", productId: CLINICS }),
        holdingStream(),
      );
    await findByTestId("chat-empty");

    // At rest: chips present, no status line.
    expect(queryAllByTestId("chat-chip").length).toBeGreaterThan(0);
    expect(queryByTestId("status-working")).toBeNull();
    expect(queryByTestId("status-finished")).toBeNull();

    // While working: status line present, chips absent — mutually exclusive.
    fireEvent.change(getByTestId("chat-intent-input"), {
      target: { value: "go" },
    });
    fireEvent.click(getByTestId("chat-send"));
    await findByTestId("status-working");
    expect(queryAllByTestId("chat-chip")).toHaveLength(0);
  });
});
