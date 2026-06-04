// WP-005 — useChatStream hook test (FR-17/19/22/23/26, ADR-001).
//
// The hook owns the chat send lifecycle for one change: it calls the single
// network funnel `streamChat` (api/client.ts) and projects the SSE events
// into a plain-English lifecycle state + the accumulating reply text + the
// honest resumed flag. It is the ONE source of truth for chat state (WPF-04);
// the Composer renders it.
//
// We inject a fake `streamChat` so the hook is tested without a real network.

import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { useChatStream } from "../api/useChatStream";
import type { ChatStreamEvent } from "../../../shared/api-types";

/** Build a fake streamChat that replays `events` then resolves. */
function fakeStream(events: ChatStreamEvent[]) {
  return vi.fn(
    async (
      _changeId: string,
      _prompt: string,
      onEvent: (e: ChatStreamEvent) => void,
    ) => {
      for (const e of events) onEvent(e);
    },
  );
}

describe("useChatStream (ADR-001)", () => {
  it("starts in the 'ready' state with no reply", () => {
    const { result } = renderHook(() =>
      useChatStream("01CHAT", { streamChat: fakeStream([]) }),
    );
    expect(result.current.state).toBe("ready");
    expect(result.current.replyText).toBe("");
    expect(result.current.isStreaming).toBe(false);
  });

  it("projects state → chunk* → complete into replying then ready, accumulating chunks", async () => {
    const stream = fakeStream([
      { type: "state", state: "replying" },
      { type: "chunk", text: "Hello " },
      { type: "chunk", text: "world" },
      { type: "complete", resumed: false },
    ]);
    const { result } = renderHook(() =>
      useChatStream("01CHAT", { streamChat: stream }),
    );
    await act(async () => {
      await result.current.send("hi");
    });
    await waitFor(() => expect(result.current.state).toBe("ready"));
    expect(result.current.replyText).toBe("Hello world");
    expect(result.current.resumed).toBe(false);
  });

  it("surfaces an honest resumed flag when the change was resumed (FR-26)", async () => {
    const stream = fakeStream([
      { type: "state", state: "resuming" },
      { type: "chunk", text: "back" },
      { type: "complete", resumed: true },
    ]);
    const { result } = renderHook(() =>
      useChatStream("01CHAT", { streamChat: stream }),
    );
    await act(async () => {
      await result.current.send("continue");
    });
    await waitFor(() => expect(result.current.resumed).toBe(true));
  });

  it("maps a SESSION_UNREACHABLE error to the could-not-start state, not delivered (FR-19)", async () => {
    const stream = fakeStream([
      {
        type: "error",
        code: "SESSION_UNREACHABLE",
        message: "couldn't reach the session",
      },
    ]);
    const { result } = renderHook(() =>
      useChatStream("01CHAT", { streamChat: stream }),
    );
    await act(async () => {
      await result.current.send("hi");
    });
    await waitFor(() => expect(result.current.state).toBe("failed"));
    expect(result.current.errorCode).toBe("SESSION_UNREACHABLE");
    // The message was NOT delivered — the reply is empty.
    expect(result.current.replyText).toBe("");
  });

  it("preserves the partial and marks interrupted on a mid-stream break (FR-22)", async () => {
    const stream = fakeStream([
      { type: "state", state: "replying" },
      { type: "chunk", text: "half a th" },
      { type: "state", state: "interrupted" },
    ]);
    const { result } = renderHook(() =>
      useChatStream("01CHAT", { streamChat: stream }),
    );
    await act(async () => {
      await result.current.send("hi");
    });
    await waitFor(() => expect(result.current.state).toBe("interrupted"));
    expect(result.current.replyText).toBe("half a th");
  });

  it("maps a thrown network failure to the failed state without claiming delivery", async () => {
    const stream = vi.fn(async () => {
      throw new Error("network down");
    });
    const { result } = renderHook(() =>
      useChatStream("01CHAT", { streamChat: stream }),
    );
    await act(async () => {
      await result.current.send("hi");
    });
    await waitFor(() => expect(result.current.state).toBe("failed"));
  });
});
