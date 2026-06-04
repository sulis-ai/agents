// WP-010 — onboarding orchestrator tests (ADR-007 amended; FR-27/31/32/N6/N11).
//
// The orchestrator sequences SEARCH → ASK → PROPOSE → CONFIRM → MINT. The
// CONVERSATION (search / ask / propose) delegates to the SAME bridge as the
// chat (FR-27, which runs the discover-* skills). The consequential MINT +
// `git init` are DETERMINISTIC SERVER actions behind the SpineMinter port
// (ADR-007 amended): the agent-delegated mint proved slow + unreliable (167s,
// minted nothing live). The orchestrator owns the confirm gate + idempotency
// probe + scope bound + all-or-nothing — never a freehand fs-walk or entity
// write, and never a process start of its own.
//
// These tests drive a scripted bridge (for the conversation) + a fake
// SpineMinter (for the act) so the full round-trip is exercised in CI without a
// live agent or real emitters (the live mint is the BLOCK-and-hand-to-founder;
// the real-emitter mint is pinned by discovery.mint-real.test.ts).

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
import type {
  SpineMinter,
  MintInput,
  MintResult,
  FindOrCreateRepoInput,
} from "../ports/SpineMinter";
import type { RepoOutcome } from "../lib/discovery/repoFindOrCreate";
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

/** A fake SpineMinter that records calls + returns scripted outcomes. */
function fakeMinter(
  opts: {
    repoOutcome?: RepoOutcome;
    mint?: MintResult;
  } = {},
): SpineMinter & { mints: MintInput[]; repos: FindOrCreateRepoInput[] } {
  const mints: MintInput[] = [];
  const repos: FindOrCreateRepoInput[] = [];
  return {
    mints,
    repos,
    async findOrCreateRepo(input: FindOrCreateRepoInput): Promise<RepoOutcome> {
      repos.push(input);
      return (
        opts.repoOutcome ?? {
          outcome: "reachable",
          repo: input.chosenArea,
          path: input.chosenArea,
          primaryBranch: "main",
        }
      );
    },
    async mint(input: MintInput): Promise<MintResult> {
      mints.push(input);
      return (
        opts.mint ?? {
          ok: true,
          tenant: input.tenantName,
          product: { productId: "dna:product:fake", name: input.productName },
          project: { projectId: "dna:project:fake", source: input.source },
        }
      );
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
  minter: SpineMinter,
  overrides: Partial<OnboardingDeps> = {},
): OnboardingDeps {
  return {
    sessionBridge: bridge,
    spineMinter: minter,
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
    const minter = fakeMinter();
    const orch = new OnboardingOrchestrator(deps(bridge, minter));

    const events = await run(orch, { phase: "search", chosenArea: CHOSEN_AREA });

    // It delegated the CONVERSATION to the bridge (orchestration, ADR-007).
    expect((bridge as { prompts: string[] }).prompts.length).toBe(1);
    // It streamed agent text…
    expect(events.some((e) => e.type === "chunk")).toBe(true);
    // …and ended awaiting confirm — a PROPOSAL, NOT a mint.
    const proposal = events.find((e) => e.type === "proposal");
    expect(proposal).toBeDefined();
    expect(events.some((e) => e.type === "minted")).toBe(false);
    // A read/propose turn mints NOTHING — the minter is never called.
    expect(minter.mints.length).toBe(0);
    if (proposal && proposal.type === "proposal") {
      expect(proposal.proposal.confirmToken).toBe("tok-fixed-1");
    }
  });

  it("a CONFIRM turn with the live token MINTS via the SpineMinter (deterministic) and emits `minted`", async () => {
    const bridge = scriptedBridge(["thinking…"]);
    const minter = fakeMinter();
    const orch = new OnboardingOrchestrator(deps(bridge, minter));

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
    // The mint went through the DETERMINISTIC minter, not a second bridge relay:
    // the bridge was relayed only for the search CONVERSATION (1 prompt).
    expect((bridge as { prompts: string[] }).prompts.length).toBe(1);
    expect(minter.repos.length).toBe(1);
    expect(minter.mints.length).toBe(1);
    // The minted Project carries the source from the resolved repo (FR-36).
    if (minted && minted.type === "minted") {
      expect(minted.minted.projects?.[0]?.source?.repo).toBe(CHOSEN_AREA);
    }
  });

  it("idempotent: an already-minted product is SURFACED (alreadyMinted), not duplicated (FR-31)", async () => {
    const bridge = scriptedBridge(["found acme."]);
    const minter = fakeMinter();
    const orch = new OnboardingOrchestrator(
      deps(bridge, minter, { listProductIds: async () => ["dna:product:existing"] }),
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
    const minter = fakeMinter({ repoOutcome: { outcome: "create-failed" } });
    const orch = new OnboardingOrchestrator(deps(bridge, minter));

    await run(orch, { phase: "search", chosenArea: CHOSEN_AREA });
    const events = await run(orch, {
      phase: "confirm",
      confirmToken: "tok-fixed-1",
      repoChoice: { mode: "create", createTarget: "local" },
    });

    const err = events.find((e) => e.type === "error");
    expect(err).toBeDefined();
    if (err && err.type === "error") expect(err.code).toBe("REPO_CREATE_FAILED");
    // NO mint happened — the repo step failed before the mint.
    expect(events.some((e) => e.type === "minted")).toBe(false);
    expect(minter.mints.length).toBe(0);
  });

  it("a CONFIRM whose MINT FAILS leaves the graph unchanged (all-or-nothing) and emits MINT_FAILED", async () => {
    const bridge = scriptedBridge(["minting"]);
    const minter = fakeMinter({
      mint: { ok: false, code: "MINT_FAILED", message: "emit failed" },
    });
    const orch = new OnboardingOrchestrator(deps(bridge, minter));

    await run(orch, { phase: "search", chosenArea: CHOSEN_AREA });
    const events = await run(orch, {
      phase: "confirm",
      confirmToken: "tok-fixed-1",
      repoChoice: { mode: "find" },
    });

    const err = events.find((e) => e.type === "error");
    expect(err).toBeDefined();
    if (err && err.type === "error") expect(err.code).toBe("MINT_FAILED");
    expect(events.some((e) => e.type === "minted")).toBe(false);
  });
});
