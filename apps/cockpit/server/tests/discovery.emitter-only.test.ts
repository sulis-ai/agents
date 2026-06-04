// WP-010 — emitter-only mint tests (FR-32 / NFR-DISC-03; ADR-007 amended).
//
// THE Form-pillar guarantee: every entity is minted ONLY through the validated
// spine emitters. After the fix-forward, that mint is a DETERMINISTIC SERVER
// action behind the SpineMinter port (not an agent turn over the bridge — the
// agent-delegated mint proved slow + unreliable, minting nothing live). The
// orchestrator NEVER writes an entity file directly and NEVER starts a process
// itself. We prove this two ways:
//   1. behaviourally — a confirm turn mints via the SpineMinter port (not via a
//      second bridge relay) and emits `minted` only after the minter succeeds;
//   2. statically — the orchestrator module imports no fs-write API and starts
//      no process (the validated emitters live behind the SpineMinter adapter,
//      which is the one allow-listed process-start/write site — proven by the
//      read-only gate; here we pin the orchestrator specifically).

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
import type {
  SpineMinter,
  MintInput,
  MintResult,
  FindOrCreateRepoInput,
} from "../ports/SpineMinter";
import type { RepoOutcome } from "../lib/discovery/repoFindOrCreate";
import type { OnboardingStreamEvent } from "../../shared/api-types";

const CHOSEN_AREA = "/founder/code/acme-checkout";

/** A bridge that records whether it was relayed a MINT prompt (it must not be). */
function conversationBridge(): SessionBridge & { mintRelayed: boolean } {
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
      // The bridge is the CONVERSATION seam only — a mint prompt here is the
      // old (removed) agent-delegated mint and would be a regression.
      if (/mint the tenant|spine emitters|emit-tenant/i.test(prompt)) {
        state.mintRelayed = true;
      }
      sink.emit({ type: "state", state: "replying" });
      sink.emit({ type: "chunk", text: "ok" });
      sink.emit({ type: "complete", resumed: false });
      return { kind: "completed", resumed: false };
    },
  } as SessionBridge & { mintRelayed: boolean };
}

/** A fake SpineMinter that records that the deterministic mint was invoked. */
function recordingMinter(): SpineMinter & { minted: boolean } {
  const state = { minted: false };
  return {
    get minted() {
      return state.minted;
    },
    async findOrCreateRepo(input: FindOrCreateRepoInput): Promise<RepoOutcome> {
      return {
        outcome: "reachable",
        repo: input.chosenArea,
        path: input.chosenArea,
        primaryBranch: "main",
      };
    },
    async mint(input: MintInput): Promise<MintResult> {
      state.minted = true;
      return {
        ok: true,
        tenant: input.tenantName,
        product: { productId: "dna:product:fake", name: input.productName },
        project: { projectId: "dna:project:fake", source: input.source },
      };
    },
  } as SpineMinter & { minted: boolean };
}

function deps(bridge: SessionBridge, minter: SpineMinter): OnboardingDeps {
  return {
    sessionBridge: bridge,
    spineMinter: minter,
    listProductIds: async () => [],
    permittedRoot: "/founder/code",
    newToken: () => "tok-1",
  };
}

describe("onboarding mints ONLY through the validated spine emitters (FR-32)", () => {
  it("the mint runs through the deterministic SpineMinter — NOT a bridge mint prompt", async () => {
    const bridge = conversationBridge();
    const minter = recordingMinter();
    const orch = new OnboardingOrchestrator(deps(bridge, minter));
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

    // The mint went through the deterministic minter (the emitters live behind
    // it), NOT through a bridge mint prompt (the removed fragile path).
    expect((minter as { minted: boolean }).minted).toBe(true);
    expect((bridge as { mintRelayed: boolean }).mintRelayed).toBe(false);
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
