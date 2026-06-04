// WP-009 — POST /api/concierge/query integration test (FR-33/34/N8/N9; ADR-006).
//
// supertest drives the concierge route against a FakeChangeStoreReader +
// a RecordedSessionBridge (the discovery-session fixture; MEA-09 recorded,
// not a mock) + a programmable bridge for the failure/containment cases.
//
// The contract this test pins:
//   - the read-only Q&A path streams ConciergeStreamEvent SSE
//     (state → chunk* → complete) and rides the SAME bridge as the chat
//     (no second bridge; ADR-006);
//   - a consequential intent (start / investigate) carries a `route` hint on
//     `complete` and the concierge does NOT act inline (FR-34/N9);
//   - the bridge being unreachable yields 502 SESSION_UNREACHABLE;
//   - the path performs ZERO writes / mints / session-starts / signals
//     (the relay is called read-only; a containment spy proves no inline act).

import { describe, it, expect, vi } from "vitest";
import request from "supertest";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import { RecordedSessionBridge } from "../adapters/RecordedSessionBridge";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type {
  SessionBridge,
  SessionResolution,
  RelaySink,
  RelayOutcome,
} from "../ports/SessionBridge";

const here = dirname(fileURLToPath(import.meta.url));
const DISCOVERY_FIXTURE = join(
  here,
  "fixtures",
  "recording-bridge-discovery-session.json",
);

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01CHANGE",
    handle: "fix-login-redirect",
    slug: "fix-login-redirect",
    primitive: "fix",
    branch: "change/fix-login-redirect",
    worktreePath: "/tmp/wt/fix-login-redirect",
    intent: "Fix login redirect loop",
    baseBranch: "main",
    baseSha: "abc",
    createdAt: "2026-06-01T00:00:00Z",
    updatedAt: "2026-06-02T00:00:00Z",
    stage: "implement",
    ...overrides,
  };
}

/** A SessionBridge whose relay the test programs (failure / containment). */
class ProgrammableBridge implements SessionBridge {
  public relayCalls = 0;
  constructor(
    private readonly onRelay?: (
      changeId: string,
      prompt: string,
      sink: RelaySink,
    ) => Promise<RelayOutcome>,
  ) {}

  async resolveSession(changeId: string): Promise<SessionResolution> {
    return { kind: "live", session: { changeId, cwd: "/tmp/wt/discovery" } };
  }

  async relay(
    changeId: string,
    prompt: string,
    sink: RelaySink,
  ): Promise<RelayOutcome> {
    this.relayCalls += 1;
    if (this.onRelay) return this.onRelay(changeId, prompt, sink);
    sink.emit({ type: "state", state: "replying" });
    sink.emit({ type: "chunk", text: "answer" });
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

function recordedBridge() {
  return new RecordedSessionBridge({
    fixturePath: DISCOVERY_FIXTURE,
    bridgeCase: "live",
    changeId: "concierge",
    worktreePath: "/tmp/wt/discovery",
  });
}

describe("POST /api/concierge/query — read-only Q&A round-trip (FR-33; ADR-006)", () => {
  it("streams ConciergeStreamEvent state → chunk* → complete as SSE", async () => {
    const app = appWith(recordedBridge());
    const res = await request(app)
      .post("/api/concierge/query")
      .send({ question: "what needs my attention?" });

    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/event-stream/);
    expect(res.headers["cache-control"]).toMatch(/no-cache/);
    expect(res.text).toContain('"type":"state"');
    expect(res.text).toContain('"type":"chunk"');
    expect(res.text).toContain('"type":"complete"');
  });

  it("a read-only question carries route=null on complete (no inline act, FR-N8)", async () => {
    const app = appWith(recordedBridge());
    const res = await request(app)
      .post("/api/concierge/query")
      .send({ question: "which change was I doing the login fix in?" });

    expect(res.status).toBe(200);
    expect(res.text).toContain('"route":null');
  });

  it("400 when the question is missing or empty", async () => {
    const app = appWith(recordedBridge());
    const res = await request(app).post("/api/concierge/query").send({});
    expect(res.status).toBe(400);
    expect(res.body.code).toBe("BAD_REQUEST");
  });
});

describe("POST /api/concierge/query — consequential intent ROUTES, never acts (FR-34/N9)", () => {
  it("an investigation request carries route=start-from-intent on complete (not inline)", async () => {
    const app = appWith(recordedBridge());
    const res = await request(app)
      .post("/api/concierge/query")
      .send({ question: "look into why sign-ups dropped last week" });

    expect(res.status).toBe(200);
    expect(res.text).toContain('"route":"start-from-intent"');
  });

  it("a start-work request carries route=start-from-intent on complete", async () => {
    const app = appWith(recordedBridge());
    const res = await request(app)
      .post("/api/concierge/query")
      .send({ question: "start a change to add saved cards" });

    expect(res.status).toBe(200);
    expect(res.text).toContain('"route":"start-from-intent"');
  });

  it("an empty-world set-up request carries route=onboarding (UC-09→UC-07)", async () => {
    const app = appWith(recordedBridge(), []); // empty world
    const res = await request(app)
      .post("/api/concierge/query")
      .send({ question: "set me up" });

    expect(res.status).toBe(200);
    expect(res.text).toContain('"route":"onboarding"');
  });
});

describe("POST /api/concierge/query — failure (FR-19/N3) + containment (FR-N8)", () => {
  it("502 SESSION_UNREACHABLE when the bridge can't be reached", async () => {
    const bridge = new ProgrammableBridge(async () => ({
      kind: "unreachable",
      detail: "no bridge",
    }));
    const app = appWith(bridge);
    const res = await request(app)
      .post("/api/concierge/query")
      .send({ question: "what needs my attention?" });

    expect(res.status).toBe(502);
    expect(res.body.code).toBe("SESSION_UNREACHABLE");
  });

  it("performs ZERO writes/mints/starts: the relay is the ONLY bridge call, read-only", async () => {
    // The route resolves nothing change-scoped and never starts a session
    // beyond the single read-only relay. We assert relay is called once and
    // resolveSession (the binding/process path) is NOT used by the concierge.
    const bridge = new ProgrammableBridge();
    const resolveSpy = vi.spyOn(bridge, "resolveSession");
    const app = appWith(bridge);

    await request(app)
      .post("/api/concierge/query")
      .send({ question: "what have I got in flight?" });

    expect(bridge.relayCalls).toBe(1);
    // The concierge is NOT change-bound (ADR-006): it does not run the
    // change-binding resolveSession path the chat relay does.
    expect(resolveSpy).not.toHaveBeenCalled();
  });

  it("an interrupted stream closes honestly with an error frame (partial kept, FR-22)", async () => {
    const bridge = new ProgrammableBridge(async (_c, _p, sink) => {
      sink.emit({ type: "state", state: "replying" });
      sink.emit({ type: "chunk", text: "half an answer" });
      return { kind: "interrupted" };
    });
    const app = appWith(bridge);
    const res = await request(app)
      .post("/api/concierge/query")
      .send({ question: "what needs my attention?" });

    expect(res.status).toBe(200);
    // The partial is preserved and the stream closes with an honest error frame
    // (never a fabricated complete — FR-N5).
    expect(res.text).toContain("half an answer");
    expect(res.text).toContain('"type":"error"');
    expect(res.text).not.toContain('"type":"complete"');
  });

  it("does NOT log the question or reply text — one structured line only (NFR-SEC-03)", async () => {
    const lines: unknown[] = [];
    const bridge = new ProgrammableBridge();
    const app = createApp({
      changeStore: new FakeChangeStoreReader([record()]),
      sessionBridge: bridge,
      conciergeLogSink: (line) => lines.push(line),
      sulisStateDir: "/tmp/unused-state",
      claudeProjectsDir: "/tmp/unused-projects",
    });
    await request(app)
      .post("/api/concierge/query")
      .send({ question: "secret question text about the login fix" });

    expect(lines).toHaveLength(1);
    const serialised = JSON.stringify(lines[0]);
    expect(serialised).not.toContain("secret question text");
    expect(serialised).not.toContain("answer");
    expect(serialised).toContain("completed");
  });

  it("does NOT register /api/concierge/query when no bridge is wired (degrades, read surfaces unaffected)", async () => {
    const app = createApp({
      changeStore: new FakeChangeStoreReader([record()]),
      // no sessionBridge
      sulisStateDir: "/tmp/unused-state",
      claudeProjectsDir: "/tmp/unused-projects",
    });
    const res = await request(app)
      .post("/api/concierge/query")
      .send({ question: "anything?" });
    // With no bridge the concierge route is not mounted → 405 (POST on an
    // unregistered path under the GET-only fallback).
    expect(res.status).toBe(405);
  });
});
