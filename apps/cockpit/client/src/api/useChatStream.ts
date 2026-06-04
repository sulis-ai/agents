// WP-005 — useChatStream(changeId) — the chat send lifecycle (ADR-001).
//
// The ONE source of truth for chat state for one change (WPF-04). It calls the
// single network funnel `streamChat` (api/client.ts) and projects the SSE
// events into a plain-English lifecycle state + the accumulating reply text +
// the honest `resumed` flag (FR-26). The Composer renders this; it owns no
// chat state of its own.
//
// `streamChat` is injectable (defaults to the real funnel) so the hook + the
// Composer are testable without a network.

import { useCallback, useState } from "react";

import type { ChatStreamEvent, ChatErrorCode } from "../../../shared/api-types";
import { streamChat as defaultStreamChat, type StreamChatFn } from "./client";

/** The founder-facing lifecycle state (FR-23), plain-English in the UI layer. */
export type ChatLifecycle =
  | "ready" // idle, ready to send
  | "resuming" // waking the change up
  | "spawning" // starting fresh
  | "replying" // the agent is replying
  | "interrupted" // the reply broke mid-stream (partial kept)
  | "failed"; // couldn't start / errored

export interface ChatStreamState {
  state: ChatLifecycle;
  /** The accumulating reply text (preserved on interrupt, FR-22). */
  replyText: string;
  /** Honest indication the change was resumed, not silently continued (FR-26). */
  resumed: boolean;
  /** True while a send is in flight (the Composer disables send, FR-20). */
  isStreaming: boolean;
  /** The typed error code when state === "failed" (FR-19/20/21). */
  errorCode: ChatErrorCode | null;
  /** Plain-English error message when failed. */
  errorMessage: string | null;
  /** Send a prompt to the change. Resolves when the stream ends. */
  send: (prompt: string) => Promise<void>;
}

export interface UseChatStreamOptions {
  /** Injectable for tests; defaults to the real relay funnel. */
  streamChat?: StreamChatFn;
}

export function useChatStream(
  changeId: string,
  options: UseChatStreamOptions = {},
): ChatStreamState {
  const stream = options.streamChat ?? defaultStreamChat;

  const [state, setState] = useState<ChatLifecycle>("ready");
  const [replyText, setReplyText] = useState("");
  const [resumed, setResumed] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorCode, setErrorCode] = useState<ChatErrorCode | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const onEvent = useCallback((event: ChatStreamEvent) => {
    switch (event.type) {
      case "state":
        // The bridge's lifecycle states map 1:1 onto the founder-facing ones;
        // "complete" is handled by the `complete` event, so it is ignored here.
        if (event.state === "resuming") setState("resuming");
        else if (event.state === "spawning") setState("spawning");
        else if (event.state === "replying") setState("replying");
        else if (event.state === "interrupted") setState("interrupted");
        else if (event.state === "failed") setState("failed");
        break;
      case "chunk":
        setReplyText((prev) => prev + event.text);
        break;
      case "complete":
        setResumed(event.resumed);
        setState("ready");
        break;
      case "error":
        setErrorCode(event.code);
        setErrorMessage(event.message);
        setState("failed");
        break;
    }
  }, []);

  const send = useCallback(
    async (prompt: string) => {
      // Reset per-send state (a resend is a NEW message, Q10).
      setReplyText("");
      setResumed(false);
      setErrorCode(null);
      setErrorMessage(null);
      setIsStreaming(true);
      setState("replying");
      try {
        await stream(changeId, prompt, onEvent);
      } catch (err) {
        // A thrown network failure: failed, never claim delivery (FR-19).
        setState("failed");
        setErrorMessage(err instanceof Error ? err.message : String(err));
      } finally {
        setIsStreaming(false);
      }
    },
    [changeId, stream, onEvent],
  );

  return {
    state,
    replyText,
    resumed,
    isStreaming,
    errorCode,
    errorMessage,
    send,
  };
}
