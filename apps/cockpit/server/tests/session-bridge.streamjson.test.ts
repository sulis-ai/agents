// WP-005 — StreamJsonSessionBridge satisfies the SessionBridge contract.
//
// Runs the reusable contract suite against the PRODUCTION adapter with a
// STUBBED stream-json child (CI-runnable; no live claude). The stub feeds the
// same recorded stream-json line shapes the real `claude -p --output-format
// stream-json --include-partial-messages` emits, so the adapter's parser +
// resume/spawn argv construction are exercised with full parity to the
// recorded fixture. The REAL claude path is the founder-machine observation.
//
// The adapter takes an injectable `spawnBridge` so the test supplies a fake
// child; in production `index.ts` wires the real `child_process.spawn`. This
// is the one place a process may start (ADR-003) — the gate allow-lists this
// adapter file.

import { describe, it, expect } from "vitest";
import { Readable } from "node:stream";
import { EventEmitter } from "node:events";

import { StreamJsonSessionBridge } from "../adapters/StreamJsonSessionBridge";
import type { BridgeChildHandle } from "../adapters/StreamJsonSessionBridge";
import { runSessionBridgeContract } from "./session-bridge.contract.test";
import type { BridgeCase } from "./session-bridge.contract.test";

/**
 * Build the recorded stream-json lines a real `claude -p` would emit for a
 * case. One JSON object per line (NDJSON). The adapter maps:
 *   system/init                      → state "ready"/"resuming"/"spawning"
 *   stream_event (text delta)        → chunk
 *   result/success                   → complete (resumed from the resolution)
 */
function streamJsonLinesFor(bridgeCase: BridgeCase): string[] {
  const greeting =
    bridgeCase === "mid-step"
      ? "Resuming the half-finished step and re-running it now."
      : bridgeCase === "fresh"
        ? "Starting fresh on this change."
        : "Working on it.";
  const lines: string[] = [];
  lines.push(JSON.stringify({ type: "system", subtype: "init" }));
  for (const word of greeting.split(" ")) {
    lines.push(
      JSON.stringify({
        type: "stream_event",
        event: { type: "content_block_delta", delta: { text: word + " " } },
      }),
    );
  }
  lines.push(JSON.stringify({ type: "result", subtype: "success" }));
  return lines;
}

/** A fake child whose stdout replays the recorded NDJSON then closes 0. */
function fakeChild(lines: string[]): BridgeChildHandle {
  const stdout = Readable.from(lines.map((l) => l + "\n"));
  const emitter = new EventEmitter() as BridgeChildHandle["process"];
  const handle: BridgeChildHandle = {
    process: emitter,
    stdout,
    kill: () => {
      /* no-op for the stub */
    },
  };
  // Emit close(0) after stdout drains.
  stdout.on("end", () => {
    setImmediate(() => emitter.emit("close", 0));
  });
  return handle;
}

function makeBridge(args: {
  bridgeCase: BridgeCase;
  changeId: string;
  worktreePath: string;
}): StreamJsonSessionBridge {
  const { bridgeCase, worktreePath } = args;
  return new StreamJsonSessionBridge({
    // The resolver is injected so the contract suite controls which case the
    // change resolves to without a filesystem (the real adapter reads
    // liveness + transcript locator; that path is covered by those libs'
    // own tests + the founder-machine observation).
    resolve: async () => {
      const session = { changeId: args.changeId, cwd: worktreePath };
      if (bridgeCase === "live") return { kind: "live", session };
      if (bridgeCase === "fresh") return { kind: "fresh", session };
      return { kind: "resumable", session };
    },
    spawnBridge: () => fakeChild(streamJsonLinesFor(bridgeCase)),
    startupTimeoutMs: 1000,
  });
}

runSessionBridgeContract("StreamJsonSessionBridge (stubbed child)", {
  setup: async (args) => makeBridge(args),
});

describe("StreamJsonSessionBridge — process-start discipline", () => {
  it("constructs the resume argv with --resume for a resumable session", async () => {
    let capturedArgs: string[] = [];
    const bridge = new StreamJsonSessionBridge({
      resolve: async () => ({
        kind: "resumable",
        session: {
          changeId: "01CHATAAAAAAAAAAAAAAAAAAAA",
          cwd: "/tmp/wp-005-change-worktree",
          lastSessionRef: "/tmp/transcript.jsonl",
        },
      }),
      spawnBridge: (argv) => {
        capturedArgs = argv;
        return fakeChild(streamJsonLinesFor("resumable"));
      },
      startupTimeoutMs: 1000,
    });
    const sink = {
      events: [] as unknown[],
      emit(e: unknown) {
        this.events.push(e);
      },
    };
    await bridge.relay("01CHATAAAAAAAAAAAAAAAAAAAA", "continue", sink as never);
    expect(capturedArgs).toContain("--output-format");
    expect(capturedArgs).toContain("stream-json");
    expect(capturedArgs.join(" ")).toMatch(/--resume|--continue/);
  });

  it("constructs a spawn (no --resume) for a fresh session", async () => {
    let capturedArgs: string[] = [];
    const bridge = new StreamJsonSessionBridge({
      resolve: async () => ({
        kind: "fresh",
        session: {
          changeId: "01CHATAAAAAAAAAAAAAAAAAAAA",
          cwd: "/tmp/wp-005-change-worktree",
        },
      }),
      spawnBridge: (argv) => {
        capturedArgs = argv;
        return fakeChild(streamJsonLinesFor("fresh"));
      },
      startupTimeoutMs: 1000,
    });
    const sink = {
      events: [] as unknown[],
      emit(e: unknown) {
        this.events.push(e);
      },
    };
    await bridge.relay("01CHATAAAAAAAAAAAAAAAAAAAA", "start", sink as never);
    expect(capturedArgs.join(" ")).not.toMatch(/--resume/);
    expect(capturedArgs).toContain("stream-json");
  });
});
