// WP-010 — useOnboarding() — the cold-start onboarding lifecycle (ADR-007/008).
//
// The ONE source of truth for the onboarding conversation's state. It calls the
// onboarding funnel `streamOnboarding` (api/client.ts) and projects the SSE
// events into a plain-English lifecycle + the accumulating agent text + the
// live PROPOSAL (awaiting confirm) + the MINTED result + a typed error.
// OnboardingChat renders this; it owns no onboarding state of its own.
//
// The confirm gate is server-side (FR-N6); the hook simply sends the turns:
//   - search(area)         — begin discovery in the chosen area;
//   - answer(message)       — answer a clarifying question;
//   - confirm(repoChoice)   — approve the live proposal (the consequential act);
//   - decline()             — drop the proposal (creates nothing, FR-N6).
//
// `streamOnboarding` is injectable (defaults to the real funnel) so the hook +
// the component are testable without a network.

import { useCallback, useRef, useState } from "react";

import type {
  OnboardingRequest,
  OnboardingStreamEvent,
} from "../../../shared/api-types";
import {
  streamOnboarding as defaultStreamOnboarding,
  type StreamOnboardingFn,
} from "./client";

/** The founder-facing lifecycle state (plain-English in the UI layer). */
export type OnboardingLifecycle =
  | "idle" // nothing started
  | "searching" // looking in the chosen area
  | "asking" // a clarifying question is in flight
  | "proposing" // a proposal is being prepared
  | "proposed" // a proposal is shown, awaiting confirm (the gate)
  | "minting" // the confirmed act is running
  | "done" // the product is set up
  | "failed"; // a scope violation / stale confirm / failed create

/** What the agent will mint/create, awaiting confirm (FR-N6). */
export type OnboardingProposal = Extract<
  OnboardingStreamEvent,
  { type: "proposal" }
>["proposal"];

/** The minted entities after a confirmed turn (FR-32). */
export type OnboardingMinted = Extract<
  OnboardingStreamEvent,
  { type: "minted" }
>["minted"];

export type OnboardingErrorCode = Extract<
  OnboardingStreamEvent,
  { type: "error" }
>["code"];

export interface OnboardingState {
  state: OnboardingLifecycle;
  /** The accumulating agent text for the current turn. */
  replyText: string;
  /** The live proposal (shown before any mint), or null. */
  proposal: OnboardingProposal | null;
  /** The minted result once a confirmed turn completes, or null. */
  minted: OnboardingMinted | null;
  /** True while a turn is in flight (the composer disables send). */
  isStreaming: boolean;
  errorCode: OnboardingErrorCode | null;
  errorMessage: string | null;
  /** Begin discovery in the chosen area. */
  search: (chosenArea: string) => Promise<void>;
  /** Answer a clarifying question. */
  answer: (message: string) => Promise<void>;
  /** Approve the live proposal (the consequential act — mint + repo). */
  confirm: (repoChoice?: OnboardingRequest["repoChoice"]) => Promise<void>;
  /** Drop the proposal — creates nothing (FR-N6). */
  decline: () => void;
}

export interface UseOnboardingOptions {
  /** Injectable for tests; defaults to the real funnel. */
  streamOnboarding?: StreamOnboardingFn;
}

export function useOnboarding(
  options: UseOnboardingOptions = {},
): OnboardingState {
  const stream = options.streamOnboarding ?? defaultStreamOnboarding;

  const [state, setState] = useState<OnboardingLifecycle>("idle");
  const [replyText, setReplyText] = useState("");
  const [proposal, setProposal] = useState<OnboardingProposal | null>(null);
  const [minted, setMinted] = useState<OnboardingMinted | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorCode, setErrorCode] = useState<OnboardingErrorCode | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // The live confirm token (carried from the proposal into the confirm turn).
  const tokenRef = useRef<string | null>(null);

  const onEvent = useCallback((event: OnboardingStreamEvent) => {
    switch (event.type) {
      case "state":
        if (event.state === "searching") setState("searching");
        else if (event.state === "asking") setState("asking");
        else if (event.state === "proposing") setState("proposing");
        else if (event.state === "minting") setState("minting");
        else if (event.state === "complete") setState("done");
        else if (event.state === "failed") setState("failed");
        // "confirming" is a transient internal state; the UI shows "minting".
        break;
      case "chunk":
        setReplyText((prev) => prev + event.text);
        break;
      case "proposal":
        tokenRef.current = event.proposal.confirmToken;
        setProposal(event.proposal);
        setState("proposed");
        break;
      case "minted":
        setMinted(event.minted);
        setState("done");
        break;
      case "error":
        setErrorCode(event.code);
        setErrorMessage(event.message);
        setState("failed");
        break;
    }
  }, []);

  const runTurn = useCallback(
    async (request: OnboardingRequest) => {
      setReplyText("");
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

  const search = useCallback(
    async (chosenArea: string) => {
      setProposal(null);
      setMinted(null);
      await runTurn({ phase: "search", chosenArea });
    },
    [runTurn],
  );

  const answer = useCallback(
    async (message: string) => {
      await runTurn({ phase: "ask", message });
    },
    [runTurn],
  );

  const confirm = useCallback(
    async (repoChoice?: OnboardingRequest["repoChoice"]) => {
      const token = tokenRef.current;
      if (token === null) return; // nothing to confirm — defensive
      await runTurn({
        phase: "confirm",
        confirmToken: token,
        ...(repoChoice ? { repoChoice } : {}),
      });
    },
    [runTurn],
  );

  const decline = useCallback(() => {
    // Dropping the proposal creates nothing (FR-N6) — purely local reset.
    tokenRef.current = null;
    setProposal(null);
    setState("idle");
  }, []);

  return {
    state,
    replyText,
    proposal,
    minted,
    isStreaming,
    errorCode,
    errorMessage,
    search,
    answer,
    confirm,
    decline,
  };
}
