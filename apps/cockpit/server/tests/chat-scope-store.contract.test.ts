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

/** A factory builds a fresh, isolated store and returns a teardown. */
type Factory = () => Promise<{ store: ChatScopeStore; cleanup: () => Promise<void> }>;

/** The in-memory fake — the same shape the route tests inject. */
function fakeFactory(): ReturnType<Factory> {
  const remembered = new Map<string, ChatProvider>();
  const REGISTERED: ChatProvider[] = ["pty", "agy"];
  const store: ChatScopeStore = {
    async getThread(scope) {
      return {
        messages: [],
        provider: remembered.get(scope) ?? "pty",
        productId: scope === ALL_SCOPE ? null : scope.slice("product:".length),
      };
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
  });
}

runChatScopeStoreContract("LocalChatScopeStore (durable)", adapterFactory);
runChatScopeStoreContract("in-memory fake", fakeFactory);
