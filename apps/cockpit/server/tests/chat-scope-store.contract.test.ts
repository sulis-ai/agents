// WP-002 — Contract test for the ChatScopeStore port (TDD §2.2; ADR-002/003).
//
// One reusable `runChatScopeStoreContract` suite both implementations satisfy:
//   - the production `LocalChatScopeStore` (on a temp chat root);
//   - the in-memory fake the route tests use.
// Same assertions, two implementations — the boundary-parity guarantee the
// other cockpit ports already have (session-bridge / change-store-reader /
// SettingsStore each ship a shared contract test). Without this, the route's
// fake and the production adapter can drift on the fallback order, productId
// resolution, or the remember/resolve round-trip — and only the fake is what
// the route tests see (the gap the code-review caught).
//
// The factory is asymmetric on purpose: each implementation prepares its own
// world (the adapter a temp dir; the fake a pair of maps) without leaking the
// shape into the contract.

import { describe, it, expect, afterEach } from "vitest";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { LocalChatScopeStore } from "../adapters/LocalChatScopeStore";
import type { ChatScopeStore } from "../ports/ChatScopeStore";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ChatProvider, ChatScope } from "../../shared/api-types";

const REAL_SCOPE = "product:dna:product:01HZX9" as ChatScope;
const OTHER_SCOPE = "product:dna:product:01HZY0" as ChatScope;
const ALL_SCOPE = "product:__all__" as ChatScope;

/** The text content of a TranscriptMessage, regardless of kind (user text or
 *  the assistant's first text block). `undefined` for an absent message. */
function messageText(
  msg: import("../../shared/api-types").TranscriptMessage | undefined,
): string {
  if (msg === undefined) return "";
  if (msg.kind === "user") return msg.text;
  if (msg.kind === "assistant") {
    const block = msg.blocks[0];
    return block && block.kind === "text" ? block.text : "";
  }
  return ""; // system message — not produced by appendTurn
}

/** A factory builds a fresh, isolated store and returns a teardown. */
type Factory = () => Promise<{ store: ChatScopeStore; cleanup: () => Promise<void> }>;

/** The in-memory fake — the same shape the route tests inject. */
function fakeFactory(): ReturnType<Factory> {
  const remembered = new Map<string, ChatProvider>();
  const turns = new Map<string, { kind: "user" | "assistant"; text: string }[]>();
  const REGISTERED: ChatProvider[] = ["pty", "agy"];
  const store: ChatScopeStore = {
    async getThread(scope) {
      const log = turns.get(scope) ?? [];
      return {
        messages: log.map((t, i) =>
          t.kind === "user"
            ? {
                kind: "user" as const,
                uuid: `${scope}-${i}`,
                timestamp: "",
                text: t.text,
              }
            : {
                kind: "assistant" as const,
                uuid: `${scope}-${i}`,
                timestamp: "",
                blocks: [{ kind: "text" as const, text: t.text }],
              },
        ),
        provider: remembered.get(scope) ?? "pty",
        productId: scope === ALL_SCOPE ? null : scope.slice("product:".length),
      };
    },
    async appendTurn(scope, role, content) {
      // The fake mirrors the redacting path's externally-visible contract — a
      // secret-shaped token is replaced before it is stored — so the route
      // tests inherit the same redaction guarantee the durable adapter gives.
      // (The token shapes mirror the Python catalogue's GitHub-PAT + OpenAI
      // forms so the fake and the real adapter agree on what gets scrubbed.)
      const redacted = content.replace(
        /\b(?:ghp_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{40,})\b/g,
        "[redacted-secret]",
      );
      const log = turns.get(scope) ?? [];
      log.push({ kind: role === "user" ? "user" : "assistant", text: redacted });
      turns.set(scope, log);
    },
    async groundCwd(scope) {
      // The fake returns a deterministic, scope-keyed path (no real dir created);
      // the durable adapter returns the scope's real, existing chat-store dir.
      return `/fake/chat/${scope.replace(/:/g, "_")}`;
    },
    async rememberProvider(scope, provider) {
      remembered.set(scope, provider);
    },
    async resolveProvider(scope, picked) {
      if (picked && REGISTERED.includes(picked)) return picked;
      const r = remembered.get(scope);
      if (r && REGISTERED.includes(r)) return r;
      return "pty";
    },
    async rememberChangeProvider(changeId, provider) {
      remembered.set(`change:${changeId}`, provider);
    },
    async resolveChangeProvider(changeId) {
      const r = remembered.get(`change:${changeId}`);
      if (r && REGISTERED.includes(r)) return r;
      return "pty";
    },
  };
  return Promise.resolve({ store, cleanup: async () => {} });
}

/** The production adapter on a temp chat root. */
async function adapterFactory(): ReturnType<Factory> {
  const chatRoot = await mkdtemp(join(tmpdir(), "wp002-contract-"));
  return {
    store: new LocalChatScopeStore({ chatRoot }),
    cleanup: () => rm(chatRoot, { recursive: true, force: true }),
  };
}

export function runChatScopeStoreContract(name: string, factory: Factory): void {
  describe(`ChatScopeStore contract — ${name}`, () => {
    let cleanup: () => Promise<void> = async () => {};
    afterEach(() => cleanup());

    async function make(): Promise<ChatScopeStore> {
      const built = await factory();
      cleanup = built.cleanup;
      return built.store;
    }

    it("resolveProvider: picked wins over remembered (ADR-003 precedence)", async () => {
      const store = await make();
      await store.rememberProvider(REAL_SCOPE, "agy");
      expect(await store.resolveProvider(REAL_SCOPE, "pty")).toBe("pty");
    });

    it("resolveProvider: remembered used when nothing picked", async () => {
      const store = await make();
      await store.rememberProvider(REAL_SCOPE, "agy");
      expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("agy");
    });

    it("resolveProvider: pty default when nothing picked or remembered", async () => {
      const store = await make();
      expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("pty");
    });

    it("rememberProvider: persists per scope, isolated across scopes", async () => {
      const store = await make();
      await store.rememberProvider(REAL_SCOPE, "agy");
      await store.rememberProvider(OTHER_SCOPE, "pty");
      expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("agy");
      expect(await store.resolveProvider(OTHER_SCOPE, null)).toBe("pty");
    });

    it("getThread: productId resolves from a real scope and is null for the overview", async () => {
      const store = await make();
      expect((await store.getThread(REAL_SCOPE)).productId).toBe(
        "dna:product:01HZX9",
      );
      expect((await store.getThread(ALL_SCOPE)).productId).toBeNull();
    });

    it("getThread: reflects the remembered provider", async () => {
      const store = await make();
      await store.rememberProvider(REAL_SCOPE, "agy");
      expect((await store.getThread(REAL_SCOPE)).provider).toBe("agy");
    });

    // ── WP-004 seam-close: the persistence round-trip (DAT-PERSIST-01) ──────
    // Today nothing appends chat turns at runtime, so getThread is always empty
    // and per-product history is not real. appendTurn closes the round-trip:
    // each turn is persisted through the REDACTING store path and read back by
    // getThread, in order, isolated per scope.

    it("appendTurn: a user then an assistant turn round-trip through getThread, in order", async () => {
      const store = await make();
      await store.appendTurn(REAL_SCOPE, "user", "what changed today?");
      await store.appendTurn(REAL_SCOPE, "assistant", "three changes shipped");
      const { messages } = await store.getThread(REAL_SCOPE);
      expect(messages.map((m) => m.kind)).toEqual(["user", "assistant"]);
      expect(messageText(messages[0])).toBe("what changed today?");
      expect(messageText(messages[1])).toBe("three changes shipped");
    });

    it("appendTurn: history is isolated per scope — switching never blends", async () => {
      const store = await make();
      await store.appendTurn(REAL_SCOPE, "user", "hello from A");
      await store.appendTurn(OTHER_SCOPE, "user", "hello from B");
      const a = (await store.getThread(REAL_SCOPE)).messages;
      const b = (await store.getThread(OTHER_SCOPE)).messages;
      expect(a).toHaveLength(1);
      expect(b).toHaveLength(1);
      expect(messageText(a[0])).toBe("hello from A");
      expect(messageText(b[0])).toBe("hello from B");
    });

    it("appendTurn: chat content is redacted on write (the REDACTING store path)", async () => {
      const store = await make();
      // A GitHub-PAT-shaped token the Python secret catalogue detects (the
      // REDACTING path proves it for real; the fake mirrors the same shape).
      const secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789AB";
      await store.appendTurn(REAL_SCOPE, "user", `my key is ${secret} keep it`);
      const text = messageText((await store.getThread(REAL_SCOPE)).messages[0]);
      expect(text).not.toContain(secret);
      expect(text).toContain("[redacted-secret]");
    });

    // ── WP-004 seam-close: ground the relay cwd (folded ADV-CWD-01) ────────
    // The chat session's cwd must resolve to a REAL directory for the scope
    // (today the change resolver returns null → cwd:''). groundCwd returns the
    // scope's real, existing chat-store directory so the relay runs in a real
    // place keyed to the scope (histories physically separate, ADR-002).

    it("groundCwd: returns a real, scope-keyed, non-empty directory path", async () => {
      const store = await make();
      const cwd = await store.groundCwd(REAL_SCOPE);
      expect(cwd).not.toBe("");
      // Distinct scopes ground to distinct dirs (never share a cwd → never blend).
      const other = await store.groundCwd(OTHER_SCOPE);
      expect(cwd).not.toBe(other);
    });
  });
}

runChatScopeStoreContract("LocalChatScopeStore (durable)", adapterFactory);
runChatScopeStoreContract("in-memory fake", fakeFactory);
