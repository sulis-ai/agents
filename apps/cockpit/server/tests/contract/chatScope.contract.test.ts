// WP-001 — per-product chat-scope seam contract test (CF-05/07/09; ADR-002/003/004).
//
// This is the CONTRACT-FIRST seam (CONTRACT_FIRST_STANDARD CF-05): the wire
// shape the cockpit client sends and the server resolves for the per-product
// chat. WP-002 (backend) and WP-003 (frontend) build against THIS shape in
// parallel, so it must be pinned before either side ships behaviour.
//
// What this test pins (TDD §2.3, the four routes):
//   GET  /api/chat/:scope/thread    → ChatThreadResponse
//   POST /api/chat/:scope/message   → SSE ChatStreamEvent (state|chunk*|complete)
//   PUT  /api/chat/:scope/provider  → ChatProviderResult
//   POST /api/changes/start-from-intent (REUSED verbatim — ADR-004, no new shape)
//
// The real gate is `tsc --noEmit`: each fixture below is constructed field-by-
// field from the WP Contract's declared shape, so if a field is dropped, an
// enum literal drifts, or a property is invented, the fixture stops compiling.
// The runtime `expect`s additionally pin:
//   - the closed ChatProvider union ("pty" | "agy", ADR-003 — no free-form);
//   - parseChatScope's accept/reject behaviour (the three forms vs traversal);
//   - CF-07 conformance: BOTH a stub client funnel AND a stub server route
//     import the SAME shared types, so producer and consumer agree by
//     construction (two consumers of one source of truth).
//
// References:
// - .architecture/product-wide-chat/TDD.md §2.3 (the client↔server seam).
// - ADR-002 (chatScope keying), ADR-003 (provider on open), ADR-004 (chat→card).
// - CONTRACT_FIRST_STANDARD CF-05 (contract-first seam), CF-07 (conformance by
//   shared test), CF-09 (structured stream-event schema).

import { describe, it, expect } from "vitest";

import type {
  // The seam under contract (api-types.ts — the shared wire types).
  ChatScope,
  ChatProvider,
  ChatThreadResponse,
  ChatMessageRequest,
  ChatProviderRequest,
  ChatProviderResult,
  // SSE for POST /message is the EXISTING ChatStreamEvent (reused, not forked).
  ChatStreamEvent,
  // The reused transcript message union (ADR-002 — no new message shape).
  TranscriptMessage,
  // chat→card REUSES start-from-intent verbatim (ADR-004 — no new shape).
  StartFromIntentRequest,
} from "../../../shared/api-types";

import { parseChatScope } from "../../../shared/chatScope";

// The two CF-07 conformance consumers: a stub client funnel and a stub server
// route, each importing the SAME shared shapes. If producer and consumer ever
// disagree on the wire shape, one of these stops compiling.
import {
  stubChatClientFunnel,
  stubChatProviderRequest,
} from "../../../shared/chatScope.client.stub";
import { stubChatThreadRoute } from "../../../shared/chatScope.route.stub";

describe("chat-scope seam contract — the four routes' wire shapes", () => {
  // A real product id is colon-bearing (`dna:product:<ulid>`), so a real-product
  // scope is `product:dna:product:<ulid>`. The two synthetic scopes use the
  // bare sentinels behind the `product:` prefix (ADR-002).
  const realScope = "product:dna:product:01HZX9" as ChatScope;
  const allScope = "product:__all__" as ChatScope;
  const unassignedScope = "product:__unassigned__" as ChatScope;

  it("GET /thread → ChatThreadResponse pins exactly {messages, provider, productId}", () => {
    const userMsg: TranscriptMessage = {
      kind: "user",
      uuid: "u1",
      timestamp: "2026-06-25T00:00:00Z",
      text: "hello",
    };
    const response: ChatThreadResponse = {
      messages: [userMsg],
      provider: "pty",
      productId: "dna:product:01HZX9",
    };
    expect(Object.keys(response).sort()).toEqual([
      "messages",
      "productId",
      "provider",
    ]);
    // productId is null for the overview chat (product:__all__).
    const overview: ChatThreadResponse = {
      messages: [],
      provider: "agy",
      productId: null,
    };
    expect(overview.productId).toBeNull();
    expect(overview.messages).toEqual([]); // CF-04: empty case in the contract.
  });

  it("POST /message → request is {prompt}; SSE stream is the existing ChatStreamEvent", () => {
    const req: ChatMessageRequest = { prompt: "do the thing" };
    expect(Object.keys(req)).toEqual(["prompt"]);

    // The reply stream is the EXISTING ChatStreamEvent union: state|chunk*|
    // complete|error (CF-09, narrowed on `type`). Reusing it, not forking it.
    const events: ChatStreamEvent[] = [
      { type: "state", state: "ready" },
      { type: "chunk", text: "..." },
      { type: "complete", resumed: false },
    ];
    const states = events
      .filter((e): e is Extract<ChatStreamEvent, { type: "state" }> => e.type === "state")
      .map((e) => e.state);
    expect(states).toEqual(["ready"]);
  });

  it("PUT /provider → request {provider}; result {provider, applied:'new-work'} (AI-03)", () => {
    const req: ChatProviderRequest = { provider: "agy" };
    expect(Object.keys(req)).toEqual(["provider"]);

    const result: ChatProviderResult = { provider: "agy", applied: "new-work" };
    expect(Object.keys(result).sort()).toEqual(["applied", "provider"]);
    // AI-03: the choice applies to NEW work, never re-homes a live run.
    expect(result.applied).toBe("new-work");
  });

  it("ChatProvider is the closed union 'pty' | 'agy' (ADR-003 — no free-form)", () => {
    const providers: ChatProvider[] = ["pty", "agy"];
    expect(providers).toEqual(["pty", "agy"]);
    // pty = Claude, agy = Antigravity; the union is closed (compile-time pin).
  });

  it("chat→card REUSES StartFromIntentRequest verbatim (ADR-004 — no new shape)", () => {
    // The overview chat (product:__all__) must supply productId before propose.
    const propose: StartFromIntentRequest = {
      phase: "propose",
      productId: "dna:product:01HZX9",
      intent: "ship the cancel flow",
      kind: "change",
    };
    expect(propose.phase).toBe("propose");
    expect(propose.productId).toBe("dna:product:01HZX9");
  });
});

describe("parseChatScope — validator (rejects traversal, accepts the three forms)", () => {
  it("accepts product:{id} for a real (colon-bearing) product id", () => {
    const s = parseChatScope("product:dna:product:01HZX9");
    expect(s).toBe("product:dna:product:01HZX9");
  });

  it("accepts the product:__all__ overview sentinel", () => {
    expect(parseChatScope("product:__all__")).toBe("product:__all__");
  });

  it("accepts the reserved product:__unassigned__ sentinel", () => {
    expect(parseChatScope("product:__unassigned__")).toBe("product:__unassigned__");
  });

  it("rejects a path-traversal attempt in the id", () => {
    expect(parseChatScope("product:../../etc/passwd")).toBeNull();
    expect(parseChatScope("product:..")).toBeNull();
    expect(parseChatScope("product:a/b")).toBeNull();
  });

  it("rejects an embedded newline (no smuggling into a constructed path)", () => {
    expect(parseChatScope("product:abc\n")).toBeNull();
    expect(parseChatScope("product:a\nb")).toBeNull();
  });

  it("rejects a missing/empty id and a non-product prefix", () => {
    expect(parseChatScope("product:")).toBeNull();
    expect(parseChatScope("change:abc")).toBeNull();
    expect(parseChatScope("")).toBeNull();
    expect(parseChatScope("dna:product:01HZX9")).toBeNull(); // no product: prefix
  });
});

describe("CF-07 conformance — producer and consumer agree by shared type", () => {
  it("the stub client funnel and stub server route round-trip the same shape", () => {
    // The client funnel produces the request; the server route consumes it and
    // produces the response — both typed against the SAME shared shapes. This
    // is the conformance check: two consumers of one source of truth.
    const scope: ChatScope = "product:dna:product:01HZX9";
    const sent: ChatMessageRequest = stubChatClientFunnel(scope, "hello");
    expect(sent.prompt).toBe("hello");

    const served: ChatThreadResponse = stubChatThreadRoute(scope);
    expect(served.provider).toBe("pty");
    expect(served.productId).toBe("dna:product:01HZX9");
    // The overview scope resolves productId to null.
    expect(stubChatThreadRoute("product:__all__").productId).toBeNull();

    // The provider-PUT request funnel is the same shared shape, both sides.
    const switched: ChatProviderRequest = stubChatProviderRequest(scope, "agy");
    expect(switched.provider).toBe("agy");
  });
});
