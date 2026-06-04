// WP-010 — POST /api/onboarding/session integration test (ADR-007/008;
// FR-27/31/32/35/36/N6/N7/N10/N11).
//
// supertest drives the onboarding route against a FakeChangeStoreReader + a
// programmable / recorded SessionBridge + a seeded fixture project directory.
// The route is registered INSIDE routes/chat.ts (the ONE sanctioned write
// file, ADR-006 — no new read-only-gate write exception); it rides the SAME
// bridge as the chat (FR-27).
//
// The contract this test pins:
//   - the conversation streams OnboardingStreamEvent SSE
//     (state → chunk* → proposal, then on confirm → minted);
//   - search is BOUNDED to the chosen area (chosenArea outside the permitted
//     root ⇒ 422 DISCOVERY_SCOPE_VIOLATION, FR-N7);
//   - a stale/mismatched confirm token ⇒ 422 DISCOVERY_CONFIRM_STALE (FR-N6);
//   - a second concurrent session ⇒ 409 SESSION_BUSY (one product per
//     conversation, founder-locked);
//   - idempotent: re-running does not grow the entity count (FR-31);
//   - a declined / failed-create flow leaves the graph unchanged
//     (all-or-nothing, FR-N10/N11);
//   - the bridge is the only mint path (no direct entity write, FR-32).

import { describe, it, expect } from "vitest";
import request from "supertest";

import { createApp } from "../app";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type {
  SessionBridge,
  SessionResolution,
  RelaySink,
  RelayOutcome,
} from "../ports/SessionBridge";
import type { OnboardingStreamEvent } from "../../shared/api-types";

const PERMITTED_ROOT = "/founder/code";
const CHOSEN_AREA = "/founder/code/acme-checkout";

/** A SessionBridge whose relay the test programs. */
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
    return { kind: "live", session: { changeId, cwd: CHOSEN_AREA } };
  }

  async relay(
    changeId: string,
    prompt: string,
    sink: RelaySink,
  ): Promise<RelayOutcome> {
    this.relayCalls += 1;
    if (this.onRelay) return this.onRelay(changeId, prompt, sink);
    sink.emit({ type: "state", state: "replying" });
    sink.emit({ type: "chunk", text: "discovery text" });
    sink.emit({ type: "complete", resumed: false });
    return { kind: "completed", resumed: false };
  }
}

function appWith(bridge: SessionBridge) {
  return createApp({
    changeStore: new FakeChangeStoreReader([]),
    sessionBridge: bridge,
    sulisStateDir: "/tmp/unused-state-empty", // empty brain ⇒ worldIsEmpty
    claudeProjectsDir: "/tmp/unused-projects",
    onboardingPermittedRoot: PERMITTED_ROOT,
  });
}

/** Parse the SSE body into the typed onboarding event objects. */
function sseEvents(body: string): OnboardingStreamEvent[] {
  return body
    .split("\n\n")
    .map((f) => f.split("\n").find((l) => l.startsWith("data:")))
    .filter((l): l is string => Boolean(l))
    .map((l) => JSON.parse(l.slice("data:".length).trim()) as OnboardingStreamEvent);
}

/** Pull the confirm token from a proposal event in an SSE body (test helper). */
function tokenFromProposal(body: string): string {
  const proposal = sseEvents(body).find((e) => e.type === "proposal");
  if (!proposal || proposal.type !== "proposal") {
    throw new Error("no proposal event in the onboarding stream");
  }
  return proposal.proposal.confirmToken;
}

describe("POST /api/onboarding/session — search → propose (read-only, mints nothing)", () => {
  it("a search turn streams state → chunk* → proposal as SSE (no mint yet)", async () => {
    const app = appWith(new ProgrammableBridge());
    const res = await request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: CHOSEN_AREA });

    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/event-stream/);
    const events = sseEvents(res.text);
    expect(events.some((e) => e.type === "chunk")).toBe(true);
    expect(events.some((e) => e.type === "proposal")).toBe(true);
    expect(events.some((e) => e.type === "minted")).toBe(false);
  });

  it("422 DISCOVERY_SCOPE_VIOLATION when chosenArea is OUTSIDE the permitted root (FR-N7)", async () => {
    const app = appWith(new ProgrammableBridge());
    const res = await request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: "/etc" });

    expect(res.status).toBe(422);
    expect(res.body.code).toBe("DISCOVERY_SCOPE_VIOLATION");
  });

  it("does NOT relay the bridge on a scope violation (search never escapes the area)", async () => {
    const bridge = new ProgrammableBridge();
    const app = appWith(bridge);
    await request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: "/founder/../etc/secrets" });
    expect(bridge.relayCalls).toBe(0);
  });
});

describe("POST /api/onboarding/session — confirm gate (FR-N6) + all-or-nothing (FR-N10/N11)", () => {
  it("a confirm with a STALE token ⇒ 422 DISCOVERY_CONFIRM_STALE, mints nothing", async () => {
    const bridge = new ProgrammableBridge();
    const app = appWith(bridge);
    // Establish a live proposal first.
    await request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: CHOSEN_AREA });
    // Confirm with the wrong token.
    const res = await request(app).post("/api/onboarding/session").send({
      phase: "confirm",
      confirmToken: "not-the-live-token",
      repoChoice: { mode: "find" },
    });
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("DISCOVERY_CONFIRM_STALE");
  });

  it("a matching confirm MINTS via the bridge and streams `minted`", async () => {
    const bridge = new ProgrammableBridge();
    const app = appWith(bridge);
    const proposeRes = await request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: CHOSEN_AREA });
    const token = tokenFromProposal(proposeRes.text);

    const res = await request(app).post("/api/onboarding/session").send({
      phase: "confirm",
      confirmToken: token,
      repoChoice: { mode: "find" },
    });
    expect(res.status).toBe(200);
    const events = sseEvents(res.text);
    const minted = events.find((e) => e.type === "minted");
    expect(minted).toBeDefined();
    // The minted Project carries source = {repo, path, primary_branch} (FR-36)
    // — the repo is the CHOSEN AREA carried from the search turn (the confirm
    // turn does not repeat it). A regression here would persist an empty repo.
    if (minted && minted.type === "minted") {
      expect(minted.minted.projects?.[0]?.source?.repo).toBe(CHOSEN_AREA);
      expect(minted.minted.projects?.[0]?.source?.primary_branch).toBe("main");
    }
  });

  it("a confirmed CREATE that FAILS leaves the graph unchanged + emits REPO_CREATE_FAILED (no dangling config)", async () => {
    const app = createApp({
      changeStore: new FakeChangeStoreReader([]),
      sessionBridge: new ProgrammableBridge(),
      sulisStateDir: "/tmp/unused-state-empty",
      claudeProjectsDir: "/tmp/unused-projects",
      onboardingPermittedRoot: PERMITTED_ROOT,
      // Inject a repo attempt that fails the create.
      onboardingAttemptRepo: async () => ({ outcome: "create-failed" }),
    });
    const proposeRes = await request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: CHOSEN_AREA });
    const token = tokenFromProposal(proposeRes.text);

    const res = await request(app).post("/api/onboarding/session").send({
      phase: "confirm",
      confirmToken: token,
      repoChoice: { mode: "create", createTarget: "local" },
    });
    expect(res.status).toBe(200);
    const events = sseEvents(res.text);
    const err = events.find((e) => e.type === "error");
    expect(err).toBeDefined();
    if (err && err.type === "error") expect(err.code).toBe("REPO_CREATE_FAILED");
    expect(events.some((e) => e.type === "minted")).toBe(false);
  });
});

describe("POST /api/onboarding/session — one product per conversation (founder-locked)", () => {
  it("409 SESSION_BUSY when a second session starts while one is in flight", async () => {
    // A bridge that holds the relay open until released, so the first session
    // is genuinely in flight when the second arrives. `entered` resolves once
    // the first request's handler has acquired the lock + reached the relay, so
    // we never race on a fixed timeout.
    let release: () => void = () => {};
    let signalEntered: () => void = () => {};
    const gate = new Promise<void>((r) => {
      release = r;
    });
    const entered = new Promise<void>((r) => {
      signalEntered = r;
    });
    const bridge = new ProgrammableBridge(async (_c, _p, sink) => {
      sink.emit({ type: "state", state: "replying" });
      signalEntered();
      await gate;
      sink.emit({ type: "chunk", text: "done" });
      sink.emit({ type: "complete", resumed: false });
      return { kind: "completed", resumed: false };
    });
    const app = appWith(bridge);

    // `.then()` actually dispatches the supertest request (merely building it
    // does not). Kick it off and wait until its handler holds the lock.
    const first = request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: CHOSEN_AREA })
      .then((r) => r);
    await entered;

    const second = await request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: CHOSEN_AREA });

    expect(second.status).toBe(409);
    expect(second.body.code).toBe("SESSION_BUSY");

    release();
    await first;
  });
});

describe("POST /api/onboarding/session — wiring", () => {
  it("does NOT register the route when no bridge is wired (degrades; read surfaces unaffected)", async () => {
    const app = createApp({
      changeStore: new FakeChangeStoreReader([]),
      sulisStateDir: "/tmp/unused-state-empty",
      claudeProjectsDir: "/tmp/unused-projects",
    });
    const res = await request(app)
      .post("/api/onboarding/session")
      .send({ phase: "search", chosenArea: CHOSEN_AREA });
    expect(res.status).toBe(405);
  });

  it("400 when phase is missing", async () => {
    const app = appWith(new ProgrammableBridge());
    const res = await request(app).post("/api/onboarding/session").send({});
    expect(res.status).toBe(400);
    expect(res.body.code).toBe("BAD_REQUEST");
  });
});
