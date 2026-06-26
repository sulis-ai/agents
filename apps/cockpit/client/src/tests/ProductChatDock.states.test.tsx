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

describe("<ProductChatDock> collapsed is a slim right rail (chat-ux Fix 2)", () => {
  it("collapsing the dock renders a rail with the expand affordance + agent identity, not empty space", async () => {
    const { findByTestId, getByTestId, queryByTestId } = renderDock(async () => ({
      messages: [],
      provider: "pty",
      productId: CLINICS,
    }));
    // Wait for the dock to settle, then collapse it.
    await findByTestId("chat-empty");
    fireEvent.click(getByTestId("chat-toggle"));

    // Collapsed = a rail, not the full dock body. The composer is gone…
    expect(queryByTestId("chat-intent-input")).toBeNull();
    // …but the rail is present, carries the expand affordance, and names the
    // agent identity (the active product) so "whose chat" stays legible.
    const rail = getByTestId("chat-rail");
    expect(rail).toBeTruthy();
    const expand = getByTestId("chat-toggle");
    expect(expand.getAttribute("aria-label")).toMatch(/show chat/i);
    // The rail names the active product (agent identity) for legibility.
    expect(rail.textContent ?? "").toMatch(/clinics/i);
  });
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
    await waitFor(() => expect(fetchChatThread.mock.calls.length).toBeGreaterThanOrEqual(2));
  });
});

describe("<ProductChatDock> the composer sends a chat message (ADR-001/003)", () => {
  it("Send streams a reply for the typed message (distinct from Start work)", async () => {
    const stream = vi.fn(
      async (_s: ChatScope, _p: string, onEvent: (e: ChatStreamEvent) => void) => {
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
    fireEvent.change(getByTestId("chat-intent-input"), { target: { value: "hello" } });
    fireEvent.click(getByTestId("chat-send"));

    await waitFor(() => expect(stream).toHaveBeenCalledWith(`product:${CLINICS}`, "hello", expect.any(Function)));
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
    await waitFor(() => expect(stream).toHaveBeenCalledWith(`product:${CLINICS}`, "ping", expect.any(Function)));
  });
});
