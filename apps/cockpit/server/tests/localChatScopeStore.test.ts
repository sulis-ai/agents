// WP-002 — LocalChatScopeStore adapter (ADR-002/003).
//
// Exercises the durable on-disk binding directly (a real temp chatRoot, no
// mocks): the provider remember/resolve round-trip, the GET /thread projection,
// productId resolution (real scope vs overview), and the message-log read.
// Mirrors the on-disk shape the Python `_session_manager.chat_scope_store`
// resolver writes, so the two sides agree by construction over the file contract.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { LocalChatScopeStore } from "../adapters/LocalChatScopeStore";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ChatScope } from "../../shared/api-types";

const REAL_SCOPE = "product:dna:product:01HZX9" as ChatScope;
const ALL_SCOPE = "product:__all__" as ChatScope;

let chatRoot: string;
let store: LocalChatScopeStore;

beforeEach(async () => {
  chatRoot = await mkdtemp(join(tmpdir(), "wp002-chat-"));
  store = new LocalChatScopeStore({ chatRoot });
});

afterEach(async () => {
  await rm(chatRoot, { recursive: true, force: true });
});

describe("LocalChatScopeStore — provider remember/resolve", () => {
  it("remembers the picked provider per scope and reads it back", async () => {
    await store.rememberProvider(REAL_SCOPE, "agy");
    expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("agy");
    const thread = await store.getThread(REAL_SCOPE);
    expect(thread.provider).toBe("agy");
  });

  it("picked provider wins over remembered (ADR-003 precedence)", async () => {
    await store.rememberProvider(REAL_SCOPE, "agy");
    expect(await store.resolveProvider(REAL_SCOPE, "pty")).toBe("pty");
  });

  it("falls back to pty when nothing picked or remembered", async () => {
    expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("pty");
  });

  it("ignores a corrupt remembered value and falls back to pty", async () => {
    // Write a memory record with a non-registered provider directly.
    const key = REAL_SCOPE.replace(/:/g, "_");
    const dir = join(chatRoot, key, "threads");
    await mkdir(dir, { recursive: true });
    await writeFile(
      join(dir, `${key}.memory.json`),
      JSON.stringify({
        thread_id: "chat",
        version: 1,
        content: { participant_context: { provider: "gemini" } },
        created_at: "2026-06-25T00:00:00Z",
        updated_at: "2026-06-25T00:00:00Z",
      }),
      "utf8",
    );
    expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("pty");
  });

  it("bumps the memory version monotonically across remembers", async () => {
    await store.rememberProvider(REAL_SCOPE, "agy");
    await store.rememberProvider(REAL_SCOPE, "pty");
    expect(await store.resolveProvider(REAL_SCOPE, null)).toBe("pty");
  });
});

describe("LocalChatScopeStore — getThread", () => {
  it("resolves productId from a real scope and null for the overview scope", async () => {
    expect((await store.getThread(REAL_SCOPE)).productId).toBe("dna:product:01HZX9");
    expect((await store.getThread(ALL_SCOPE)).productId).toBeNull();
  });

  it("projects the durable message log onto TranscriptMessage[]", async () => {
    const key = REAL_SCOPE.replace(/:/g, "_");
    const dir = join(chatRoot, key, "threads");
    await mkdir(dir, { recursive: true });
    const lines = [
      JSON.stringify({
        id: "m1",
        participant_type: "user",
        content: "hello",
        created_at: "2026-06-25T00:00:00Z",
      }),
      JSON.stringify({
        id: "m2",
        participant_type: "studio_agent",
        content: "hi back",
        created_at: "2026-06-25T00:00:01Z",
      }),
      "", // blank line tolerated
      "{not json", // malformed line skipped
    ].join("\n");
    await writeFile(join(dir, `${key}.messages.jsonl`), lines, "utf8");

    const thread = await store.getThread(REAL_SCOPE);
    expect(thread.messages).toHaveLength(2);
    expect(thread.messages[0]).toMatchObject({ kind: "user", text: "hello" });
    expect(thread.messages[1]).toMatchObject({ kind: "assistant" });
  });

  it("returns an empty transcript for a scope with no log yet", async () => {
    const thread = await store.getThread(REAL_SCOPE);
    expect(thread.messages).toEqual([]);
    expect(thread.provider).toBe("pty");
  });
});
