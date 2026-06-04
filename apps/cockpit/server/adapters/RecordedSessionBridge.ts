// WP-005 — RecordedSessionBridge (ADR-002; MEA-09 recorded, not a mock).
//
// The test adapter for the SessionBridge port. It replays a RECORDED real
// stream-json session (the `recording-bridge-claude-session` fixture) so the
// relay + resolution + binding + lock + composer are exercised in CI WITHOUT a
// live `claude`. It satisfies the SAME `session-bridge.contract.test.ts` suite
// the production `StreamJsonSessionBridge` does — the boundary-parity guarantee.
//
// It is a REAL adapter, not a mock: it reads a recorded event stream off disk
// and maps it through the SHARED `streamJsonToEvents` mapper (the same mapper
// the prod adapter uses), so a parser bug shows up identically in both.
//
// Starts no process (it replays from a file), so it lives OUTSIDE the
// read-only gate's process-start allow-list.

import { readFileSync } from "node:fs";

import type {
  SessionBridge,
  SessionResolution,
  RelaySink,
  RelayOutcome,
} from "../ports/SessionBridge";
import {
  streamJsonToEvent,
  leadingStateFor,
  resumedFor,
  type StreamJsonRecord,
} from "../lib/streamJsonToEvents";

type FixtureCase = "live" | "resumable" | "fresh" | "mid-step";

interface FixtureFile {
  cases: Record<
    FixtureCase,
    { resolution: SessionResolution["kind"]; events: StreamJsonRecord[] }
  >;
}

export interface RecordedSessionBridgeOptions {
  /** Absolute path to the recorded fixture JSON. */
  fixturePath: string;
  /** Which recorded case to replay (live | resumable | fresh | mid-step). */
  bridgeCase: FixtureCase;
  /** The change id the resolved session carries (binding identity). */
  changeId: string;
  /** The worktree cwd the resolved session carries (binding identity). */
  worktreePath: string;
}

export class RecordedSessionBridge implements SessionBridge {
  private readonly recorded: {
    resolution: SessionResolution["kind"];
    events: StreamJsonRecord[];
  };

  constructor(private readonly opts: RecordedSessionBridgeOptions) {
    const file = JSON.parse(
      readFileSync(opts.fixturePath, "utf8"),
    ) as FixtureFile;
    const recorded = file.cases[opts.bridgeCase];
    if (!recorded) {
      throw new Error(
        `RecordedSessionBridge: fixture has no case '${opts.bridgeCase}'`,
      );
    }
    this.recorded = recorded;
  }

  /** Side-effect-free: report the recorded resolution kind (FR-N4). */
  async resolveSession(changeId: string): Promise<SessionResolution> {
    const session = {
      changeId,
      cwd: this.opts.worktreePath,
    };
    return { kind: this.recorded.resolution, session } as SessionResolution;
  }

  /** Replay the recorded stream into the sink (ADR-001 ordering). */
  async relay(
    _changeId: string,
    _prompt: string,
    sink: RelaySink,
  ): Promise<RelayOutcome> {
    const kind = this.recorded.resolution;
    // The adapter owns the leading state so it is honest about resume/spawn
    // (FR-23/26), rather than guessing it from the stream.
    sink.emit({ type: "state", state: leadingStateFor(kind) });

    for (const record of this.recorded.events) {
      const event = streamJsonToEvent(record, kind);
      if (event) sink.emit(event);
    }

    return { kind: "completed", resumed: resumedFor(kind) };
  }
}
