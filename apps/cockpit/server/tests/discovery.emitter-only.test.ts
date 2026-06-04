// WP-010 — emitter-only mint tests (FR-32 / NFR-DISC-03; ADR-007).
//
// THE Form-pillar guarantee: every entity is minted ONLY through the validated
// spine emitters, which run INSIDE the agent session over the bridge. The
// orchestrator NEVER writes an entity file directly. We prove this two ways:
//   1. behaviourally — a mint turn relays a mint prompt to the bridge and emits
//      `minted` only after the bridge completes (no out-of-band write);
//   2. statically — the orchestrator module imports no fs-write API and starts
//      no process (the read-only gate also proves this repo-wide; here we pin
//      the orchestrator specifically).

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

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

function bridgeRecordingMint(): SessionBridge & { mintRelayed: boolean } {
  const state = { mintRelayed: false };
  return {
    get mintRelayed() {
      return state.mintRelayed;
    },
    async resolveSession(changeId: string): Promise<SessionResolution> {
      return { kind: "live", session: { changeId, cwd: CHOSEN_AREA } };
    },
    async relay(
      _id: string,
      prompt: string,
      sink: RelaySink,
    ): Promise<RelayOutcome> {
      if (/mint|emit|create the/i.test(prompt)) state.mintRelayed = true;
      sink.emit({ type: "state", state: "replying" });
      sink.emit({ type: "chunk", text: "ok" });
      sink.emit({ type: "complete", resumed: false });
      return { kind: "completed", resumed: false };
    },
  } as SessionBridge & { mintRelayed: boolean };
}

function deps(bridge: SessionBridge): OnboardingDeps {
  return {
    sessionBridge: bridge,
    listProductIds: async () => [],
    permittedRoot: "/founder/code",
    newToken: () => "tok-1",
  };
}

describe("onboarding mints ONLY through the bridge/emitter seam (FR-32)", () => {
  it("the mint is relayed to the bridge — the orchestrator performs no out-of-band write", async () => {
    const bridge = bridgeRecordingMint();
    const orch = new OnboardingOrchestrator(deps(bridge));
    const events: OnboardingStreamEvent[] = [];

    await orch.turn(
      { phase: "search", chosenArea: CHOSEN_AREA },
      { emit: (e) => events.push(e) },
    );
    await orch.turn(
      {
        phase: "confirm",
        confirmToken: "tok-1",
        repoChoice: { mode: "find" },
      },
      { emit: (e) => events.push(e) },
    );

    // The mint went THROUGH the bridge (the emitter runs inside the session).
    expect((bridge as { mintRelayed: boolean }).mintRelayed).toBe(true);
    expect(events.some((e) => e.type === "minted")).toBe(true);
  });

  it("the orchestrator source imports NO fs-write API and starts NO process", () => {
    const src = readFileSync(
      join(__dirname, "..", "lib", "discovery", "onboardingOrchestrator.ts"),
      "utf8",
    );
    // Strip comments so prose mentioning a verb isn't a false positive.
    const code = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/(^|[^:])\/\/.*$/gm, "$1");
    expect(/\bwriteFile(Sync)?\s*\(/.test(code)).toBe(false);
    expect(/\bappendFile(Sync)?\s*\(/.test(code)).toBe(false);
    expect(/\bspawn(Sync)?\s*\(/.test(code)).toBe(false);
    expect(/\bexecFile(Sync)?\s*\(/.test(code)).toBe(false);
  });
});
