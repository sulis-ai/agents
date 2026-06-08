// WP-009 — useConciergeStream() — the concierge ask lifecycle (FR-33; ADR-006).
//
// The ONE source of truth for the concierge front door's state. It calls the
// read-only funnel `streamConciergeQuery` (api/client.ts) and projects the SSE
// events into a plain-English lifecycle state + the accumulating answer text +
// the `route` hint (FR-34 — surfaced as a confirm-gated OFFER, never acted on
// here). ConciergeChat renders this; it owns no answer state of its own.
//
// `streamQuery` is injectable (defaults to the real read-only funnel) so the
// hook + the component are testable without a network.

import { useCallback, useState } from "react";

import type { ConciergeStreamEvent } from "../../../shared/api-types";
import {
  streamConciergeQuery as defaultStreamQuery,
  type StreamConciergeFn,
} from "./client";

/** The founder-facing lifecycle state (plain-English in the UI layer). */
export type ConciergeLifecycle =
  | "ready" // idle, ready to ask
  | "thinking" // the concierge is looking across your world
  | "replying" // the answer is streaming
  | "failed"; // couldn't reach the concierge

/** Where a consequential intent should be OFFERED (never acted on inline). */
export type ConciergeRouteHint = "onboarding" | "start-from-intent" | null;

export interface ConciergeStreamState {
  state: ConciergeLifecycle;
  /** The accumulating read-only answer text. */
  answerText: string;
  /** The route hint on complete — the front door OFFERS this (FR-N9). */
  route: ConciergeRouteHint;
  /** True while a query is in flight. */
  isStreaming: boolean;
  /** Plain-English error message when state === "failed". */
  errorMessage: string | null;
  /** Ask a question. Resolves when the answer stream ends. */
  ask: (question: string) => Promise<void>;
}

export interface UseConciergeStreamOptions {
  /** Injectable for tests; defaults to the real read-only funnel. */
  streamQuery?: StreamConciergeFn;
  /** Optional Product scope for the answer (ADR-009). */
  productId?: string;
}

export function useConciergeStream(
  options: UseConciergeStreamOptions = {},
): ConciergeStreamState {
  const stream = options.streamQuery ?? defaultStreamQuery;

  const [state, setState] = useState<ConciergeLifecycle>("ready");
  const [answerText, setAnswerText] = useState("");
  const [route, setRoute] = useState<ConciergeRouteHint>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const onEvent = useCallback((event: ConciergeStreamEvent) => {
    switch (event.type) {
      case "state":
        if (event.state === "thinking") setState("thinking");
        else if (event.state === "replying") setState("replying");
        else if (event.state === "failed") setState("failed");
        // "complete" is carried by the `complete` event below.
        break;
      case "chunk":
        setAnswerText((prev) => prev + event.text);
        break;
      case "complete":
        setRoute(event.route);
        setState("ready");
        break;
      case "error":
        setErrorMessage(event.message);
        setState("failed");
        break;
    }
  }, []);

  const ask = useCallback(
    async (question: string) => {
      // Reset per-ask state (a new question is a fresh answer).
      setAnswerText("");
      setRoute(null);
      setErrorMessage(null);
      setIsStreaming(true);
      setState("thinking");
      try {
        await stream(question, onEvent, options.productId);
      } catch (err) {
        setState("failed");
        setErrorMessage(err instanceof Error ? err.message : String(err));
      } finally {
        setIsStreaming(false);
      }
    },
    [stream, onEvent, options.productId],
  );

  return { state, answerText, route, isStreaming, errorMessage, ask };
}
