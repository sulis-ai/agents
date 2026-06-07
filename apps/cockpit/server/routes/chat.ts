// WP-005 — POST /api/changes/:id/chat — the relay route (TDD §3.1; ADR-001/003/004).
//
// THE ONE SANCTIONED WRITE/ACT PATH in the cockpit (ADR-003). Every other
// route is GET-only and provably read-only; this file is the single allow-
// listed `app.post` exception (and the SessionBridge adapter it calls is the
// single allow-listed process-start). The read-only gate names both by path.
//
// The pipeline order is LOAD-BEARING (TDD §3.1):
//   1. acquire the one-in-flight lock  → else SESSION_BUSY (409), FR-20
//   2. resolveSession (side-effect-free) → live | resumable | fresh, FR-N4
//   3. BIND (ADR-004): positively prove the session belongs to THIS change
//      → else SESSION_CHANGE_MISMATCH (422), zero bytes, no process, FR-21/N2
//   4. act + stream SSE: state → chunk* → complete (ADR-001); on drop,
//      partial preserved + interrupted (FR-22); on can't-start,
//      SESSION_UNREACHABLE (502), not delivered (FR-19/N3)
//   5. release the lock (always — complete / break / fail)
//
// One structured log line per send: { changeId, resolution, outcome, code? } —
// NEVER the prompt body or the reply text (NFR-SEC-03).

import { Router, json as jsonBody } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import type {
  SessionBridge,
  RelaySink,
  RelayOutcome,
} from "../ports/SessionBridge";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type {
  ChatStreamEvent,
  ConciergeStreamEvent,
  OnboardingRequest,
  OnboardingStreamEvent,
  StartFromIntentRequest,
  StartFromIntentStreamEvent,
} from "../../shared/api-types";
import { checkSessionBinding } from "../lib/sessionBinding";
import { InFlightLock } from "../lib/inFlightLock";
import {
  detectRoute,
  buildConciergeContext,
  type ConciergeRoute,
} from "../lib/concierge/conciergeRead";
import { OnboardingOrchestrator } from "../lib/discovery/onboardingOrchestrator";
import {
  StartFromIntentOrchestrator,
  type ResolvedProject,
} from "../lib/discovery/startFromIntent";
import type { StartChangeRunner } from "../ports/StartChangeRunner";
import type { SpineMinter } from "../ports/SpineMinter";
import {
  readProducts,
  IMPLICIT_PRODUCT_ID,
} from "../lib/products/readProducts";

import { requireChange } from "./_change-lookup";

/** A structured relay log line — no body, no reply text (NFR-SEC-03). */
export interface ChatLogLine {
  changeId: string;
  resolution: "live" | "resume" | "spawn";
  outcome: "accepted" | "refused" | "completed" | "broken";
  code?: string;
}

export interface ChatRouterDeps {
  changeStore: ChangeStoreReader;
  sessionBridge: SessionBridge;
  /** The per-change one-in-flight lock (shared singleton across requests). */
  inFlightLock: InFlightLock;
  /** Where the one-line-per-send structured log goes (defaults to no-op). */
  chatLogSink?: (line: ChatLogLine) => void;
}

const RESOLUTION_LABEL: Record<string, ChatLogLine["resolution"]> = {
  live: "live",
  resumable: "resume",
  fresh: "spawn",
};

export function createChatRouter(deps: ChatRouterDeps): Router {
  const router = Router({ mergeParams: true });
  const log = deps.chatLogSink ?? (() => {});

  // JSON body parsing scoped to the relay (read routes never parse a body).
  router.use(jsonBody());

  // The relay is the ONE sanctioned write verb in the cockpit (ADR-003).
  // Mounted at the literal `/api/changes` prefix, so the change id is matched
  // here as `/:id/chat` (an unambiguous full-path POST that works identically
  // in-process and over a real HTTP socket).
  router.post("/:id/chat", (req, res, next) => {
    void handleChat(req, res, deps, log).catch(next);
  });

  return router;
}

async function handleChat(
  req: import("express").Request,
  res: import("express").Response,
  deps: ChatRouterDeps,
  log: (line: ChatLogLine) => void,
): Promise<void> {
  const { id } = req.params as { id: string };
  const prompt = (req.body as { prompt?: unknown })?.prompt;

  // Validate the prompt up front — a missing/empty prompt is a 400.
  if (typeof prompt !== "string" || prompt.trim() === "") {
    res
      .status(400)
      .json({ error: "a non-empty prompt is required", code: "BAD_REQUEST" });
    return;
  }

  // 404 for an unknown change (before touching the lock or the bridge).
  const record = await requireChange(deps.changeStore, id);

  // 1. Acquire the one-in-flight lock → else SESSION_BUSY (FR-20).
  const handle = deps.inFlightLock.acquire(id);
  if (handle === null) {
    log({
      changeId: id,
      resolution: "live",
      outcome: "refused",
      code: "SESSION_BUSY",
    });
    res.status(409).json({
      error: "this change is already replying — one message at a time",
      code: "SESSION_BUSY",
    });
    return;
  }

  try {
    // 2. Resolve (side-effect-free).
    const resolution = await deps.sessionBridge.resolveSession(id);
    const resolutionLabel = RESOLUTION_LABEL[resolution.kind] ?? "live";

    // 3. Bind (ADR-004): fail closed → SESSION_CHANGE_MISMATCH, zero bytes,
    //    no process touched. This runs BEFORE relay so resume/spawn can only
    //    ever act on the targeted change's session (NFR-SEC-06).
    const verdict = checkSessionBinding(
      { changeId: id, worktreePath: record.worktreePath },
      resolution.session,
    );
    if (!verdict.bound) {
      log({
        changeId: id,
        resolution: resolutionLabel,
        outcome: "refused",
        code: "SESSION_CHANGE_MISMATCH",
      });
      res.status(422).json({
        error: "the resolved session does not belong to this change",
        code: "SESSION_CHANGE_MISMATCH",
      });
      return;
    }

    // 4. Act + stream. We open the SSE response LAZILY — only on the first
    //    emitted event — so a session that never starts (zero bytes, FR-19/N3)
    //    can still return a clean 502 JSON status rather than a 200 stream with
    //    an error frame. Once any byte has been streamed, a later failure is an
    //    in-stream error/interrupted event (the connection is already open).
    let streamOpened = false;
    const sink: RelaySink = {
      emit: (event: ChatStreamEvent) => {
        if (!streamOpened) {
          openSseHeaders(res);
          streamOpened = true;
        }
        writeSseFrame(res, event);
      },
    };

    let outcome: RelayOutcome;
    try {
      outcome = await deps.sessionBridge.relay(id, prompt, sink);
    } catch {
      // An unexpected relay throw: if nothing streamed yet, it's unreachable;
      // otherwise a broken stream.
      outcome = streamOpened
        ? { kind: "interrupted" }
        : { kind: "unreachable", detail: "relay threw before streaming" };
    }

    finishOutcome(res, outcome, streamOpened, id, resolutionLabel, log);
  } finally {
    // 5. Always release the lock.
    handle.release();
  }
}

/**
 * Translate the relay outcome into the terminal disposition + the structured
 * log line.
 *
 *   - If the stream NEVER opened (zero bytes), a failure is a clean JSON status
 *     (502 SESSION_UNREACHABLE / 422 SESSION_CHANGE_MISMATCH) — FR-19/N3: the
 *     message is NOT marked delivered. A `completed` with no bytes is degenerate
 *     but handled (the stream opens to carry the complete frame).
 *   - If the stream IS open, the outcome is carried in a terminal SSE
 *     event/state (ADR-001) and the response is ended.
 */
function finishOutcome(
  res: import("express").Response,
  outcome: RelayOutcome,
  streamOpened: boolean,
  changeId: string,
  resolution: ChatLogLine["resolution"],
  log: (line: ChatLogLine) => void,
): void {
  if (!streamOpened) {
    // Nothing was delivered. Return a clean JSON status (FR-19/N3).
    if (outcome.kind === "unreachable") {
      log({
        changeId,
        resolution,
        outcome: "refused",
        code: "SESSION_UNREACHABLE",
      });
      res.status(502).json({
        error: "couldn't reach this change's session",
        code: "SESSION_UNREACHABLE",
      });
      return;
    }
    if (outcome.kind === "mismatch") {
      log({
        changeId,
        resolution,
        outcome: "refused",
        code: "SESSION_CHANGE_MISMATCH",
      });
      res.status(422).json({
        error: "the resolved session does not belong to this change",
        code: "SESSION_CHANGE_MISMATCH",
      });
      return;
    }
    // A completed/interrupted outcome that emitted nothing: open the stream to
    // carry the terminal frame so the client sees an honest close.
    openSseHeaders(res);
  }

  if (outcome.kind === "completed") {
    log({ changeId, resolution, outcome: "completed" });
  } else if (outcome.kind === "interrupted") {
    log({ changeId, resolution, outcome: "broken" });
  } else if (outcome.kind === "unreachable") {
    writeSseFrame(res, {
      type: "error",
      code: "SESSION_UNREACHABLE",
      message: "couldn't reach this change's session",
    });
    log({
      changeId,
      resolution,
      outcome: "refused",
      code: "SESSION_UNREACHABLE",
    });
  } else {
    writeSseFrame(res, {
      type: "error",
      code: "SESSION_CHANGE_MISMATCH",
      message: "the resolved session does not belong to this change",
    });
    log({
      changeId,
      resolution,
      outcome: "refused",
      code: "SESSION_CHANGE_MISMATCH",
    });
  }
  res.end();
}

/** SSE headers (ADR-001 §Consequences): event-stream, no-cache, keep-alive, unbuffered. */
function openSseHeaders(res: import("express").Response): void {
  res.status(200);
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  // Disable proxy/response buffering so chunks flush immediately.
  res.setHeader("X-Accel-Buffering", "no");
  if (
    typeof (res as { flushHeaders?: () => void }).flushHeaders === "function"
  ) {
    (res as { flushHeaders: () => void }).flushHeaders();
  }
}

/**
 * Write one SSE frame: `data: {json}\n\n`. Shared by the chat relay and the
 * concierge query (EP-03 — 2-consumer threshold): both emit a discriminated
 * stream-event union over the same SSE wire shape, so the frame writer lives
 * once. The event type is the caller's union; serialisation is identical.
 */
function writeSseFrame(
  res: import("express").Response,
  event:
    | ChatStreamEvent
    | ConciergeStreamEvent
    | OnboardingStreamEvent
    | StartFromIntentStreamEvent,
): void {
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

// ─── WP-009 — the concierge query route (FR-33/34/N8/N9; ADR-006) ────────────
//
// The concierge front door's read-only relay. It lives in THIS file — the ONE
// already-sanctioned write-verb path (ADR-003) — so the concierge adds NO new
// file-level write exception (WP-009 AC#3 / ADR-006). It rides the SAME bridge
// as the chat (no second bridge, FR-27): a single read-only `relay` over a
// discovery session, mapped from `ChatStreamEvent` → `ConciergeStreamEvent`.
//
// It is READ-ONLY (FR-N8): it does NOT run the chat relay's change-binding
// `resolveSession` path, takes NO in-flight lock (it is not change-scoped),
// mints nothing, and starts no session beyond the one read-only bridge read.
// When the founder's intent is consequential (start / investigate / empty-world
// set-up), `complete` carries a `route` hint — the concierge does NOT act here;
// the front door surfaces a confirm-gated OFFER (FR-N9).

/** The sentinel session the concierge relays over (NOT a change id). */
const CONCIERGE_SESSION = "concierge";

/** A structured concierge log line — no question, no reply text (NFR-SEC-03). */
export interface ConciergeLogLine {
  outcome: "completed" | "refused";
  route: ConciergeRoute;
  code?: string;
}

export interface ConciergeRouterDeps {
  changeStore: ChangeStoreReader;
  sessionBridge: SessionBridge;
  /** One-line-per-query structured log (no question/reply text). Default no-op. */
  conciergeLogSink?: (line: ConciergeLogLine) => void;
}

export function createConciergeRouter(deps: ConciergeRouterDeps): Router {
  const router = Router({ mergeParams: true });
  const log = deps.conciergeLogSink ?? (() => {});

  // JSON body parsing scoped to the concierge query (it carries the question).
  router.use(jsonBody());

  // POST /query — registered HERE (in the sanctioned relay file) so no NEW file
  // gains a write verb. The path remains read-only (no mutation, no process
  // start beyond the read-only bridge read).
  router.post("/query", (req, res, next) => {
    void handleConcierge(req, res, deps, log).catch(next);
  });

  return router;
}

async function handleConcierge(
  req: import("express").Request,
  res: import("express").Response,
  deps: ConciergeRouterDeps,
  log: (line: ConciergeLogLine) => void,
): Promise<void> {
  const question = (req.body as { question?: unknown })?.question;
  const product = (req.body as { product?: unknown })?.product;

  if (typeof question !== "string" || question.trim() === "") {
    res
      .status(400)
      .json({ error: "a non-empty question is required", code: "BAD_REQUEST" });
    return;
  }

  // Read-only context (FR-N8): compose the change store read to ground the
  // answer and decide empty-world routing. Zero writes.
  const context = await buildConciergeContext({
    changeStore: deps.changeStore,
    ...(typeof product === "string" ? { productId: product } : {}),
  });
  const route = detectRoute(question, { worldIsEmpty: context.worldIsEmpty });

  // CONTAINMENT (FR-N9): a consequential intent (investigate / start-work /
  // empty-world set-up) is NEVER answered inline. We short-circuit BEFORE the
  // bridge so the inline read-only relay is never started — the investigation
  // is contained in a change, not run loose in the concierge. The route hint is
  // surfaced as a confirm-gated OFFER by the front door (the concierge does not
  // act). The deterministic detectRoute pre-classifier is the gate; the bridge
  // is reached ONLY for a read-only (route === null) question.
  if (route !== null) {
    openSseHeaders(res);
    writeSseFrame(res, { type: "complete", route });
    log({ outcome: "completed", route });
    res.end();
    return;
  }

  // Stream the read-only answer. We open the SSE response lazily so a bridge
  // that never starts (zero bytes) returns a clean 502 JSON status instead of a
  // 200 stream (FR-19/N3) — parity with the chat relay.
  let streamOpened = false;
  const sink: RelaySink = {
    emit: (event: ChatStreamEvent) => {
      if (!streamOpened) {
        openSseHeaders(res);
        streamOpened = true;
      }
      const mapped = toConciergeEvent(event);
      if (mapped) writeSseFrame(res, mapped);
    },
  };

  let outcome: RelayOutcome;
  try {
    outcome = await deps.sessionBridge.relay(CONCIERGE_SESSION, question, sink);
  } catch {
    outcome = streamOpened
      ? { kind: "interrupted" }
      : { kind: "unreachable", detail: "relay threw before streaming" };
  }

  finishConcierge(res, outcome, streamOpened, route, log);
}

/**
 * Map a chat lifecycle/chunk/error event onto the concierge stream. The
 * concierge's terminal `complete` (with the route hint) is emitted by
 * `finishConcierge`, so a `complete` from the bridge is swallowed here.
 */
function toConciergeEvent(
  event: ChatStreamEvent,
): ConciergeStreamEvent | null {
  switch (event.type) {
    case "state":
      if (event.state === "replying") {
        return { type: "state", state: "replying" };
      }
      // resuming / spawning both read as "thinking" at the front door.
      if (event.state === "resuming" || event.state === "spawning") {
        return { type: "state", state: "thinking" };
      }
      if (event.state === "failed") {
        return { type: "state", state: "failed" };
      }
      return null; // "interrupted" handled by the terminal disposition.
    case "chunk":
      return { type: "chunk", text: event.text };
    case "error":
      return {
        type: "error",
        code: "SESSION_UNREACHABLE",
        message: event.message,
      };
    case "complete":
      return null;
    default:
      return null;
  }
}

/** Translate the relay outcome into the terminal concierge disposition + log. */
function finishConcierge(
  res: import("express").Response,
  outcome: RelayOutcome,
  streamOpened: boolean,
  route: ConciergeRoute,
  log: (line: ConciergeLogLine) => void,
): void {
  if (!streamOpened) {
    // Nothing delivered — return a clean JSON status (FR-19/N3).
    if (outcome.kind === "unreachable" || outcome.kind === "mismatch") {
      log({ outcome: "refused", route, code: "SESSION_UNREACHABLE" });
      res.status(502).json({
        error: "couldn't reach the concierge",
        code: "SESSION_UNREACHABLE",
      });
      return;
    }
    // A completed/interrupted outcome that emitted nothing: open the stream to
    // carry the terminal frame so the client sees an honest close.
    openSseHeaders(res);
  }

  if (outcome.kind === "unreachable" || outcome.kind === "mismatch") {
    writeSseFrame(res, {
      type: "error",
      code: "SESSION_UNREACHABLE",
      message: "couldn't reach the concierge",
    });
    log({ outcome: "refused", route, code: "SESSION_UNREACHABLE" });
    res.end();
    return;
  }

  if (outcome.kind === "interrupted") {
    writeSseFrame(res, {
      type: "error",
      code: "SESSION_UNREACHABLE",
      message: "the answer was interrupted",
    });
    log({ outcome: "refused", route, code: "INTERRUPTED" });
    res.end();
    return;
  }

  // completed — emit the terminal `complete` carrying the route hint (FR-34).
  writeSseFrame(res, { type: "complete", route });
  log({ outcome: "completed", route });
  res.end();
}

// ─── WP-010 — the cold-start onboarding route (ADR-007/008) ──────────────────
//
// The conversational front door for an EMPTY graph (UC-07). It is the SECOND
// confirm-gated ACT path in the cockpit (after the chat relay). It is
// registered HERE — in the ONE already-sanctioned write-verb file (ADR-003) —
// so onboarding adds NO new file-level write exception (WP-010 AC#3 / ADR-006);
// the read-only gate's rule-5 allow-list is unchanged.
//
// It rides the SAME bridge as the chat (no second bridge, FR-27) for the
// CONVERSATION (search / clarify / propose — the agent runs the discover-*
// skills). The consequential MINT + `git init`, however, are DETERMINISTIC
// SERVER actions behind the SpineMinter port (ADR-007 amended): the
// agent-delegated mint proved slow + unreliable (167s, minted nothing live).
// The orchestrator owns only the safety plumbing — scope bound, confirm gate,
// repo find-or-create, idempotency, all-or-nothing — and starts no process
// itself; the SpineMinter adapter is the one sanctioned emitter-invocation site.
//
// One discovery session at a time (one Product per conversation, founder-
// locked): a single in-flight lock yields 409 SESSION_BUSY on a second
// concurrent session, and a single orchestrator instance carries the live
// proposal across the propose→confirm turns.
//
// One structured act-log line per consequential act — never a directory,
// prompt, or reply (NFR-SEC-03).

/** A structured onboarding log line — no chosen area, prompt, or reply text. */
export interface OnboardingLogLine {
  phase: OnboardingRequest["phase"];
  outcome: "proposed" | "minted" | "refused";
  code?: string;
}

export interface OnboardingRouterDeps {
  sessionBridge: SessionBridge;
  /**
   * The deterministic server-side mint + repo find-or-create (ADR-007 amended).
   * The MINT + `git init` go through this port, not the bridge agent.
   */
  spineMinter: SpineMinter;
  /** ~/.sulis (or a test override) — the idempotency probe reads Products here. */
  sulisStateDir: string;
  /** The permitted search root the chosen area must be inside (FR-N7). */
  permittedRoot: string;
  /** One-line-per-act structured log (no area/prompt/reply). Default no-op. */
  onboardingLogSink?: (line: OnboardingLogLine) => void;
}

/** The sentinel discovery session id (NOT a change id). */
const ONBOARDING_LOCK_KEY = "onboarding";

export function createOnboardingRouter(deps: OnboardingRouterDeps): Router {
  const router = Router({ mergeParams: true });
  const log = deps.onboardingLogSink ?? (() => {});
  const lock = new InFlightLock();

  // One orchestrator instance per process carries the live proposal across the
  // propose→confirm turns (one Product per conversation, founder-locked).
  const orchestrator = new OnboardingOrchestrator({
    sessionBridge: deps.sessionBridge,
    spineMinter: deps.spineMinter,
    permittedRoot: deps.permittedRoot,
    newToken: () => randomToken(),
    listProductIds: async () => {
      // Idempotency probe (FR-31): the REAL minted Products (the synthesised
      // single implicit Product is not a real mint, so it is filtered out).
      const { list } = await readProducts({ sulisStateDir: deps.sulisStateDir });
      return list.products
        .map((p) => p.productId)
        .filter((id) => id !== IMPLICIT_PRODUCT_ID);
    },
  });

  router.use(jsonBody());

  router.post("/session", (req, res, next) => {
    void handleOnboarding(req, res, orchestrator, lock, log).catch(next);
  });

  return router;
}

async function handleOnboarding(
  req: import("express").Request,
  res: import("express").Response,
  orchestrator: OnboardingOrchestrator,
  lock: InFlightLock,
  log: (line: OnboardingLogLine) => void,
): Promise<void> {
  const body = req.body as OnboardingRequest;
  const phase = body?.phase;

  // A missing/invalid phase is a 400.
  if (phase !== "search" && phase !== "ask" && phase !== "confirm") {
    res
      .status(400)
      .json({ error: "a valid phase is required", code: "BAD_REQUEST" });
    return;
  }

  // One discovery session at a time (FR — one Product per conversation). A
  // second concurrent session is refused with 409 SESSION_BUSY.
  const handle = lock.acquire(ONBOARDING_LOCK_KEY);
  if (handle === null) {
    log({ phase, outcome: "refused", code: "SESSION_BUSY" });
    res.status(409).json({
      error: "I'm already setting something up — one at a time.",
      code: "SESSION_BUSY",
    });
    return;
  }

  try {
    // PRE-STREAM refusals (parity with the chat relay's lazy-open): a scope
    // violation or a stale confirm returns a clean JSON status, never a 200
    // stream with an error frame (FR-N6/N7).
    const refusal = orchestrator.precheck(body);
    if (refusal) {
      log({ phase, outcome: "refused", code: refusal.code });
      res.status(refusal.status).json({
        error: refusal.message,
        code: refusal.code,
      });
      return;
    }

    // Stream the turn as SSE. We open the headers eagerly here (the orchestrator
    // always emits at least a leading `state`).
    openSseHeaders(res);
    let sawMinted = false;
    let sawError: string | undefined;
    await orchestrator.turn(body, {
      emit: (event: OnboardingStreamEvent) => {
        if (event.type === "minted") sawMinted = true;
        if (event.type === "error") sawError = event.code;
        writeSseFrame(res, event);
      },
    });
    log({
      phase,
      outcome: sawError ? "refused" : sawMinted ? "minted" : "proposed",
      ...(sawError ? { code: sawError } : {}),
    });
    res.end();
  } finally {
    handle.release();
  }
}

// ─── WP-011 — the start-from-intent route (FR-29/30/34; FR-N6/N9; ADR-006/007) ─
//
// Say what you want → (confirm) → a change starts at Recon. The THIRD confirm-
// gated ACT path in the cockpit, registered HERE — in the ONE already-sanctioned
// write-verb file (ADR-003) — so start-from-intent adds NO new file-level write
// exception (WP-011 AC / ADR-006); the read-only gate's allow-list stays
// {chat.ts}.
//
// The classify is a DETERMINISTIC server step (the change-primitives vocabulary,
// FR-29). The consequential change-start is a DETERMINISTIC SERVER action behind
// the StartChangeRunner port (the WP-010 lesson: never delegate the act to the
// bridge agent — that ran 167s and created nothing). The orchestrator owns the
// safety plumbing — confirm gate, local-first clone, all-or-nothing — and starts
// no process itself; the SulisChangeStarter adapter is the one sanctioned site.
//
// One discovery session at a time: a single in-flight lock yields 409
// SESSION_BUSY on a second concurrent start, and a single orchestrator instance
// carries the live proposal across the propose → confirm turns.
//
// One structured act-log line per consequential act — never the intent text
// (NFR-SEC-03).

/** A structured start-from-intent log line — no intent text (NFR-SEC-03). */
export interface StartChangeLogLine {
  phase: StartFromIntentRequest["phase"];
  outcome: "proposed" | "started" | "refused";
  primitive?: string;
  code?: string;
}

export interface StartChangeRouterDeps {
  /** The SAME bridge the chat rides (FR-27) — present so the route mounts. */
  sessionBridge: SessionBridge;
  /** The deterministic server-side change-start (ADR-007). */
  startChangeRunner: StartChangeRunner;
  /** Resolve a productId → its Project repo (or null when unknown). */
  resolveProject: (productId: string) => Promise<ResolvedProject | null>;
  /** One-line-per-act structured log (no intent text). Default no-op. */
  startChangeLogSink?: (line: StartChangeLogLine) => void;
}

/** The sentinel session id (NOT a change id). */
const START_LOCK_KEY = "start-from-intent";

export function createStartChangeRouter(deps: StartChangeRouterDeps): Router {
  const router = Router({ mergeParams: true });
  const log = deps.startChangeLogSink ?? (() => {});
  const lock = new InFlightLock();

  // One orchestrator instance per process carries the live proposal across the
  // propose → confirm turns.
  const orchestrator = new StartFromIntentOrchestrator({
    startChangeRunner: deps.startChangeRunner,
    resolveProject: deps.resolveProject,
    newToken: () => randomToken(),
  });

  router.use(jsonBody());

  // Registered at the LITERAL `/start-from-intent` path; mounted under
  // `/api/changes` in app.ts (a literal-prefix mount, mirroring the chat relay).
  router.post("/start-from-intent", (req, res, next) => {
    void handleStartChange(req, res, orchestrator, lock, log).catch(next);
  });

  return router;
}

async function handleStartChange(
  req: import("express").Request,
  res: import("express").Response,
  orchestrator: StartFromIntentOrchestrator,
  lock: InFlightLock,
  log: (line: StartChangeLogLine) => void,
): Promise<void> {
  const body = req.body as StartFromIntentRequest;
  const phase = body?.phase;

  // A missing/invalid phase is a 400.
  if (phase !== "propose" && phase !== "confirm") {
    res.status(400).json({ error: "a valid phase is required", code: "BAD_REQUEST" });
    return;
  }

  // One start at a time. A second concurrent session is refused with 409.
  const handle = lock.acquire(START_LOCK_KEY);
  if (handle === null) {
    log({ phase, outcome: "refused", code: "SESSION_BUSY" });
    res.status(409).json({
      error: "I'm already starting something — one at a time.",
      code: "SESSION_BUSY",
    });
    return;
  }

  try {
    // PRE-STREAM refusals (parity with the onboarding/chat lazy-open pattern):
    // an ambiguous intent, a stale confirm, or an unreachable repo returns a
    // clean JSON status — never a 200 stream with an error frame (FR-29/30/N6).
    const refusal = await orchestrator.precheck(body);
    if (refusal) {
      log({ phase, outcome: "refused", code: refusal.code });
      res.status(refusal.status).json({ error: refusal.message, code: refusal.code });
      return;
    }

    openSseHeaders(res);
    let sawStarted = false;
    let sawError: string | undefined;
    let startedPrimitive: string | undefined;
    await orchestrator.turn(body, {
      emit: (event: StartFromIntentStreamEvent) => {
        if (event.type === "started") {
          sawStarted = true;
          startedPrimitive = event.started.primitive;
        }
        if (event.type === "error") sawError = event.code;
        writeSseFrame(res, event);
      },
    });
    log({
      phase,
      outcome: sawError ? "refused" : sawStarted ? "started" : "proposed",
      ...(startedPrimitive ? { primitive: startedPrimitive } : {}),
      ...(sawError ? { code: sawError } : {}),
    });
    res.end();
  } finally {
    handle.release();
  }
}

/** A short, opaque confirm token (no crypto needed — it is a same-process nonce). */
function randomToken(): string {
  return `tok-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
