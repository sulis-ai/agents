// CH-R5EE44 Fix 3 — change-scoped provider remember/resolve on
// LocalChatScopeStore.
//
// The per-change live session opens on a daemon/pty provider resolved at
// session-open (index.ts `resolveProvider(changeId)`). Until now that resolver
// was the hardcoded `() => "pty"` literal. This adds the change-scoped sibling of
// the per-product provider-remember (reuse-first: the SAME on-disk memory-record
// format the per-product `rememberProvider`/`resolveProvider` already write,
// under a `change/{changeId}/threads/chat.memory.json` root). It does NOT fork
// the `product:` chat-scope wire vocabulary — a change id is not a ChatScope, so
// the change-scoped path is its own pair of methods over the same substrate.
//
// Discipline: real temp chatRoot, real fs I/O, no mocks — same as the per-product
// localChatScopeStore.test.ts.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, rm, mkdir, writeFile, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { LocalChatScopeStore } from "../adapters/LocalChatScopeStore";

const CHANGE_ID = "01KW46HTT0R5EE449MT9NGWYNJ";

let chatRoot: string;
let store: LocalChatScopeStore;

beforeEach(async () => {
  chatRoot = await mkdtemp(join(tmpdir(), "ch-r5ee44-change-"));
  store = new LocalChatScopeStore({ chatRoot });
});

afterEach(async () => {
  await rm(chatRoot, { recursive: true, force: true });
});

describe("LocalChatScopeStore — change-scoped provider remember/resolve", () => {
  it("remembers the picked provider per change and reads it back", async () => {
    await store.rememberChangeProvider(CHANGE_ID, "agy");
    expect(await store.resolveChangeProvider(CHANGE_ID)).toBe("agy");
  });

  it("falls back to pty when nothing remembered for the change", async () => {
    expect(await store.resolveChangeProvider(CHANGE_ID)).toBe("pty");
  });

  it("ignores a corrupt remembered value and falls back to pty", async () => {
    const dir = join(chatRoot, "change", CHANGE_ID, "threads");
    await mkdir(dir, { recursive: true });
    await writeFile(
      join(dir, "chat.memory.json"),
      JSON.stringify({
        thread_id: "chat",
        version: 1,
        content: { participant_context: { provider: "gemini" } },
        created_at: "2026-06-27T00:00:00Z",
        updated_at: "2026-06-27T00:00:00Z",
      }),
      "utf8",
    );
    expect(await store.resolveChangeProvider(CHANGE_ID)).toBe("pty");
  });

  it("bumps the memory version monotonically across remembers (atomic write)", async () => {
    await store.rememberChangeProvider(CHANGE_ID, "agy");
    await store.rememberChangeProvider(CHANGE_ID, "pty");
    expect(await store.resolveChangeProvider(CHANGE_ID)).toBe("pty");
    const raw = await readFile(
      join(chatRoot, "change", CHANGE_ID, "threads", "chat.memory.json"),
      "utf8",
    );
    const record = JSON.parse(raw) as { version: number };
    expect(record.version).toBe(2);
  });

  it("keeps per-change provider memories physically separate", async () => {
    await store.rememberChangeProvider(CHANGE_ID, "agy");
    await store.rememberChangeProvider("OTHER_CHANGE", "pty");
    expect(await store.resolveChangeProvider(CHANGE_ID)).toBe("agy");
    expect(await store.resolveChangeProvider("OTHER_CHANGE")).toBe("pty");
  });

  it("rejects a hostile change id (path traversal) rather than escaping the root", async () => {
    await expect(
      store.rememberChangeProvider("../../etc", "agy"),
    ).rejects.toThrow();
  });
});
