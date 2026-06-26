// WP-003 — useProductChat: resolve the active product's chat scope, load its
// durable thread, and relay messages on its resolved provider (ADR-001/002/003).
//
// The dock reads the SAME `useActiveProduct()` store the board reads (no second
// active-product store — ADR-001). This hook turns that scope into the wire
// `ChatScope`, loads the scope's thread (react-query, keyed by scope so each
// product's history is its own and switching swaps it — never blends), and
// exposes a `send` that streams the reply via the existing `ChatStreamEvent`
// shape (reused, not forked). Modeled on `useChatStream` (the per-change relay)
// + `useProducts` (the read-query pattern).

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  ChatErrorCode,
  ChatProvider,
  ChatScope,
  ChatThreadResponse,
  TranscriptMessage,
} from "../../../shared/api-types";
import {
  fetchChatThread as defaultFetchChatThread,
  streamProductChat as defaultStreamProductChat,
  putChatProvider as defaultPutChatProvider,
  type FetchChatThreadFn,
  type StreamProductChatFn,
  type PutChatProviderFn,
} from "./client";

export type ProductChatLifecycle =
  | "ready"
  | "resuming"
  | "spawning"
  | "replying"
  | "interrupted"
  | "failed";

export interface UseProductChatOptions {
  fetchChatThread?: FetchChatThreadFn;
  streamProductChat?: StreamProductChatFn;
  putChatProvider?: PutChatProviderFn;
}

export interface ProductChatState {
  /** The durable transcript for the active scope (empty while loading). */
  messages: TranscriptMessage[];
  /** The scope's resolved provider — the RUNNING agent (AI-07 honest identity). */
  provider: ChatProvider;
  /** True while the scope's thread is loading (drives the skeleton state). */
  isLoading: boolean;
  /** True if the thread could not be loaded (drives the error state). */
  isError: boolean;
  /** The live relay lifecycle for an in-flight send. */
  state: ProductChatLifecycle;
  replyText: string;
  isStreaming: boolean;
  errorCode: ChatErrorCode | null;
  errorMessage: string | null;
  /** Stream a prompt on the scope's provider. */
  send: (prompt: string) => Promise<void>;
  /** Switch the scope's provider (AI-03 — applies to new work). */
  switchProvider: (provider: ChatProvider) => Promise<void>;
  /** Refetch the thread (the error state's retry). */
  retry: () => void;
}

/**
 * chat-ux Fix 4 — append the founder's just-submitted turn to the scope's
 * cached thread so it is visible IMMEDIATELY (during streaming), mirroring
 * `useChatStream`'s instant-user-turn behaviour. This is the ONE optimistic
 * cache-write shape (the Blue constraint: no duplicated cache logic) — `send`
 * calls it on submit and the durable thread, refetched on `complete`, replaces
 * the cache wholesale so the optimistic copy is reconciled, never duplicated.
 */
function appendOptimisticUserTurn(
  prev: ChatThreadResponse | undefined,
  text: string,
): ChatThreadResponse {
  const base: ChatThreadResponse = prev ?? {
    messages: [],
    provider: "pty",
    productId: null,
  };
  const optimistic: TranscriptMessage = {
    kind: "user",
    // A transient id — the durable thread's own uuid takes over on refetch.
    uuid: `optimistic-${Date.now()}`,
    timestamp: new Date().toISOString(),
    text,
  };
  return { ...base, messages: [...base.messages, optimistic] };
}

export function useProductChat(
  scope: ChatScope,
  options: UseProductChatOptions = {},
): ProductChatState {
  const fetchThread = options.fetchChatThread ?? defaultFetchChatThread;
  const streamChat = options.streamProductChat ?? defaultStreamProductChat;
  const putProvider = options.putChatProvider ?? defaultPutChatProvider;
  const queryClient = useQueryClient();

  // Keyed by scope → switching the active product swaps the cache entry, so
  // each product's history is its own and the two never blend in the UI.
  const thread = useQuery({
    queryKey: ["product-chat", scope],
    queryFn: () => fetchThread(scope),
  });

  const [state, setState] = useState<ProductChatLifecycle>("ready");
  const [replyText, setReplyText] = useState("");
  const [errorCode, setErrorCode] = useState<ChatErrorCode | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // The provider the agent picker shows is the RUNNING one (from the thread),
  // overlaid with an optimistic switch the founder has applied this session.
  const [pendingProvider, setPendingProvider] = useState<ChatProvider | null>(
    null,
  );
  const provider: ChatProvider = pendingProvider ?? thread.data?.provider ?? "pty";

  // Clear the optimistic overlay whenever the scope's thread (re)loads OR the
  // scope itself changes, so the picker always settles on the server's
  // authoritative running provider (AI-07 honest identity) — the overlay must
  // never shadow the real provider across a refetch or a product switch.
  useEffect(() => {
    setPendingProvider(null);
  }, [scope, thread.dataUpdatedAt]);

  const send = useCallback(
    async (prompt: string) => {
      setState("spawning");
      setReplyText("");
      setErrorCode(null);
      setErrorMessage(null);
      // chat-ux Fix 4 — show the founder's own message INSTANTLY (before any
      // reply chunk) by appending it to the cached thread. The durable thread,
      // refetched on `complete`, reconciles it (no duplicate).
      queryClient.setQueryData<ChatThreadResponse>(
        ["product-chat", scope],
        (prev) => appendOptimisticUserTurn(prev, prompt),
      );
      await streamChat(scope, prompt, (event) => {
        if (event.type === "state") {
          if (event.state === "complete") setState("ready");
          else if (event.state !== "ready") setState(event.state);
        } else if (event.type === "chunk") {
          setState("replying");
          setReplyText((prev) => prev + event.text);
        } else if (event.type === "complete") {
          setState("ready");
          // The send may have appended to the durable thread — refetch it.
          queryClient.invalidateQueries({ queryKey: ["product-chat", scope] });
        } else if (event.type === "error") {
          setState("failed");
          setErrorCode(event.code);
          setErrorMessage(event.message);
        }
      });
    },
    [scope, streamChat, queryClient],
  );

  const switchProvider = useCallback(
    async (next: ChatProvider) => {
      // Optimistic — the picker reflects the chosen provider immediately; the
      // server applies it to NEW work (AI-03), never re-homing a live run.
      setPendingProvider(next);
      try {
        await putProvider(scope, next);
      } catch {
        // The server rejected the switch — roll back the optimistic overlay so
        // the picker keeps naming the provider actually running (AI-07), never
        // a choice the server never accepted.
        setPendingProvider(null);
      }
    },
    [scope, putProvider],
  );

  const retry = useCallback(() => {
    void thread.refetch();
  }, [thread]);

  return useMemo(
    () => ({
      messages: thread.data?.messages ?? [],
      provider,
      isLoading: thread.isLoading,
      isError: thread.isError,
      state,
      replyText,
      isStreaming: state === "replying" || state === "spawning" || state === "resuming",
      errorCode,
      errorMessage,
      send,
      switchProvider,
      retry,
    }),
    [
      thread.data,
      thread.isLoading,
      thread.isError,
      provider,
      state,
      replyText,
      errorCode,
      errorMessage,
      send,
      switchProvider,
      retry,
    ],
  );
}
