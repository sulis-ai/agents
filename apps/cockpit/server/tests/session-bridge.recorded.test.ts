// WP-005 — RecordedSessionBridge satisfies the SessionBridge contract.
//
// Runs the reusable `runSessionBridgeContract` suite against the recorded
// fixture adapter (MEA-09: a recorded REAL stream-json session, replayed —
// not a mock). The fixture (`recording-bridge-claude-session`) covers all
// four cases: live, resume-from-transcript, spawn-grounded, mid-step. The
// mid-step case is the FR-N5 proof — resume re-runs the incomplete step and
// surfaces complete.resumed=true, never a synthesised "done".

import { describe, it, expect } from "vitest";

import { RecordedSessionBridge } from "../adapters/RecordedSessionBridge";
import {
  runSessionBridgeContract,
  CollectingSink,
  type BridgeCase,
} from "./session-bridge.contract.test";

// The recorded fixture lives beside the tests so CI ships it.
const FIXTURE_PATH = new URL(
  "./fixtures/recording-bridge-claude-session.json",
  import.meta.url,
).pathname;

runSessionBridgeContract("RecordedSessionBridge (recorded fixture)", {
  setup: async ({ bridgeCase, changeId, worktreePath }) => {
    return new RecordedSessionBridge({
      fixturePath: FIXTURE_PATH,
      bridgeCase,
      changeId,
      worktreePath,
    });
  },
});

// FR-N5 detail — the mid-step transcript re-runs honestly. The contract suite
// asserts complete.resumed=true; here we additionally pin that the recorded
// stream carried the re-run text (the incomplete step being re-executed),
// proving the adapter does not synthesise a completion.
describe("RecordedSessionBridge — FR-N5 honest mid-step re-run", () => {
  const changeId = "01CHATAAAAAAAAAAAAAAAAAAAA";
  const worktreePath = "/tmp/wp-005-change-worktree";

  function bridge(bridgeCase: BridgeCase): RecordedSessionBridge {
    return new RecordedSessionBridge({
      fixturePath: FIXTURE_PATH,
      bridgeCase,
      changeId,
      worktreePath,
    });
  }

  it("re-runs the incomplete step on resume (the reply mentions resuming the work, not a fake done)", async () => {
    const sink = new CollectingSink();
    const outcome = await bridge("mid-step").relay(changeId, "carry on", sink);
    expect(outcome).toEqual({ kind: "completed", resumed: true });
    // The recorded mid-step reply re-runs the step; the body is non-empty and
    // distinguishable from an empty already-done close.
    expect(sink.replyText.toLowerCase()).toContain("resum");
  });

  it("resolveSession on the mid-step case reports 'resumable' without acting", async () => {
    const r = await bridge("mid-step").resolveSession(changeId);
    expect(r.kind).toBe("resumable");
  });
});
