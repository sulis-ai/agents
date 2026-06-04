// WP-010 — onboarding orchestrator tests (ADR-007; FR-27/31/32/N6/N11).
//
// The orchestrator sequences SEARCH → ASK → PROPOSE → CONFIRM → MINT over the
// SAME bridge as the chat (FR-27). It REIMPLEMENTS nothing (ADR-007): search
// delegates to the bridge (which runs the discover-* skills), mint delegates to
// the bridge (which runs the validated spine emitters). The orchestrator owns
// the confirm gate + the idempotency probe + the scope bound + the
// all-or-nothing persistence — never a freehand fs-walk or entity write.
//
// These tests drive a RecordedSessionBridge so the full round-trip is exercised
// in CI without a live agent (the live mint is the BLOCK-and-hand-to-founder).

import { describe, it, expect } from "vitest";

import {
  OnboardingOrchestrator,
  type OnboardingDeps,
} from "../lib/discovery/onboardingOrchestrator";
import type {
  SessionBridge,
  RelaySink,
  RelayOutcome,
  SessionResolution,
} from "../ports/SessionBridge";
import type { OnboardingStreamEvent } from "../../shared/api-types";

const CHOSEN_AREA = "/founder/code/acme-checkout";

/** A scripted bridge that records prompts + replays canned chunks. */
function scriptedBridge(chunks: string[]): SessionBridge & { prompts: string[] } {
  const prompts: string[] = [];
  return {
    prompts,
    async resolveSession(changeId: string): Promise<SessionResolution> {
      return {
        kind: "live",
        session: { changeId, cwd: CHOSEN_AREA },
      };
    },
    async relay(
      _id: string,
      prompt: string,
      sink: RelaySink,
    ): Promise<RelayOutcome> {
      prompts.push(prompt);
      sink.emit({ type: "state", state: "replying" });
      for (const c of chunks) sink.emit({ type: "chunk", text: c });
      sink.emit({ type: "complete", resumed: false });
      return { kind: "completed", resumed: false };
    },
  };
}

/** Collect the orchestrator's emitted onboarding events for a turn. */
async function run(
  orch: OnboardingOrchestrator,
  request: Parameters<OnboardingOrchestrator["turn"]>[0],
): Promise<OnboardingStreamEvent[]> {
  const events: OnboardingStreamEvent[] = [];
  await orch.turn(request, { emit: (e) => events.push(e) });
  return events;
}

/** Deps with a deterministic token factory + an empty graph (worldIsEmpty). */
function deps(
  bridge: SessionBridge,
  overrides: Partial<OnboardingDeps> = {},
): OnboardingDeps {
  return {
    sessionBridge: bridge,
    // The idempotency probe: returns the already-minted product ids.
    listProductIds: async () => [],
    permittedRoot: "/founder/code",
    newToken: () => "tok-fixed-1",
    ...overrides,
  };
}

describe("OnboardingOrchestrator — sequence search → ask → propose → confirm → mint", () => {
  it("a SEARCH turn drives the bridge (delegation) and ends in a PROPOSAL, minting nothing", async () => {
    const bridge = scriptedBridge(["Looking in your folder… ", "found a Node app."]);
    const orch = new OnboardingOrchestrator(deps(bridge));

    const events = await run(orch, { phase: "search", chosenArea: CHOSEN_AREA });

    // It delegated to the bridge (orchestration, ADR-007).
    expect((bridge as { prompts: string[] }).prompts.length).toBe(1);
    // It streamed agent text…
    expect(events.some((e) => e.type === "chunk")).toBe(true);
    // …and ended awaiting confirm — a PROPOSAL, NOT a mint.
    const proposal = events.find((e) => e.type === "proposal");
    expect(proposal).toBeDefined();
    expect(events.some((e) => e.type === "minted")).toBe(false);
    if (proposal && proposal.type === "proposal") {
      expect(proposal.proposal.confirmToken).toBe("tok-fixed-1");
    }
  });

  it("a CONFIRM turn with the live token MINTS via the bridge and emits `minted`", async () => {
    const bridge = scriptedBridge(["minting…"]);
    const orch = new OnboardingOrchestrator(deps(bridge));

    // First propose to establish the live token.
    await run(orch, { phase: "search", chosenArea: CHOSEN_AREA });
    // Then confirm with the matching token + a repo choice (default local).
    const events = await run(orch, {
      phase: "confirm",
      confirmToken: "tok-fixed-1",
      repoChoice: { mode: "create", createTarget: "local" },
    });

    const minted = events.find((e) => e.type === "minted");
    expect(minted).toBeDefined();
    // The mint went THROUGH the bridge (emitter delegation) — 2 relays total
    // (search + confirm-mint), never a direct entity write.
    expect((bridge as { prompts: string[] }).prompts.length).toBe(2);
  });

  it("idempotent: an already-minted product is SURFACED (alreadyMinted), not duplicated (FR-31)", async () => {
    const bridge = scriptedBridge(["found acme."]);
    const orch = new OnboardingOrchestrator(
      deps(bridge, { listProductIds: async () => ["dna:product:existing"] }),
    );

    const events = await run(orch, { phase: "search", chosenArea: CHOSEN_AREA });
    const proposal = events.find((e) => e.type === "proposal");
    expect(proposal).toBeDefined();
    if (proposal && proposal.type === "proposal") {
      expect(proposal.proposal.alreadyMinted).toBe(true);
    }
  });

  it("a CONFIRM whose repo create FAILS leaves the graph unchanged (all-or-nothing) and emits REPO_CREATE_FAILED", async () => {
    const bridge = scriptedBridge(["attempting create"]);
    const orch = new OnboardingOrchestrator(
      deps(bridge, {
        // The injected repo-outcome resolver reports a failed create.
        attemptRepo: async () => ({ outcome: "create-failed" }),
      }),
    );

    await run(orch, { phase: "search", chosenArea: CHOSEN_AREA });
    const events = await run(orch, {
      phase: "confirm",
      confirmToken: "tok-fixed-1",
      repoChoice: { mode: "create", createTarget: "local" },
    });

    const err = events.find((e) => e.type === "error");
    expect(err).toBeDefined();
    if (err && err.type === "error") expect(err.code).toBe("REPO_CREATE_FAILED");
    // NO mint happened.
    expect(events.some((e) => e.type === "minted")).toBe(false);
  });
});
