// WP-002 — per-product chat routes (TDD §2.2/§2.3; ADR-002, ADR-003, ADR-004).
//
// The server side of the WP-001 seam, built against the shared wire types. The
// three routes the contract pins:
//
//   GET  /api/chat/:scope/thread   → ChatThreadResponse {messages, provider, productId}
//   POST /api/chat/:scope/message  → SSE ChatStreamEvent (state|chunk*|complete)
//   PUT  /api/chat/:scope/provider → ChatProviderResult {provider, applied:"new-work"}
//
// Provider-on-open (ADR-003) — WHERE the provider is selected. ADR-003 is
// explicit that there are TWO session systems and that provider selection
// belongs on the PROVIDER-AWARE daemon/pty path, NOT on the Claude-only text
// relay (`StreamJsonSessionBridge`, which "has no provider concept at all" —
// ADR-003 rejected adding one). So this route's job is to RESOLVE + REMEMBER the
// scope's provider durably (picked → remembered → pty); the resolved provider is
// consumed at session-open on the daemon/pty path via `resolveChange` →
// `SessionSpec.provider` (the `{provider:"pty"}` literal at index.ts:275 widened
// to that resolver). The `POST /message` relay here is the Claude text-relay seam
// (ADR-003's non-provider-aware system) — it streams the reply; it does NOT
// re-home provider selection onto the relay (that was ADR-003's rejected
// alternative). The route still resolves the provider so a future provider-aware
// relay seam (or the daemon-relay rewire) has the value at hand, and so the log
// records which provider the scope is opening on.
//
// AI-03 (PUT /provider): the choice is PERSISTED per scope and applies to NEW
// work only — `applied:"new-work"` is the fixed contract literal. A session
// already running is NOT re-homed; the route touches no live session, it only
// remembers the choice for the next open.
//
// Every scope is validated through `parseChatScope` (the shared wire guard)
// before any store touch — a hostile string (path traversal, wrong prefix) is a
// 400, the wire-level backstop behind the on-disk `validate_store_id` guard.

import { Router, json as jsonBody } from "express";

import type { ChatScopeStore } from "../ports/ChatScopeStore";
import type {
  SessionBridge,
  RelaySink,
  RelayOutcome,
} from "../ports/SessionBridge";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import type {
  ChatProvider,
  ChatProviderResult,
  ChatStreamEvent,
  ChatThreadResponse,
} from "../../shared/api-types";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (the one source for the chat-scope vocabulary + validator)
import { parseChatScope } from "../../shared/chatScope";
import { InFlightLock } from "../lib/inFlightLock";

/** The registered provider keys (the closed union; ADR-003). A PUT carrying any
 *  other value is a 400 — the client only ever sends one of these. */
const REGISTERED_PROVIDERS: readonly ChatProvider[] = ["pty", "agy"];

export interface ChatScopeRouterDeps {
  /** The durable per-product chat store (ADR-002). */
  store: ChatScopeStore;
  /** The session bridge the message route relays through. This is the Claude
   *  text-relay seam (ADR-003's non-provider-aware system); provider selection
   *  rides the daemon/pty path (`SessionSpec.provider`), not this relay. */
  sessionBridge: SessionBridge;
  /** The one-in-flight lock guarding concurrent sends to the SAME scope
   *  (FR-20 parity with the change-scoped relay). Optional: defaults to a fresh
   *  per-router lock; tests may inject one to observe SESSION_BUSY. */
  inFlightLock?: InFlightLock;
}

export function createChatScopeRouter(deps: ChatScopeRouterDeps): Router {
  const router = Router({ mergeParams: true });
  // One-in-flight lock keyed by scope — the per-product sibling of the relay's
  // change-keyed lock (chat.ts). Two concurrent POSTs to the same scope would
  // otherwise spawn two sessions racing the same durable thread.
  const inFlightLock = deps.inFlightLock ?? new InFlightLock();

  // Body parsing scoped to the write verbs (the GET read route never parses).
  router.use(jsonBody());

  // CH-R5EE44 Fix 3 — the per-CHANGE provider seam (the per-change sibling of the
  // per-product PUT /:scope/provider). Registered BEFORE the `/:scope/...` routes
  // so the literal `change` segment is matched here, never as a `:scope` value.
  // GET reads the change's remembered (resolved) provider for the picker; PUT
  // persists the picker's choice (AI-03: applies to the change's NEXT
  // session-open — the terminal sidecar's `resolveProvider(changeId)` consumes
  // it). A change id is NOT a `ChatScope` — no chat-scope wire vocabulary fork.
  router.get("/change/:id/provider", (req, res, next) => {
    void handleChangeProviderGet(req, res, deps).catch(next);
  });
  router.put("/change/:id/provider", (req, res, next) => {
    void handleChangeProviderPut(req, res, deps).catch(next);
  });

  // GET /:scope/thread — the scope's durable transcript + resolved provider.
  router.get("/:scope/thread", (req, res, next) => {
    void handleThread(req, res, deps).catch(next);
  });

  // PUT /:scope/provider — persist the picker's choice (AI-03: new work).
  router.put("/:scope/provider", (req, res, next) => {
    void handleProvider(req, res, deps).catch(next);
  });

  // POST /:scope/message — relay a turn over SSE (one-in-flight per scope).
  router.post("/:scope/message", (req, res, next) => {
    void handleMessage(req, res, deps, inFlightLock).catch(next);
  });

  return router;
}

/** Validate the `:scope` param through the shared wire guard, or 400. Returns
 *  the validated `ChatScope` or `null` (after sending the 400). */
function requireScope(
  req: import("express").Request,
  res: import("express").Response,
): ReturnType<typeof parseChatScope> {
  const raw = (req.params as { scope?: string }).scope ?? "";
  const scope = parseChatScope(decodeURIComponent(raw));
  if (scope === null) {
    res.status(400).json({ error: "invalid chat scope", code: "BAD_REQUEST" });
    return null;
  }
  return scope;
}

async function handleThread(
  req: import("express").Request,
  res: import("express").Response,
  deps: ChatScopeRouterDeps,
): Promise<void> {
  const scope = requireScope(req, res);
  if (scope === null) return;
  const thread: ChatThreadResponse = await deps.store.getThread(scope);
  res.status(200).json(thread);
}

async function handleProvider(
  req: import("express").Request,
  res: import("express").Response,
  deps: ChatScopeRouterDeps,
): Promise<void> {
  const scope = requireScope(req, res);
  if (scope === null) return;

  const provider = (req.body as { provider?: unknown })?.provider;
  if (
    typeof provider !== "string" ||
    !REGISTERED_PROVIDERS.includes(provider as ChatProvider)
  ) {
    res
      .status(400)
      .json({ error: "provider must be one of: pty, agy", code: "BAD_REQUEST" });
    return;
  }

  // AI-03: persist the choice for NEW work. We touch no live session — the
  // choice applies to the next open, never re-homing a running run.
  await deps.store.rememberProvider(scope, provider as ChatProvider);
  const result: ChatProviderResult = {
    provider: provider as ChatProvider,
    applied: "new-work",
  };
  res.status(200).json(result);
}

/** A safe change-id path component (no traversal, no separators). The store has
 *  its own backstop, but we reject hostile ids at the wire too. */
const SAFE_CHANGE_ID = /^[A-Za-z0-9_-]+$/;

function requireChangeId(
  req: import("express").Request,
  res: import("express").Response,
): string | null {
  const raw = (req.params as { id?: string }).id ?? "";
  const id = decodeURIComponent(raw);
  if (id === "" || !SAFE_CHANGE_ID.test(id)) {
    res.status(400).json({ error: "invalid change id", code: "BAD_REQUEST" });
    return null;
  }
  return id;
}

/** GET /change/:id/provider — the change's resolved (remembered → default)
 *  provider, the value the per-change picker shows as RUNNING (CH-R5EE44 Fix 3). */
async function handleChangeProviderGet(
  req: import("express").Request,
  res: import("express").Response,
  deps: ChatScopeRouterDeps,
): Promise<void> {
  const id = requireChangeId(req, res);
  if (id === null) return;
  const provider = await deps.store.resolveChangeProvider(id);
  res.status(200).json({ provider });
}

/** PUT /change/:id/provider — persist the per-change picker's choice (AI-03:
 *  applies to the change's NEXT session-open; never re-homes a running PTY). */
async function handleChangeProviderPut(
  req: import("express").Request,
  res: import("express").Response,
  deps: ChatScopeRouterDeps,
): Promise<void> {
  const id = requireChangeId(req, res);
  if (id === null) return;

  const provider = (req.body as { provider?: unknown })?.provider;
  if (
    typeof provider !== "string" ||
    !REGISTERED_PROVIDERS.includes(provider as ChatProvider)
  ) {
    res
      .status(400)
      .json({ error: "provider must be one of: pty, agy", code: "BAD_REQUEST" });
    return;
  }

  await deps.store.rememberChangeProvider(id, provider as ChatProvider);
  const result: ChatProviderResult = {
    provider: provider as ChatProvider,
    applied: "new-work",
  };
  res.status(200).json(result);
}

async function handleMessage(
  req: import("express").Request,
  res: import("express").Response,
  deps: ChatScopeRouterDeps,
  inFlightLock: InFlightLock,
): Promise<void> {
  const scope = requireScope(req, res);
  if (scope === null) return;

  const prompt = (req.body as { prompt?: unknown })?.prompt;
  if (typeof prompt !== "string" || prompt.trim() === "") {
    res
      .status(400)
      .json({ error: "a non-empty prompt is required", code: "BAD_REQUEST" });
    return;
  }

  // One-in-flight per scope (FR-20 parity with the change-scoped relay): a
  // concurrent send to the same scope is refused with SESSION_BUSY (409) rather
  // than spawning a second session racing the same durable thread.
  const handle = inFlightLock.acquire(scope);
  if (handle === null) {
    res.status(409).json({
      error: "this chat is already replying — one message at a time",
      code: "SESSION_BUSY",
    });
    return;
  }

  try {
    // Resolve the scope's provider (picked → remembered → pty). The message
    // route carries no explicit pick — the choice is already persisted via
    // PUT /provider. Per ADR-003 the resolved provider is consumed at the
    // daemon/pty session open (`SessionSpec.provider`, wired through
    // `resolveChange`), NOT re-homed onto this Claude text relay (ADR-003's
    // rejected alternative). We resolve it here so the value is available to the
    // daemon path and recorded for the scope; the relay itself streams the reply.
    await deps.store.resolveProvider(scope, null);

    // Ground the relay cwd to a REAL directory for the scope (WP-004, folded
    // ADV-CWD-01): ensure the scope's chat-store dir exists so the session runs
    // in a real, scope-keyed place rather than the server's own dir (the prior
    // `resolveChange(scope) === null → cwd:""`). The grounded dir also backs the
    // durable thread the turns below persist to.
    //
    // Persist the user turn BEFORE relaying (WP-004, folded DAT-PERSIST-01) —
    // through the store's REDACTING append path, so per-product history is real.
    // BOTH are fail-soft: a durable-write hiccup (e.g. the vendored CLI is
    // transiently unavailable) must NOT take chat down — the reply still
    // streams, that turn just isn't persisted. Availability of the conversation
    // outranks durability of one turn (the same posture the assistant-turn
    // append below already takes).
    try {
      await deps.store.groundCwd(scope);
      await deps.store.appendTurn(scope, "user", prompt);
    } catch {
      // Logged-and-tolerated: the relay proceeds; this turn is not persisted.
    }

    // The session key for a chat scope IS the scope (one thread per scope,
    // ADR-002).
    let streamOpened = false;
    // Accumulate the reply text so it can be persisted as the assistant turn
    // after the stream closes (the durable thread is the per-product history).
    let replyText = "";
    const sink: RelaySink = {
      emit: (event: ChatStreamEvent) => {
        if (event.type === "chunk") replyText += event.text;
        if (!streamOpened) {
          openSseHeaders(res);
          streamOpened = true;
        }
        writeSseFrame(res, event);
      },
    };

    let outcome: RelayOutcome;
    try {
      // No `originEnv` is passed: provider selection is NOT carried on the relay
      // (ADR-003). The assisted-origin stamp (the relay's actual 4th-arg
      // contract) is out of scope for the per-product chat relay in this WP.
      outcome = await deps.sessionBridge.relay(scope, prompt, sink);
    } catch {
      outcome = streamOpened
        ? { kind: "interrupted" }
        : { kind: "unreachable", detail: "relay threw before streaming" };
    }

    // Persist the assistant turn ONLY when the relay actually produced a reply
    // (FR-N5 parity: never synthesise/persist an empty or absent reply). A
    // persistence failure must not break the already-delivered stream, so it is
    // swallowed after the reply has been streamed to the client.
    if (replyText.length > 0) {
      try {
        await deps.store.appendTurn(scope, "assistant", replyText);
      } catch {
        // The reply already streamed to the client; a durable-write hiccup is
        // logged-and-tolerated, not surfaced as a failed turn.
      }
    }

    finishMessage(res, outcome, streamOpened);
  } finally {
    handle.release();
  }
}

/** Close the SSE stream (or send a JSON status when nothing streamed). Mirrors
 *  the chat relay's outcome→disposition mapping, scoped to this route. */
function finishMessage(
  res: import("express").Response,
  outcome: RelayOutcome,
  streamOpened: boolean,
): void {
  if (streamOpened) {
    // The stream already carried the lifecycle (state→chunk*→complete /
    // interrupted); just end it.
    res.end();
    return;
  }
  // Nothing streamed — a clean JSON status (zero bytes delivered).
  if (outcome.kind === "unreachable") {
    res
      .status(502)
      .json({ error: "the chat session could not be started", code: "SESSION_UNREACHABLE" });
    return;
  }
  if (outcome.kind === "mismatch") {
    // Defensive contract-completeness: this route does not run the relay's
    // bind step (it relays text by scope, ADR-003), so a conforming bridge does
    // not surface `mismatch` here today. The branch keeps RelayOutcome handling
    // exhaustive so a future bind step (or a bridge that binds internally) maps
    // to the right status rather than falling through to a degenerate 200.
    res
      .status(422)
      .json({ error: "the resolved session does not belong to this scope", code: "SESSION_CHANGE_MISMATCH" });
    return;
  }
  // completed/interrupted with no stream is degenerate; return an empty 200.
  res.status(200).end();
}

// ── SSE wire helpers (scoped to this route) ────────────────────────────────
// The chat relay (routes/chat.ts) has its own module-private copies shared by
// its four in-file consumers (chat/concierge/onboarding/start). Cross-file
// extraction of those would broaden this WP into chat.ts's relay surface; the
// frame shape is the trivial, stable `data: {json}\n\n` SSE convention, so the
// two-line helpers live here too. (Boy-Scout scope, EP-07: bounded to this file.)

function openSseHeaders(res: import("express").Response): void {
  res.status(200);
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  if (typeof (res as { flushHeaders?: () => void }).flushHeaders === "function") {
    (res as { flushHeaders: () => void }).flushHeaders();
  }
}

function writeSseFrame(
  res: import("express").Response,
  event: ChatStreamEvent,
): void {
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}
