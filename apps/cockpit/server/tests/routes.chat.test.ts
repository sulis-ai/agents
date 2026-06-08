// WP-005 — POST /api/changes/:id/chat relay route (TDD §3.1, ADR-001/003/004).
//
// The relay pipeline in its load-bearing order:
//   acquire lock → resolveSession → bind → act → stream SSE → release.
//
// supertest drives the route against a FakeChangeStoreReader + a programmable
// fake SessionBridge so the failure paths are deterministic and CI-runnable:
//   - 409 SESSION_BUSY            (a second send while this change streams, FR-20)
//   - 422 SESSION_CHANGE_MISMATCH (zero bytes, no process touched, FR-21/N2)
//   - 502 SESSION_UNREACHABLE     (NOT marked delivered, FR-19/N3)
//   - 200 SSE state→chunk*→complete (the happy round-trip, ADR-001)
//   - mid-stream drop ⇒ partial preserved + interrupted (FR-22)
//   - one structured log line per send, never the body/reply (NFR-SEC-03)

import { describe, it, expect, vi, beforeAll, afterAll } from "vitest";
import request from "supertest";
import { mkdtemp, mkdir, writeFile, rm, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import { mangleCwd } from "../lib/mangleCwd";
import { deriveThreadId } from "../lib/threadIdentity";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type {
  SessionBridge,
  SessionResolution,
  RelaySink,
  RelayOutcome,
} from "../ports/SessionBridge";

const CHANGE_ID = "01CHATAAAAAAAAAAAAAAAAAAAA";
const WORKTREE = "/tmp/wp-005-change-worktree";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: CHANGE_ID,
    handle: "CH-01CHAT",
    slug: "chat-change",
    primitive: "create",
    branch: "change/chat-change",
    worktreePath: WORKTREE,
    intent: "the chat change",
    baseBranch: "dev",
    baseSha: null,
    createdAt: "2026-06-01T10:00:00Z",
    updatedAt: "2026-06-01T10:00:00Z",
    stage: "implement",
    ...overrides,
  };
}

/** A SessionBridge whose behaviour the test programs per-case. */
class ProgrammableBridge implements SessionBridge {
  /**
   * The 4th `originEnv` argument the route passed to the most recent `relay`
   * (WP-002 wiring; WP-004 relay computation). `undefined` means the route
   * spawned unstamped — the degradation path (ADR-013). Captured so a test can
   * assert the assisted-origin stamp end-to-end.
   */
  public lastOriginEnv: Record<string, string> | undefined;
  public relayCallCount = 0;

  constructor(
    private readonly opts: {
      resolution?: SessionResolution;
      /** Override relay; default emits a clean happy stream. */
      onRelay?: (
        changeId: string,
        prompt: string,
        sink: RelaySink,
      ) => Promise<RelayOutcome>;
    } = {},
  ) {}

  async resolveSession(changeId: string): Promise<SessionResolution> {
    return (
      this.opts.resolution ?? {
        kind: "live",
        session: { changeId, cwd: WORKTREE },
      }
    );
  }

  async relay(
    changeId: string,
    prompt: string,
    sink: RelaySink,
    originEnv?: Record<string, string>,
  ): Promise<RelayOutcome> {
    this.relayCallCount += 1;
    this.lastOriginEnv = originEnv;
    if (this.opts.onRelay) return this.opts.onRelay(changeId, prompt, sink);
    sink.emit({ type: "state", state: "replying" });
    sink.emit({ type: "chunk", text: "hello " });
    sink.emit({ type: "chunk", text: "there" });
    sink.emit({ type: "complete", resumed: false });
    return { kind: "completed", resumed: false };
  }
}

function appWith(
  bridge: SessionBridge,
  records: ChangeStoreRecord[] = [record()],
) {
  return createApp({
    changeStore: new FakeChangeStoreReader(records),
    sessionBridge: bridge,
    sulisStateDir: "/tmp/unused-state",
    claudeProjectsDir: "/tmp/unused-projects",
  });
}

describe("POST /api/changes/:id/chat — happy round-trip (ADR-001)", () => {
  it("streams state → chunk* → complete as SSE", async () => {
    const app = appWith(new ProgrammableBridge());
    const res = await request(app)
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "hi" });

    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/event-stream/);
    expect(res.headers["cache-control"]).toMatch(/no-cache/);
    // SSE frames: each event is `data: {json}\n\n`.
    expect(res.text).toContain('"type":"state"');
    expect(res.text).toContain('"type":"chunk"');
    expect(res.text).toContain('"type":"complete"');
    expect(res.text).toContain("hello ");
  });

  it("honestly reports resumed=true on a resume (FR-26)", async () => {
    const bridge = new ProgrammableBridge({
      resolution: {
        kind: "resumable",
        session: { changeId: CHANGE_ID, cwd: WORKTREE },
      },
      onRelay: async (_id, _p, sink) => {
        sink.emit({ type: "state", state: "resuming" });
        sink.emit({ type: "chunk", text: "back" });
        sink.emit({ type: "complete", resumed: true });
        return { kind: "completed", resumed: true };
      },
    });
    const res = await request(appWith(bridge))
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "continue" });
    expect(res.text).toContain('"resumed":true');
  });
});

describe("POST /api/changes/:id/chat — refusals", () => {
  it("404 for an unknown change", async () => {
    const res = await request(appWith(new ProgrammableBridge(), []))
      .post(`/api/changes/01NOPE000000000000000000/chat`)
      .send({ prompt: "hi" });
    expect(res.status).toBe(404);
    expect(res.body.code).toBe("NOT_FOUND");
  });

  it("422 SESSION_CHANGE_MISMATCH with ZERO bytes when the resolved session is mis-bound (FR-21/N2)", async () => {
    const relaySpy = vi.fn();
    const bridge = new ProgrammableBridge({
      // Resolution points at a DIFFERENT change's worktree → binding fails.
      resolution: {
        kind: "live",
        session: {
          changeId: "01OTHER0000000000000000000",
          cwd: "/tmp/other-worktree",
        },
      },
      onRelay: async (id, p, sink) => {
        relaySpy();
        sink.emit({ type: "chunk", text: "should never happen" });
        return { kind: "completed", resumed: false };
      },
    });
    const res = await request(appWith(bridge))
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "hi" });

    expect(res.status).toBe(422);
    expect(res.body.code).toBe("SESSION_CHANGE_MISMATCH");
    // Zero bytes delivered, no process touched: relay was never called.
    expect(relaySpy).not.toHaveBeenCalled();
    expect(res.text).not.toContain("should never happen");
  });

  it("502 SESSION_UNREACHABLE and NOT delivered when the session can't start (FR-19/N3)", async () => {
    const bridge = new ProgrammableBridge({
      onRelay: async () => ({
        kind: "unreachable",
        detail: "bridge start failed",
      }),
    });
    const res = await request(appWith(bridge))
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "hi" });
    expect(res.status).toBe(502);
    expect(res.body.code).toBe("SESSION_UNREACHABLE");
  });

  it("409 SESSION_BUSY when a second send arrives while THIS change streams (FR-20)", async () => {
    // First relay blocks until we release it; the second send must be refused.
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const bridge = new ProgrammableBridge({
      onRelay: async (_id, _p, sink) => {
        sink.emit({ type: "state", state: "replying" });
        await gate; // hold the lock
        sink.emit({ type: "complete", resumed: false });
        return { kind: "completed", resumed: false };
      },
    });
    const app = appWith(bridge);

    // Dispatch the first request via `.then()` so supertest actually fires it
    // NOW (it is lazy otherwise), letting it acquire the lock + start streaming
    // before the second send arrives.
    const first = request(app)
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "one" })
      .then((r) => r);
    // Give the first request time to acquire the lock + start streaming.
    await new Promise((r) => setTimeout(r, 100));
    const second = await request(app)
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "two" });

    expect(second.status).toBe(409);
    expect(second.body.code).toBe("SESSION_BUSY");

    release();
    await first;
  });

  it("a send after the first completes is allowed (lock released, Q10 resend)", async () => {
    const app = appWith(new ProgrammableBridge());
    const one = await request(app)
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "one" });
    expect(one.status).toBe(200);
    const two = await request(app)
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "two" });
    expect(two.status).toBe(200);
  });

  it("400 when the prompt is missing/empty", async () => {
    const res = await request(appWith(new ProgrammableBridge()))
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({});
    expect(res.status).toBe(400);
  });
});

describe("POST /api/changes/:id/chat — mid-stream drop (FR-22)", () => {
  it("emits interrupted + preserves the partial when the reply breaks mid-stream", async () => {
    const bridge = new ProgrammableBridge({
      onRelay: async (_id, _p, sink) => {
        sink.emit({ type: "state", state: "replying" });
        sink.emit({ type: "chunk", text: "partial..." });
        sink.emit({ type: "state", state: "interrupted" });
        return { kind: "interrupted" };
      },
    });
    const res = await request(appWith(bridge))
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "hi" });
    expect(res.text).toContain("partial...");
    expect(res.text).toContain('"state":"interrupted"');
  });
});

describe("POST /api/changes/:id/chat — observability (NFR-SEC-03)", () => {
  it("logs one structured line per send and NEVER the prompt or reply text", async () => {
    const logged: unknown[] = [];
    const bridge = new ProgrammableBridge();
    const app = createApp({
      changeStore: new FakeChangeStoreReader([record()]),
      sessionBridge: bridge,
      sulisStateDir: "/tmp/unused-state",
      claudeProjectsDir: "/tmp/unused-projects",
      chatLogSink: (line) => logged.push(line),
    });
    await request(app)
      .post(`/api/changes/${CHANGE_ID}/chat`)
      .send({ prompt: "SECRET-PROMPT-TEXT" });

    expect(logged.length).toBe(1);
    const line = JSON.stringify(logged[0]);
    expect(line).toContain(CHANGE_ID);
    expect(line).toMatch(/resolution/);
    expect(line).toMatch(/outcome/);
    expect(line).not.toContain("SECRET-PROMPT-TEXT");
    expect(line).not.toContain("hello"); // reply text never logged
  });
});

// ─── WP-004 — assisted-origin wiring end-to-end (ADR-016/017/018) ─────────────
//
// The relay route computes the assisted origin env from the resolved session +
// its transcript (via the ConversationIdentity port, WP-003) and passes it to
// `relay`'s 4th argument (WP-002). A real cockpit-chat commit then carries
// `Sulis-Origin: assisted; conversation=thread_…; turn=<n>`.
//
// These tests use a REAL transcript fixture on disk (no transcript mock — MEA-09)
// so the route's read-only transcript locate+parse runs exactly as in production.
describe("POST /api/changes/:id/chat — assisted origin wiring (WP-004)", () => {
  let worktree: string;
  let projectsDir: string;

  const STEM = "session-relay-abc";
  const ORIGIN_CHANGE = "01CHATORIGINWIRING0000000A";

  /**
   * A transcript with `turnCount` agent turns. A turn is a run of consecutive
   * agent messages (`groupTurns` semantics), so each turn is a user message
   * followed by one assistant message — interleaved so the count is genuine.
   */
  async function writeTranscript(turnCount: number): Promise<string> {
    const sessionDir = join(projectsDir, mangleCwd(worktree));
    await mkdir(sessionDir, { recursive: true });
    const lines: string[] = [];
    for (let i = 0; i < turnCount; i++) {
      // Each user immediately precedes its assistant reply (chronological, as a
      // real transcript appends), so the post-sort order keeps the turns
      // interleaved and `groupTurns` counts them as distinct turns.
      lines.push(
        JSON.stringify({
          type: "user",
          uuid: `u${i}`,
          timestamp: `2026-06-03T09:0${i}:00Z`,
          cwd: worktree,
          message: { role: "user", content: `ask ${i}` },
        }),
      );
      lines.push(
        JSON.stringify({
          type: "assistant",
          uuid: `a${i}`,
          timestamp: `2026-06-03T09:0${i}:30Z`,
          cwd: worktree,
          message: { role: "assistant", content: [{ type: "text", text: `turn ${i}` }] },
        }),
      );
    }
    const path = join(sessionDir, `${STEM}.jsonl`);
    await writeFile(path, `${lines.join("\n")}\n`, "utf8");
    return path;
  }

  function originRecord(): ChangeStoreRecord {
    return record({ changeId: ORIGIN_CHANGE, worktreePath: worktree });
  }

  function appWithOrigin(bridge: SessionBridge, logged?: unknown[]) {
    return createApp({
      changeStore: new FakeChangeStoreReader([originRecord()]),
      sessionBridge: bridge,
      sulisStateDir: "/tmp/unused-state",
      claudeProjectsDir: projectsDir,
      ...(logged ? { chatLogSink: (line) => logged.push(line) } : {}),
    });
  }

  beforeAll(async () => {
    worktree = await realpath(await mkdtemp(join(tmpdir(), "wp004-relay-wt-")));
    projectsDir = await mkdtemp(join(tmpdir(), "wp004-relay-projects-"));
  });

  afterAll(async () => {
    await rm(worktree, { recursive: true, force: true });
    await rm(projectsDir, { recursive: true, force: true });
  });

  it("passes an assisted originEnv (conversation=thread_<stem>, turn=existing+1) to relay over a resumable resolution", async () => {
    const ref = await writeTranscript(2); // two existing turns → in-flight turn 3
    const bridge = new ProgrammableBridge({
      resolution: {
        kind: "resumable",
        session: { changeId: ORIGIN_CHANGE, cwd: worktree, lastSessionRef: ref },
      },
    });

    const res = await request(appWithOrigin(bridge))
      .post(`/api/changes/${ORIGIN_CHANGE}/chat`)
      .send({ prompt: "make a change" });

    expect(res.status).toBe(200);
    expect(bridge.lastOriginEnv).toBeDefined();
    const body = bridge.lastOriginEnv?.SULIS_ORIGIN;
    expect(body).toBe(
      `assisted; conversation=${deriveThreadId(STEM)}; turn=3`,
    );
  });

  it("degrades: a fresh resolution (no transcript) relays with NO origin env and still completes", async () => {
    const bridge = new ProgrammableBridge({
      resolution: {
        kind: "fresh",
        session: { changeId: ORIGIN_CHANGE, cwd: worktree },
      },
    });

    const res = await request(appWithOrigin(bridge))
      .post(`/api/changes/${ORIGIN_CHANGE}/chat`)
      .send({ prompt: "first message" });

    expect(res.status).toBe(200);
    expect(res.text).toContain('"type":"complete"');
    expect(bridge.relayCallCount).toBe(1);
    expect(bridge.lastOriginEnv).toBeUndefined();
  });

  it("the relay log line carries originStamped and NEVER the prompt or the thread-id body", async () => {
    const ref = await writeTranscript(1);
    const logged: unknown[] = [];
    const bridge = new ProgrammableBridge({
      resolution: {
        kind: "resumable",
        session: { changeId: ORIGIN_CHANGE, cwd: worktree, lastSessionRef: ref },
      },
    });

    await request(appWithOrigin(bridge, logged))
      .post(`/api/changes/${ORIGIN_CHANGE}/chat`)
      .send({ prompt: "SECRET-RELAY-PROMPT" });

    expect(logged.length).toBe(1);
    const line = JSON.stringify(logged[0]);
    // Observable that the round-trip stamped (NFR-SEC-03: boolean only).
    expect(line).toContain('"originStamped":true');
    // The thread-id body / prompt MUST NOT appear in the log line.
    expect(line).not.toContain("SECRET-RELAY-PROMPT");
    expect(line).not.toContain(deriveThreadId(STEM));
    expect(line).not.toContain(STEM);
  });

  it("a live resolution (no lastSessionRef) relays unstamped (the WP-003 adapter derives the id from the ref)", async () => {
    // A live, already-attached session carries NO `lastSessionRef` (SessionRef
    // contract), so the shipped LocalTranscriptConversationIdentity (WP-003,
    // consumed unchanged) derives no Thread id and the relay spawns unstamped —
    // the commit degrades to inferred (ADR-013). A live transcript still exists
    // on disk; the route's read-only locate fallback runs but the identity port
    // yields null. (The live Thread id is the later CommunicationService adapter
    // behind the same port — ADR-018.)
    await writeTranscript(1);
    const bridge = new ProgrammableBridge({
      resolution: {
        kind: "live",
        session: { changeId: ORIGIN_CHANGE, cwd: worktree },
      },
    });

    const res = await request(appWithOrigin(bridge))
      .post(`/api/changes/${ORIGIN_CHANGE}/chat`)
      .send({ prompt: "make a live change" });

    expect(res.status).toBe(200);
    expect(bridge.lastOriginEnv).toBeUndefined();
  });
});
