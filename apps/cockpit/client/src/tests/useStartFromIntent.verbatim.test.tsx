// Regression lock — the web composer passes the founder's intent VERBATIM.
//
// The intent-contamination lesson: at interactive change-creation the founder's
// `intent` got the assistant's own turn-state spliced into it. The web path
// (StartFromIntent.tsx → useStartFromIntent.ts → the server's SulisChangeStarter,
// which forwards `--intent` verbatim) was always clean — these tests PIN that so
// it cannot silently regress.
//
// useStartFromIntent is the source of truth for the start-from-intent
// conversation. `confirm()` is the consequential turn that ultimately reaches
// the server-side StartChangeRunner.start (the `--intent` carrier). We drive
// propose("<known>") → confirm() with a spy `streamStartFromIntent` and assert
// the request the hook sends on confirm carries the founder's intent EXACTLY —
// not a paraphrase, not concatenated with any UI/assistant text.

import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useStartFromIntent } from "../api/useStartFromIntent";
import type {
  StartFromIntentStreamEvent,
  StartFromIntentRequest,
} from "../../../shared/api-types";

// A sentinel that is unmistakably the founder's own words. No paraphrase could
// reproduce it, so any rewrite/truncation/contamination fails the assertion.
const KNOWN_INTENT = "fix the wobbly login redirect FOUNDER_VERBATIM_SENTINEL";

const PROPOSAL: StartFromIntentStreamEvent[] = [
  { type: "state", state: "classifying" },
  {
    type: "proposal",
    proposal: { confirmToken: "tok-1", primitive: "fix", slug: "login-redirect" },
  },
];

const STARTED: StartFromIntentStreamEvent[] = [
  { type: "state", state: "starting" },
  {
    type: "started",
    started: {
      changeId: "01CHG",
      handle: "CH-01CHG",
      slug: "login-redirect",
      primitive: "fix",
      branch: "change/fix-login-redirect",
      worktreePath: "/tmp/wt",
      intent: KNOWN_INTENT,
      baseBranch: "main",
      baseSha: "abc",
      createdAt: "2026-06-04T00:00:00Z",
      updatedAt: "2026-06-04T00:00:00Z",
      stage: "recon",
      liveness: { status: "not-running" },
    },
  },
  { type: "state", state: "complete" },
];

/** A spy stream that records every request and replays the scripted events. */
function spyStream(byPhase: Record<string, StartFromIntentStreamEvent[]>) {
  const requests: StartFromIntentRequest[] = [];
  const fn = vi.fn(
    async (
      request: StartFromIntentRequest,
      onEvent: (e: StartFromIntentStreamEvent) => void,
    ) => {
      requests.push(request);
      for (const e of byPhase[request.phase] ?? []) onEvent(e);
    },
  );
  return { fn, requests };
}

describe("useStartFromIntent — passes the founder's intent VERBATIM", () => {
  it("propose() sends the founder's intent byte-for-byte (no rewrite)", async () => {
    const stream = spyStream({ propose: PROPOSAL });
    const { result } = renderHook(() =>
      useStartFromIntent({
        productId: "dna:product:acme",
        streamStartFromIntent: stream.fn,
      }),
    );

    await act(async () => {
      await result.current.propose(KNOWN_INTENT);
    });

    const proposeReq = stream.requests.find((r) => r.phase === "propose");
    expect(proposeReq).toBeDefined();
    expect(proposeReq?.intent).toBe(KNOWN_INTENT);
  });

  it("confirm() forwards the SAME verbatim intent to the consequential start", async () => {
    const stream = spyStream({ propose: PROPOSAL, confirm: STARTED });
    const { result } = renderHook(() =>
      useStartFromIntent({
        productId: "dna:product:acme",
        streamStartFromIntent: stream.fn,
      }),
    );

    await act(async () => {
      await result.current.propose(KNOWN_INTENT);
    });
    await act(async () => {
      await result.current.confirm();
    });

    // confirm() is the turn whose intent the server uses for `--intent`. It must
    // be the founder's words EXACTLY — never a paraphrase, never concatenated
    // with greeting/plan/reply text.
    const confirmReq = stream.requests.find((r) => r.phase === "confirm");
    expect(confirmReq).toBeDefined();
    expect(confirmReq?.intent).toBe(KNOWN_INTENT);

    // And the started change records that same verbatim intent.
    expect(result.current.started?.intent).toBe(KNOWN_INTENT);
  });
});
