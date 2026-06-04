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
import type { ChatStreamEvent } from "../../shared/api-types";
import { checkSessionBinding } from "../lib/sessionBinding";
import { InFlightLock } from "../lib/inFlightLock";

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
        writeSse(res, event);
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
    writeSse(res, {
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
    writeSse(res, {
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

/** Write one SSE frame: `data: {json}\n\n`. */
function writeSse(
  res: import("express").Response,
  event: ChatStreamEvent,
): void {
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}
