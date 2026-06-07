// WP-005 — Contract test for SessionBridge (TDD §4.2, ADR-002).
//
// One reusable `runContract` suite both adapters import and satisfy:
//   - `session-bridge.recorded.test.ts` runs it against the recorded fixture;
//   - `session-bridge.streamjson.test.ts` runs it against the prod adapter
//     with a stubbed stream-json child.
// Same assertions, two implementations — the boundary-parity guarantee
// (MEA-09: the recorded fixture is a recorded REAL stream, never a mock).
//
// The four resolution cases the bridge must handle (ADR-002):
//   live | resumable | fresh   (+ a mid-step transcript that resumes and
//                                re-runs the incomplete step, FR-N5).
//
// The factory is asymmetric on purpose: each implementation prepares its own
// world (the recorded adapter loads a fixture; the stub adapter seeds a fake
// child) without leaking the shape into the contract.

import { describe, it, expect } from "vitest";

import type {
  SessionBridge,
  SessionResolution,
  RelaySink,
} from "../ports/SessionBridge";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ChatStreamEvent } from "../../shared/api-types";

/** The four cases every conforming adapter must replay. */
export type BridgeCase = "live" | "resumable" | "fresh" | "mid-step";

export type BridgeContractFactory = {
  /**
   * Build a bridge whose `changeId` resolves to `bridgeCase`. `worktreePath`
   * is the change's cwd the binding guard expects (the recorded session's
   * cwd must equal it). Returns the bridge under test.
   */
  setup: (args: {
    bridgeCase: BridgeCase;
    changeId: string;
    worktreePath: string;
  }) => Promise<SessionBridge>;
  teardown?: () => Promise<void>;
};

/** Collect every event a relay emits, for ordering assertions. */
export class CollectingSink implements RelaySink {
  readonly events: ChatStreamEvent[] = [];
  emit(event: ChatStreamEvent): void {
    this.events.push(event);
  }
  /** Concatenated text of every chunk event (the reply body). */
  get replyText(): string {
    return this.events
      .filter((e): e is { type: "chunk"; text: string } => e.type === "chunk")
      .map((e) => e.text)
      .join("");
  }
  get types(): string[] {
    return this.events.map((e) => e.type);
  }
}

const CHANGE_ID = "01CHATAAAAAAAAAAAAAAAAAAAA";
const WORKTREE = "/tmp/wp-005-change-worktree";

export function runSessionBridgeContract(
  name: string,
  factory: BridgeContractFactory,
): void {
  describe(`SessionBridge contract — ${name}`, () => {
    async function build(bridgeCase: BridgeCase): Promise<SessionBridge> {
      return factory.setup({
        bridgeCase,
        changeId: CHANGE_ID,
        worktreePath: WORKTREE,
      });
    }

    describe("resolveSession() — side-effect-free resolution (FR-N4)", () => {
      it("returns kind 'live' when a live session is present", async () => {
        const bridge = await build("live");
        const r: SessionResolution = await bridge.resolveSession(CHANGE_ID);
        expect(r.kind).toBe("live");
        expect(r.session.changeId).toBe(CHANGE_ID);
        expect(r.session.cwd).toBe(WORKTREE);
        if (factory.teardown) await factory.teardown();
      });

      it("returns kind 'resumable' when a prior transcript exists but no live session", async () => {
        const bridge = await build("resumable");
        const r = await bridge.resolveSession(CHANGE_ID);
        expect(r.kind).toBe("resumable");
        expect(r.session.changeId).toBe(CHANGE_ID);
        if (factory.teardown) await factory.teardown();
      });

      it("returns kind 'fresh' when the change never had a session", async () => {
        const bridge = await build("fresh");
        const r = await bridge.resolveSession(CHANGE_ID);
        expect(r.kind).toBe("fresh");
        expect(r.session.changeId).toBe(CHANGE_ID);
        if (factory.teardown) await factory.teardown();
      });

      it("carries the worktree cwd in the resolved session (binding identity, ADR-004)", async () => {
        const bridge = await build("live");
        const r = await bridge.resolveSession(CHANGE_ID);
        expect(r.session.cwd).toBe(WORKTREE);
        if (factory.teardown) await factory.teardown();
      });
    });

    describe("relay() — streams state → chunk* → complete (ADR-001)", () => {
      it("emits a leading state, ≥1 chunk, then complete on a live session", async () => {
        const bridge = await build("live");
        const sink = new CollectingSink();
        const outcome = await bridge.relay(CHANGE_ID, "hello", sink);

        expect(sink.events[0]?.type).toBe("state");
        expect(sink.types).toContain("chunk");
        expect(sink.events.at(-1)?.type).toBe("complete");
        expect(sink.replyText.length).toBeGreaterThan(0);
        expect(outcome.kind).toBe("completed");
        if (factory.teardown) await factory.teardown();
      });

      it("reports resumed=false on a live session's complete event (FR-26)", async () => {
        const bridge = await build("live");
        const sink = new CollectingSink();
        const outcome = await bridge.relay(CHANGE_ID, "hello", sink);
        const complete = sink.events.find((e) => e.type === "complete");
        expect(complete).toEqual({ type: "complete", resumed: false });
        expect(outcome).toEqual({ kind: "completed", resumed: false });
        if (factory.teardown) await factory.teardown();
      });

      it("reports resumed=true when resuming a prior session (FR-26)", async () => {
        const bridge = await build("resumable");
        const sink = new CollectingSink();
        const outcome = await bridge.relay(CHANGE_ID, "continue", sink);
        const complete = sink.events.find((e) => e.type === "complete");
        expect(complete).toEqual({ type: "complete", resumed: true });
        expect(outcome).toEqual({ kind: "completed", resumed: true });
        if (factory.teardown) await factory.teardown();
      });

      it("spawns fresh and completes (resumed=false) when there was no session (FR-25)", async () => {
        const bridge = await build("fresh");
        const sink = new CollectingSink();
        const outcome = await bridge.relay(CHANGE_ID, "start", sink);
        expect(sink.types).toContain("chunk");
        const complete = sink.events.find((e) => e.type === "complete");
        expect(complete).toEqual({ type: "complete", resumed: false });
        expect(outcome).toEqual({ kind: "completed", resumed: false });
        if (factory.teardown) await factory.teardown();
      });

      it("on a mid-step transcript, resumes and re-runs — complete.resumed=true, never a synthesised done (FR-N5)", async () => {
        const bridge = await build("mid-step");
        const sink = new CollectingSink();
        const outcome = await bridge.relay(CHANGE_ID, "carry on", sink);
        // The agent wakes, re-runs the incomplete step, and only THEN completes.
        const complete = sink.events.find((e) => e.type === "complete");
        expect(complete).toEqual({ type: "complete", resumed: true });
        expect(outcome).toEqual({ kind: "completed", resumed: true });
        // A re-run means the stream carried fresh chunks AFTER resuming —
        // not an empty "already done" close.
        expect(sink.replyText.length).toBeGreaterThan(0);
        if (factory.teardown) await factory.teardown();
      });

      it("a chunk only ever follows a state (no chunk-before-state)", async () => {
        const bridge = await build("live");
        const sink = new CollectingSink();
        await bridge.relay(CHANGE_ID, "hello", sink);
        const firstChunk = sink.types.indexOf("chunk");
        const firstState = sink.types.indexOf("state");
        expect(firstState).toBeGreaterThanOrEqual(0);
        expect(firstChunk).toBeGreaterThan(firstState);
        if (factory.teardown) await factory.teardown();
      });
    });
  });
}

// vitest's include pattern matches this file; a trivial self-suite keeps the
// runner from failing "no test suite found" — the substantive coverage runs
// through the importing adapter test files.
describe("SessionBridge contract module", () => {
  it("exports runSessionBridgeContract", () => {
    expect(typeof runSessionBridgeContract).toBe("function");
  });
});
