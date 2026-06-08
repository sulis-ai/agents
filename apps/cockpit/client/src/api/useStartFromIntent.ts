// WP-011 — useStartFromIntent() — the start-from-intent lifecycle (FR-29/30/34).
//
// The ONE source of truth for the start-from-intent conversation's state. It
// calls the funnel `streamStartFromIntent` (api/client.ts) and projects the SSE
// events into a plain-English lifecycle + the live PROPOSAL (awaiting confirm) +
// the STARTED change (at Recon) + a typed error. <StartFromIntent /> renders
// this; it owns no start-from-intent state of its own.
//
// The confirm gate is server-side (FR-N6); the hook simply sends the turns:
//   - propose(intent)  — classify the intent + show what will start;
//   - confirm()         — approve the proposal (the consequential change-start);
//   - reset()           — drop the proposal (starts nothing, FR-N6).
//
// `streamStartFromIntent` is injectable (defaults to the real funnel) so the
// hook + component are testable without a network.

import { useCallback, useRef, useState } from "react";

import type {
  StartFromIntentRequest,
  StartFromIntentStreamEvent,
} from "../../../shared/api-types";
import {
  streamStartFromIntent as defaultStream,
  type StreamStartFromIntentFn,
} from "./client";

/** The founder-facing lifecycle state (plain-English in the UI layer). */
export type StartLifecycle =
  | "idle" // nothing started
  | "classifying" // working out what you mean
  | "proposing" // a proposal is being prepared
  | "proposed" // a proposal is shown, awaiting confirm (the gate)
  | "cloning" // fetching the repo first (local-first, FR-30)
  | "starting" // the confirmed change is being started
  | "started" // the change is created and at Recon
  | "failed"; // ambiguous / stale / unreachable / busy

export type StartProposal = Extract<
  StartFromIntentStreamEvent,
  { type: "proposal" }
>["proposal"];

export type StartedChange = Extract<
  StartFromIntentStreamEvent,
  { type: "started" }
>["started"];

export type StartErrorCode = Extract<
  StartFromIntentStreamEvent,
  { type: "error" }
>["code"];

export interface UseStartFromIntentOptions {
  /** The Product whose Project repo the change starts against (FR-29). */
  productId: string;
  /** investigation marks an explore/look-into request (still a change, FR-N9). */
  kind?: "change" | "investigation";
  /** Injectable for tests; defaults to the real funnel. */
  streamStartFromIntent?: StreamStartFromIntentFn;
}

export interface StartFromIntentState {
  state: StartLifecycle;
  proposal: StartProposal | null;
  started: StartedChange | null;
  isStreaming: boolean;
  errorCode: StartErrorCode | null;
  errorMessage: string | null;
  /** Classify an intent + show the proposal (starts nothing). */
  propose: (intent: string) => Promise<void>;
  /** Approve the proposal — the consequential change-start. */
  confirm: () => Promise<void>;
  /** Drop the proposal — starts nothing (FR-N6). */
  reset: () => void;
}

export function useStartFromIntent(
  options: UseStartFromIntentOptions,
): StartFromIntentState {
  const stream = options.streamStartFromIntent ?? defaultStream;

  const [state, setState] = useState<StartLifecycle>("idle");
  const [proposal, setProposal] = useState<StartProposal | null>(null);
  const [started, setStarted] = useState<StartedChange | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorCode, setErrorCode] = useState<StartErrorCode | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const tokenRef = useRef<string | null>(null);
  const intentRef = useRef<string>("");

  const onEvent = useCallback((event: StartFromIntentStreamEvent) => {
    switch (event.type) {
      case "state":
        if (event.state === "classifying") setState("classifying");
        else if (event.state === "proposing") setState("proposing");
        else if (event.state === "cloning") setState("cloning");
        else if (event.state === "starting") setState("starting");
        else if (event.state === "complete") setState("started");
        else if (event.state === "failed") setState("failed");
        // "confirming" is a transient internal state; UI shows "starting".
        break;
      case "proposal":
        tokenRef.current = event.proposal.confirmToken;
        setProposal(event.proposal);
        setState("proposed");
        break;
      case "started":
        setStarted(event.started);
        setState("started");
        break;
      case "error":
        setErrorCode(event.code);
        setErrorMessage(event.message);
        setState("failed");
        break;
    }
  }, []);

  const runTurn = useCallback(
    async (request: StartFromIntentRequest) => {
      setErrorCode(null);
      setErrorMessage(null);
      setIsStreaming(true);
      try {
        await stream(request, onEvent);
      } catch (err) {
        setState("failed");
        setErrorMessage(err instanceof Error ? err.message : String(err));
      } finally {
        setIsStreaming(false);
      }
    },
    [stream, onEvent],
  );

  const propose = useCallback(
    async (intent: string) => {
      intentRef.current = intent;
      setProposal(null);
      setStarted(null);
      await runTurn({
        phase: "propose",
        productId: options.productId,
        intent,
        ...(options.kind ? { kind: options.kind } : {}),
      });
    },
    [runTurn, options.productId, options.kind],
  );

  const confirm = useCallback(async () => {
    const token = tokenRef.current;
    if (token === null) return; // nothing to confirm — defensive
    await runTurn({
      phase: "confirm",
      productId: options.productId,
      confirmToken: token,
      // Carry the intent so the started change records it (the server uses it
      // for `--intent`); harmless on confirm if the server ignores it.
      intent: intentRef.current,
      ...(options.kind ? { kind: options.kind } : {}),
    });
  }, [runTurn, options.productId, options.kind]);

  const reset = useCallback(() => {
    tokenRef.current = null;
    setProposal(null);
    setState("idle");
  }, []);

  return {
    state,
    proposal,
    started,
    isStreaming,
    errorCode,
    errorMessage,
    propose,
    confirm,
    reset,
  };
}
