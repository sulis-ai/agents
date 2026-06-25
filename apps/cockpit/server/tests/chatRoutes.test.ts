// WP-002 — per-product chat routes (TDD §2.2/§2.3; ADR-002/003/004).
//
// The server side of the WP-001 seam: three routes built against the shared
// wire types. Drives the router through supertest (no real port bind), with a
// fake `ChatScopeStore` and a programmable `SessionBridge` injected — no shell
// out, no daemon. Pins the WP-002 Definition of Done > Red for the routes:
//
//   GET  /api/chat/:scope/thread   → ChatThreadResponse {messages, provider, productId}
//   POST /api/chat/:scope/message  → SSE ChatStreamEvent (state|chunk*|complete)
//   PUT  /api/chat/:scope/provider → ChatProviderResult {provider, applied:"new-work"}
//
// AI-03 (the load-bearing assertion): `PUT /provider` persists the choice per
// scope and returns `applied:"new-work"`; a session already running is NOT
// re-homed — it keeps its provider; the new choice applies to the NEXT open.
//
// A hostile scope (path traversal) is refused (400) before any store touch —
// the wire-level backstop behind `parseChatScope`.

import { describe, it, expect } from "vitest";
import request from "supertest";
import express, { type Application } from "express";

import { createChatScopeRouter } from "../routes/chatScope";
import type { ChatScopeStore } from "../ports/ChatScopeStore";
import { InFlightLock } from "../lib/inFlightLock";
import type {
  SessionBridge,
  SessionResolution,
  RelaySink,
  RelayOutcome,
} from "../ports/SessionBridge";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ChatProvider, TranscriptMessage } from "../../shared/api-types";

const REAL_SCOPE = "product:dna:product:01HZX9";
const ALL_SCOPE = "product:__all__";

// ─── fakes ────────────────────────────────────────────────────────────────

/** A programmable in-memory ChatScopeStore — the durable LocalThreadStore seam
 *  the production adapter binds; here a fake so the routes test never shells out. */
function fakeStore(): ChatScopeStore & {
  remembered: Map<string, ChatProvider>;
  messages: Map<string, TranscriptMessage[]>;
} {
  const remembered = new Map<string, ChatProvider>();
  const messages = new Map<string, TranscriptMessage[]>();
  return {
    remembered,
    messages,
    async getThread(scope) {
      return {
        messages: messages.get(scope) ?? [],
        provider: remembered.get(scope) ?? "pty",
        productId: scope === ALL_SCOPE ? null : scope.slice("product:".length),
      };
    },
    async rememberProvider(scope, provider) {
      remembered.set(scope, provider);
    },
    async resolveProvider(scope, picked) {
      const REGISTERED: ChatProvider[] = ["pty", "agy"];
      if (picked && REGISTERED.includes(picked)) return picked;
      const r = remembered.get(scope);
      if (r && REGISTERED.includes(r)) return r;
      return "pty";
    },
  };
}

/** A SessionBridge that records each relay (the prompts it streamed). The relay
 *  does NOT carry provider selection (ADR-003: provider rides the daemon/pty
 *  path, not this Claude text relay), so the fake asserts on relays, not on a
 *  provider channel. `relays` lets the AI-03 no-re-home test prove a switch does
 *  not touch an already-completed run. */
function fakeBridge(): SessionBridge & { relays: string[] } {
  const relays: string[] = [];
  return {
    relays,
    async resolveSession(changeId: string): Promise<SessionResolution> {
      return { kind: "fresh", session: { changeId, cwd: "/tmp/x" } };
    },
    async relay(
      _changeId: string,
      prompt: string,
      sink: RelaySink,
    ): Promise<RelayOutcome> {
      relays.push(prompt);
      sink.emit({ type: "state", state: "ready" });
      sink.emit({ type: "chunk", text: "hi" });
      sink.emit({ type: "complete", resumed: false });
      return { kind: "completed", resumed: false };
    },
  };
}

function appWith(
  store: ChatScopeStore,
  bridge: SessionBridge,
  inFlightLock?: import("../lib/inFlightLock").InFlightLock,
): Application {
  const app = express();
  app.use(
    "/api/chat",
    createChatScopeRouter({
      store,
      sessionBridge: bridge,
      ...(inFlightLock ? { inFlightLock } : {}),
    }),
  );
  return app;
}

// ─── GET /thread ────────────────────────────────────────────────────────────

describe("GET /api/chat/:scope/thread", () => {
  it("returns ChatThreadResponse {messages, provider, productId} for a real scope", async () => {
    const store = fakeStore();
    store.messages.set(REAL_SCOPE, [
      { kind: "user", uuid: "u1", timestamp: "2026-06-25T00:00:00Z", text: "hi" },
    ]);
    store.remembered.set(REAL_SCOPE, "agy");
    const res = await request(appWith(store, fakeBridge())).get(
      `/api/chat/${encodeURIComponent(REAL_SCOPE)}/thread`,
    );
    expect(res.status).toBe(200);
    expect(Object.keys(res.body).sort()).toEqual([
      "messages",
      "productId",
      "provider",
    ]);
    expect(res.body.provider).toBe("agy");
    expect(res.body.productId).toBe("dna:product:01HZX9");
    expect(res.body.messages).toHaveLength(1);
  });

  it("resolves productId to null for the overview scope (product:__all__)", async () => {
    const res = await request(appWith(fakeStore(), fakeBridge())).get(
      `/api/chat/${encodeURIComponent(ALL_SCOPE)}/thread`,
    );
    expect(res.status).toBe(200);
    expect(res.body.productId).toBeNull();
  });

  it("rejects a path-traversal scope with 400 (the parseChatScope backstop)", async () => {
    const res = await request(appWith(fakeStore(), fakeBridge())).get(
      `/api/chat/${encodeURIComponent("product:../../etc/passwd")}/thread`,
    );
    expect(res.status).toBe(400);
  });
});

// ─── PUT /provider (AI-03) ──────────────────────────────────────────────────

describe("PUT /api/chat/:scope/provider", () => {
  it("persists the choice per scope and returns {provider, applied:'new-work'}", async () => {
    const store = fakeStore();
    const res = await request(appWith(store, fakeBridge()))
      .put(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/provider`)
      .send({ provider: "agy" });
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ provider: "agy", applied: "new-work" });
    // Persisted per scope.
    expect(store.remembered.get(REAL_SCOPE)).toBe("agy");
  });

  it("AI-03: switching does NOT re-home a live/completed run — it only persists for NEW work", async () => {
    const store = fakeStore();
    const bridge = fakeBridge();
    const app = appWith(store, bridge);

    // A first message completes (one relay recorded).
    await request(app)
      .post(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/message`)
      .send({ prompt: "first" });
    expect(bridge.relays).toEqual(["first"]);

    // Switch the provider — must NOT touch/re-home the prior run; it only
    // remembers the choice for new work (no extra relay, persisted in the store).
    const put = await request(app)
      .put(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/provider`)
      .send({ provider: "agy" });
    expect(put.body.applied).toBe("new-work");
    expect(bridge.relays).toEqual(["first"]); // prior run untouched
    expect(store.remembered.get(REAL_SCOPE)).toBe("agy"); // persisted for next open

    // The next message is NEW work (a new relay); the persisted choice now
    // resolves to agy for the daemon/pty open path (ADR-003).
    await request(app)
      .post(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/message`)
      .send({ prompt: "second" });
    expect(bridge.relays).toEqual(["first", "second"]);
    expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("agy");
  });

  it("rejects an unregistered provider with 400 (closed union)", async () => {
    const res = await request(appWith(fakeStore(), fakeBridge()))
      .put(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/provider`)
      .send({ provider: "gemini" });
    expect(res.status).toBe(400);
  });
});

// ─── POST /message (SSE) ────────────────────────────────────────────────────

describe("POST /api/chat/:scope/message", () => {
  it("streams the existing ChatStreamEvent SSE (state|chunk*|complete)", async () => {
    const res = await request(appWith(fakeStore(), fakeBridge()))
      .post(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/message`)
      .send({ prompt: "do the thing" });
    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toContain("text/event-stream");
    expect(res.text).toContain('"type":"state"');
    expect(res.text).toContain('"type":"chunk"');
    expect(res.text).toContain('"type":"complete"');
  });

  it("relays the prompt through the SessionBridge (the text relay seam)", async () => {
    const store = fakeStore();
    store.remembered.set(REAL_SCOPE, "agy"); // remembered choice resolves, but
    const bridge = fakeBridge(); // the relay carries text only, not provider.
    await request(appWith(store, bridge))
      .post(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/message`)
      .send({ prompt: "go" });
    expect(bridge.relays).toEqual(["go"]);
    // The provider resolves to the remembered choice for the daemon open path.
    expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("agy");
  });

  it("refuses a send when the scope is already in flight → SESSION_BUSY (FR-20 one-in-flight)", async () => {
    const store = fakeStore();
    const bridge = fakeBridge();
    // Inject a lock with the scope already held — the next send must be refused
    // before it ever relays (no second session racing the same thread).
    const lock = new InFlightLock();
    lock.acquire(REAL_SCOPE);
    const res = await request(appWith(store, bridge, lock))
      .post(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/message`)
      .send({ prompt: "second" });
    expect(res.status).toBe(409);
    expect(res.body.code).toBe("SESSION_BUSY");
    expect(bridge.relays).toEqual([]); // refused before relaying
  });

  it("releases the in-flight lock after a send completes, so the next send proceeds", async () => {
    const store = fakeStore();
    const bridge = fakeBridge();
    const lock = new InFlightLock();
    const app = appWith(store, bridge, lock);
    await request(app)
      .post(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/message`)
      .send({ prompt: "first" });
    expect(lock.isHeld(REAL_SCOPE)).toBe(false); // released in finally
    await request(app)
      .post(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/message`)
      .send({ prompt: "second" });
    expect(bridge.relays).toEqual(["first", "second"]);
  });

  it("rejects an empty prompt with 400", async () => {
    const res = await request(appWith(fakeStore(), fakeBridge()))
      .post(`/api/chat/${encodeURIComponent(REAL_SCOPE)}/message`)
      .send({ prompt: "  " });
    expect(res.status).toBe(400);
  });
});
