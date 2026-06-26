// WP-003 — useProductChat: the send relay (streams the reply via the EXISTING
// ChatStreamEvent shape) and the provider switch (AI-03 — applies to new work).

import { describe, it, expect, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ChatScope, ChatStreamEvent } from "../../../shared/api-types";
import { useProductChat } from "../api/useProductChat";
import { withQueryClient } from "./_renderWithClient";

const SCOPE = "product:dna:product:01CLINIC0000000000000000000" as ChatScope;

function wrapper({ children }: { children: React.ReactNode }) {
  return withQueryClient(children);
}

describe("useProductChat — load + send + switch", () => {
  it("loads the scope's thread, exposing messages + the running provider", async () => {
    const fetchChatThread = vi.fn(async () => ({
      messages: [
        { kind: "user" as const, uuid: "u1", timestamp: "t", text: "hi" },
      ],
      provider: "agy" as const,
      productId: "dna:product:01CLINIC0000000000000000000",
    }));
    const { result } = renderHook(
      () => useProductChat(SCOPE, { fetchChatThread, streamProductChat: async () => {}, putChatProvider: async () => ({ provider: "agy", applied: "new-work" }) }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.messages).toHaveLength(1));
    expect(result.current.provider).toBe("agy");
  });

  it("send streams the reply through the ChatStreamEvent shape", async () => {
    const streamProductChat = vi.fn(
      async (_scope: ChatScope, _prompt: string, onEvent: (e: ChatStreamEvent) => void) => {
        onEvent({ type: "state", state: "spawning" });
        onEvent({ type: "chunk", text: "Hel" });
        onEvent({ type: "chunk", text: "lo" });
        onEvent({ type: "complete", resumed: false });
      },
    );
    const { result } = renderHook(
      () => useProductChat(SCOPE, { fetchChatThread: async () => ({ messages: [], provider: "pty", productId: null }), streamProductChat, putChatProvider: async () => ({ provider: "pty", applied: "new-work" }) }),
      { wrapper },
    );
    await act(async () => {
      await result.current.send("say hello");
    });
    expect(streamProductChat).toHaveBeenCalledWith(SCOPE, "say hello", expect.any(Function));
    expect(result.current.replyText).toBe("Hello");
    expect(result.current.state).toBe("ready");
  });

  it("send renders the user's submitted message IMMEDIATELY (before any reply chunk) — chat-ux Fix 4", async () => {
    // The stream pauses after spawning so we can assert the user's own message
    // is already visible DURING streaming, not only after complete.
    let resolveStream: (() => void) | null = null;
    const streamProductChat = vi.fn(
      async (_scope: ChatScope, _prompt: string, onEvent: (e: ChatStreamEvent) => void) => {
        onEvent({ type: "state", state: "spawning" });
        // hold here — the reply has NOT arrived yet.
        await new Promise<void>((res) => {
          resolveStream = () => {
            onEvent({ type: "chunk", text: "reply" });
            onEvent({ type: "complete", resumed: false });
            res();
          };
        });
      },
    );
    const { result } = renderHook(
      () =>
        useProductChat(SCOPE, {
          fetchChatThread: async () => ({ messages: [], provider: "pty", productId: null }),
          streamProductChat,
          putChatProvider: async () => ({ provider: "pty", applied: "new-work" }),
        }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // Fire the send but DON'T await — it parks inside the stream above.
    let sendDone!: Promise<void>;
    act(() => {
      sendDone = result.current.send("hello there");
    });

    // BEFORE the reply: the user's own message is already in the transcript.
    await waitFor(() => {
      const texts = result.current.messages
        .filter((m) => m.kind === "user")
        .map((m) => (m as { text: string }).text);
      expect(texts).toContain("hello there");
    });

    // Release the stream and let it complete.
    await act(async () => {
      resolveStream?.();
      await sendDone;
    });
  });

  it("reconciles the optimistic message with the durable thread on complete — no duplicate (chat-ux Fix 4)", async () => {
    // The durable thread (after the send) contains the user's turn exactly once.
    let loads = 0;
    const fetchChatThread = vi.fn(async () => {
      loads += 1;
      // First load: empty. After complete (refetch): the durable single turn.
      if (loads === 1) return { messages: [], provider: "pty" as const, productId: null };
      return {
        messages: [
          { kind: "user" as const, uuid: "durable-u1", timestamp: "t", text: "hello there" },
          {
            kind: "assistant" as const,
            uuid: "durable-a1",
            timestamp: "t",
            blocks: [{ kind: "text" as const, text: "reply" }],
          },
        ],
        provider: "pty" as const,
        productId: null,
      };
    });
    const streamProductChat = vi.fn(
      async (_scope: ChatScope, _prompt: string, onEvent: (e: ChatStreamEvent) => void) => {
        onEvent({ type: "chunk", text: "reply" });
        onEvent({ type: "complete", resumed: false });
      },
    );
    const { result } = renderHook(
      () =>
        useProductChat(SCOPE, {
          fetchChatThread,
          streamProductChat,
          putChatProvider: async () => ({ provider: "pty", applied: "new-work" }),
        }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.send("hello there");
    });

    // After complete the durable thread is authoritative: the user's turn
    // appears EXACTLY once (the optimistic copy is reconciled, not duplicated).
    await waitFor(() => {
      const userTurns = result.current.messages.filter(
        (m) => m.kind === "user" && (m as { text: string }).text === "hello there",
      );
      expect(userTurns).toHaveLength(1);
    });
  });

  it("send surfaces a relay error as a single error projection", async () => {
    const streamProductChat = vi.fn(
      async (_scope: ChatScope, _prompt: string, onEvent: (e: ChatStreamEvent) => void) => {
        onEvent({ type: "error", code: "SESSION_BUSY", message: "busy" });
      },
    );
    const { result } = renderHook(
      () => useProductChat(SCOPE, { fetchChatThread: async () => ({ messages: [], provider: "pty", productId: null }), streamProductChat, putChatProvider: async () => ({ provider: "pty", applied: "new-work" }) }),
      { wrapper },
    );
    await act(async () => {
      await result.current.send("hi");
    });
    expect(result.current.state).toBe("failed");
    expect(result.current.errorCode).toBe("SESSION_BUSY");
    expect(result.current.errorMessage).toBe("busy");
  });

  it("switchProvider applies the chosen provider optimistically + calls the funnel", async () => {
    const putChatProvider = vi.fn(async () => ({ provider: "agy" as const, applied: "new-work" as const }));
    const { result } = renderHook(
      () => useProductChat(SCOPE, { fetchChatThread: async () => ({ messages: [], provider: "pty", productId: null }), streamProductChat: async () => {}, putChatProvider }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.provider).toBe("pty"));
    await act(async () => {
      await result.current.switchProvider("agy");
    });
    // The funnel is called with the chosen provider (AI-03: applies to new work).
    expect(putChatProvider).toHaveBeenCalledWith(SCOPE, "agy");
    // AI-07 honest identity: the picker settles back on the RUNNING provider the
    // thread reports (pty) — the optimistic overlay is transient and never
    // shadows the real running agent past the thread settling. "agy" applies to
    // the NEXT session open, not the live run.
    await waitFor(() => expect(result.current.provider).toBe("pty"));
  });

  it("rolls back the optimistic provider when the switch funnel rejects", async () => {
    const putChatProvider = vi.fn(async () => {
      throw new Error("server rejected");
    });
    const { result } = renderHook(
      () => useProductChat(SCOPE, { fetchChatThread: async () => ({ messages: [], provider: "pty", productId: null }), streamProductChat: async () => {}, putChatProvider }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.provider).toBe("pty"));
    await act(async () => {
      // Must not throw — the rejection is caught and rolled back internally.
      await result.current.switchProvider("agy");
    });
    expect(putChatProvider).toHaveBeenCalledWith(SCOPE, "agy");
    expect(result.current.provider).toBe("pty");
  });
});
