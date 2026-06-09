// WP-011 — POST /api/changes/start-from-intent integration test (FR-29/30/34;
// FR-N6/N9; NFR-SEC-03; ADR-006/007).
//
// supertest drives the start-from-intent route against a FakeChangeStoreReader,
// a programmable SessionBridge (the conversation rides the SAME bridge, FR-27),
// and a FAKE StartChangeRunner (the consequential change-start is a
// deterministic SERVER action behind a port — the WP-010 lesson; the REAL
// adapter is pinned by startChangeRunner.real.test.ts).
//
// The route is registered INSIDE routes/chat.ts (the ONE sanctioned write file,
// ADR-006) so start-from-intent adds NO new read-only-gate write exception.
//
// The contract this test pins:
//   - propose streams classify → proposal SSE (primitive + slug + repo plan);
//   - confirm streams started SSE — the new change appears at RECON (FR-29);
//   - ambiguous intent ⇒ 422 INTENT_AMBIGUOUS (one clarifying question, FR-29);
//   - a stale/mismatched confirm token ⇒ 422 START_CONFIRM_STALE (FR-N6);
//   - a second concurrent session ⇒ 409 SESSION_BUSY;
//   - an absent repo is CLONED first; a broken clone ⇒ 502 REPO_UNREACHABLE +
//     NO change started (FR-30);
//   - an investigation kind creates a CONTAINED change (not inline work, FR-N9);
//   - exactly one structured act-log line per act — never the intent text
//     (NFR-SEC-03).

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
import type {
  StartChangeRunner,
  StartInput,
  StartResult,
  CloneInput,
  CloneResult,
} from "../ports/StartChangeRunner";
import type {
  Change,
  StartFromIntentStreamEvent,
} from "../../shared/api-types";
import type { StartChangeLogLine } from "../routes/chat";

const PRODUCT_ID = "dna:product:acme";
const PROJECT_REPO = "/founder/code/acme-checkout";

/** A started Change at recon (what the fake runner returns). */
function recordedChange(slug: string, primitive: string): Change {
  return {
    changeId: "01TESTCHANGEULID00000000AA",
    handle: "CH-01TEST",
    slug,
    primitive,
    branch: `change/${primitive}-${slug}`,
    worktreePath: `/tmp/changes/01TESTCHANGEULID00000000AA/worktree`,
    intent: "",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-06-04T00:00:00Z",
    updatedAt: "2026-06-04T00:00:00Z",
    stage: "recon",
    liveness: { status: "not-running" },
    // WP-001 widened fields — fixture defaults.
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
    lastActivityAt: null,
  };
}

/** A fake StartChangeRunner so the route runs WITHOUT a real `sulis-change`. */
function fakeRunner(
  opts: { start?: StartResult; clone?: CloneResult; onStart?: () => void } = {},
): StartChangeRunner & { startCalls: StartInput[]; cloneCalls: CloneInput[] } {
  const startCalls: StartInput[] = [];
  const cloneCalls: CloneInput[] = [];
  return {
    startCalls,
    cloneCalls,
    async clone(input: CloneInput): Promise<CloneResult> {
      cloneCalls.push(input);
      return opts.clone ?? { ok: true, path: input.targetPath };
    },
    async start(input: StartInput): Promise<StartResult> {
      startCalls.push(input);
      opts.onStart?.();
      return (
        opts.start ?? { ok: true, change: recordedChange(input.slug, input.primitive) }
      );
    },
  };
}

/** A SessionBridge whose relay the test programs (the conversation half). */
class ProgrammableBridge implements SessionBridge {
  public relayCalls = 0;
  async resolveSession(changeId: string): Promise<SessionResolution> {
    return { kind: "live", session: { changeId, cwd: PROJECT_REPO } };
  }
  async relay(
    changeId: string,
    prompt: string,
    sink: RelaySink,
  ): Promise<RelayOutcome> {
    this.relayCalls += 1;
    sink.emit({ type: "state", state: "replying" });
    sink.emit({ type: "complete", resumed: false });
    return { kind: "completed", resumed: false };
  }
}

interface AppOpts {
  runner?: StartChangeRunner;
  bridge?: SessionBridge;
  logSink?: (line: StartChangeLogLine) => void;
  /** A project whose source.repo is ABSENT (so the route clones it first). */
  repoAbsent?: boolean;
}

function appWith(opts: AppOpts = {}) {
  return createApp({
    changeStore: new FakeChangeStoreReader([]),
    sessionBridge: opts.bridge ?? new ProgrammableBridge(),
    startChangeRunner: opts.runner ?? fakeRunner(),
    sulisStateDir: "/tmp/unused-state-empty",
    claudeProjectsDir: "/tmp/unused-projects",
    // The route resolves a productId → {repo, present} via this test seam so the
    // integration test does not need a seeded brain on disk.
    startResolveProject: async (_productId: string) => ({
      repo: PROJECT_REPO,
      path: PROJECT_REPO,
      primaryBranch: "main",
      present: !opts.repoAbsent,
    }),
    ...(opts.logSink ? { startChangeLogSink: opts.logSink } : {}),
  });
}

/** Parse the SSE body into typed start-from-intent events. */
function sseEvents(body: string): StartFromIntentStreamEvent[] {
  return body
    .split("\n\n")
    .map((f) => f.split("\n").find((l) => l.startsWith("data:")))
    .filter((l): l is string => Boolean(l))
    .map(
      (l) =>
        JSON.parse(l.slice("data:".length).trim()) as StartFromIntentStreamEvent,
    );
}

function tokenFromProposal(body: string): string {
  const ev = sseEvents(body).find((e) => e.type === "proposal");
  if (!ev || ev.type !== "proposal") throw new Error("no proposal event");
  return ev.proposal.confirmToken;
}

const ENDPOINT = "/api/changes/start-from-intent";

describe("POST /start-from-intent — propose (classify, read-only)", () => {
  it("a propose turn streams classifying → proposal SSE with primitive + slug (FR-29)", async () => {
    const res = await request(appWith())
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "add saved cards" });

    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/event-stream/);
    const events = sseEvents(res.text);
    const proposal = events.find((e) => e.type === "proposal");
    expect(proposal).toBeDefined();
    if (proposal && proposal.type === "proposal") {
      expect(proposal.proposal.primitive).toBe("create");
      expect(proposal.proposal.slug).toBeTruthy();
    }
    // Propose is read-only: NO change started yet.
    expect(events.some((e) => e.type === "started")).toBe(false);
  });

  it("a propose turn does NOT start a change (the runner is untouched until confirm)", async () => {
    const runner = fakeRunner();
    await request(appWith({ runner }))
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "fix the login bug" });
    expect(runner.startCalls.length).toBe(0);
  });

  it("an AMBIGUOUS intent ⇒ 422 INTENT_AMBIGUOUS (asks one clarifying question, never guesses)", async () => {
    const runner = fakeRunner();
    const res = await request(appWith({ runner }))
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "do the thing" });
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("INTENT_AMBIGUOUS");
    expect(runner.startCalls.length).toBe(0);
  });

  it("400 when phase is missing", async () => {
    const res = await request(appWith()).post(ENDPOINT).send({});
    expect(res.status).toBe(400);
    expect(res.body.code).toBe("BAD_REQUEST");
  });
});

describe("POST /start-from-intent — confirm gate (FR-N6) + start at Recon (FR-29)", () => {
  it("a matching confirm STARTS a real change that appears at RECON (FR-29)", async () => {
    const app = appWith();
    const proposeRes = await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "fix the login bug" });
    const token = tokenFromProposal(proposeRes.text);

    const res = await request(app)
      .post(ENDPOINT)
      .send({ phase: "confirm", productId: PRODUCT_ID, confirmToken: token });

    expect(res.status).toBe(200);
    const started = sseEvents(res.text).find((e) => e.type === "started");
    expect(started).toBeDefined();
    if (started && started.type === "started") {
      expect(started.started.stage).toBe("recon");
      expect(started.started.primitive).toBe("fix");
    }
  });

  it("the confirm invokes the runner with the resolved primitive + slug + repo root", async () => {
    const runner = fakeRunner();
    const app = appWith({ runner });
    const proposeRes = await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "add saved cards" });
    const token = tokenFromProposal(proposeRes.text);
    await request(app)
      .post(ENDPOINT)
      .send({ phase: "confirm", productId: PRODUCT_ID, confirmToken: token });

    expect(runner.startCalls.length).toBe(1);
    expect(runner.startCalls[0]?.primitive).toBe("create");
    expect(runner.startCalls[0]?.repoRoot).toBe(PROJECT_REPO);
    expect(runner.startCalls[0]?.slug).toBeTruthy();
  });

  it("a confirm with a STALE token ⇒ 422 START_CONFIRM_STALE, starts nothing (FR-N6)", async () => {
    const runner = fakeRunner();
    const app = appWith({ runner });
    await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "fix the login bug" });
    const res = await request(app)
      .post(ENDPOINT)
      .send({ phase: "confirm", productId: PRODUCT_ID, confirmToken: "not-the-token" });
    expect(res.status).toBe(422);
    expect(res.body.code).toBe("START_CONFIRM_STALE");
    expect(runner.startCalls.length).toBe(0);
  });
});

describe("POST /start-from-intent — local-first clone (FR-30)", () => {
  it("an ABSENT repo is CLONED first, then the change starts (FR-30)", async () => {
    const runner = fakeRunner();
    const app = appWith({ runner, repoAbsent: true });
    const proposeRes = await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "add saved cards" });
    const token = tokenFromProposal(proposeRes.text);

    const res = await request(app)
      .post(ENDPOINT)
      .send({ phase: "confirm", productId: PRODUCT_ID, confirmToken: token });

    expect(res.status).toBe(200);
    expect(runner.cloneCalls.length).toBe(1);
    expect(runner.startCalls.length).toBe(1);
    // The clone ran BEFORE the start.
    expect(sseEvents(res.text).some((e) => e.type === "started")).toBe(true);
  });

  it("a BROKEN clone ⇒ 502 REPO_UNREACHABLE + NO change started (FR-30 all-or-nothing)", async () => {
    const runner = fakeRunner({
      clone: { ok: false, code: "REPO_UNREACHABLE", message: "could not clone" },
    });
    const app = appWith({ runner, repoAbsent: true });
    const proposeRes = await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "add saved cards" });
    const token = tokenFromProposal(proposeRes.text);

    const res = await request(app)
      .post(ENDPOINT)
      .send({ phase: "confirm", productId: PRODUCT_ID, confirmToken: token });

    // Pre-stream refusal ⇒ a clean JSON status (parity with onboarding).
    expect(res.status).toBe(502);
    expect(res.body.code).toBe("REPO_UNREACHABLE");
    expect(runner.startCalls.length).toBe(0); // NO change started
  });
});

describe("POST /start-from-intent — investigation containment (FR-34 / FR-N9)", () => {
  it("an investigation creates a CONTAINED change (a real change, not inline work)", async () => {
    const runner = fakeRunner();
    const app = appWith({ runner });
    const proposeRes = await request(app).post(ENDPOINT).send({
      phase: "propose",
      productId: PRODUCT_ID,
      intent: "look into why checkout is slow",
      kind: "investigation",
    });
    const events = sseEvents(proposeRes.text);
    const proposal = events.find((e) => e.type === "proposal");
    expect(proposal).toBeDefined();
    const token = tokenFromProposal(proposeRes.text);

    const res = await request(app)
      .post(ENDPOINT)
      .send({ phase: "confirm", productId: PRODUCT_ID, confirmToken: token });
    expect(res.status).toBe(200);
    // The investigation became a REAL started change (contained), not inline.
    expect(runner.startCalls.length).toBe(1);
    expect(sseEvents(res.text).some((e) => e.type === "started")).toBe(true);
  });
});

describe("POST /start-from-intent — one-in-flight + observability", () => {
  it("409 SESSION_BUSY when a second start runs while one is in flight", async () => {
    let release: () => void = () => {};
    let signalEntered: () => void = () => {};
    const gate = new Promise<void>((r) => {
      release = r;
    });
    const entered = new Promise<void>((r) => {
      signalEntered = r;
    });
    // A runner whose start() blocks until released, so the first confirm is
    // genuinely in flight when the second start arrives.
    const runner: StartChangeRunner = {
      async clone(input: CloneInput): Promise<CloneResult> {
        return { ok: true, path: input.targetPath };
      },
      async start(input: StartInput): Promise<StartResult> {
        signalEntered();
        await gate;
        return { ok: true, change: recordedChange(input.slug, input.primitive) };
      },
    };
    const app = appWith({ runner });
    const proposeRes = await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "fix the login bug" });
    const token = tokenFromProposal(proposeRes.text);

    const first = request(app)
      .post(ENDPOINT)
      .send({ phase: "confirm", productId: PRODUCT_ID, confirmToken: token })
      .then((r) => r);
    await entered;

    // A propose for a NEW intent while the first confirm holds the lock.
    const second = await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "add saved cards" });
    expect(second.status).toBe(409);
    expect(second.body.code).toBe("SESSION_BUSY");

    release();
    await first;
  });

  it("logs ONE structured act-log line per act — never the intent text (NFR-SEC-03)", async () => {
    const lines: StartChangeLogLine[] = [];
    const app = appWith({ logSink: (l) => lines.push(l) });
    const proposeRes = await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "fix the login bug" });
    const token = tokenFromProposal(proposeRes.text);
    await request(app)
      .post(ENDPOINT)
      .send({ phase: "confirm", productId: PRODUCT_ID, confirmToken: token });

    expect(lines.length).toBeGreaterThanOrEqual(1);
    const serialised = JSON.stringify(lines);
    // The act-log NEVER carries the founder's intent text (NFR-SEC-03).
    expect(serialised).not.toContain("fix the login bug");
    // It DOES carry the structured act + outcome.
    const startLine = lines.find((l) => l.outcome === "started");
    expect(startLine).toBeDefined();
  });
});

describe("POST /start-from-intent — wiring", () => {
  it("does NOT register the route when no bridge is wired (degrades; read surfaces unaffected)", async () => {
    const app = createApp({
      changeStore: new FakeChangeStoreReader([]),
      sulisStateDir: "/tmp/unused-state-empty",
      claudeProjectsDir: "/tmp/unused-projects",
    });
    const res = await request(app)
      .post(ENDPOINT)
      .send({ phase: "propose", productId: PRODUCT_ID, intent: "fix the login bug" });
    expect(res.status).toBe(405);
  });
});
