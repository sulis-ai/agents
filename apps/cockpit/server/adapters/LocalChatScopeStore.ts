// WP-002 — LocalChatScopeStore: the durable, local ChatScopeStore adapter
// (ADR-002, ADR-003).
//
// Binds the `ChatScopeStore` port to the SHIPPED Python store's ON-DISK
// contract — the same local binding `readThreadStore.ts` already uses for the
// raw transcript view. It does NOT shell the Python store; it reads/writes the
// durable bytes the Python `_session_manager.chat_scope_store` resolver lays
// down at the chat-scoped root:
//
//   {chatRoot}/{scope-key}/threads/{scope-key}.messages.jsonl   (append-only log)
//   {chatRoot}/{scope-key}/threads/{scope-key}.memory.json      (provider stamp)
//
// where `chatRoot` defaults to `~/.sulis/chat` and `scope-key` is the wire scope
// with each `:` mapped to `_` (the Python `_scope_key` derivation, mirrored).
// When the hosted communication-service REST adapter lands (the future second
// adapter behind the same port), this read/write moves behind that transport
// with no change to the routes.
//
// The provider stamp is the ONE write this adapter performs (PUT /provider).
// It is a checkpoint write of `participant_context.provider` onto the scope's
// memory record — monotonic `version`, mirroring the Python `put_memory`
// invariant — done with the same atomic temp-then-rename the Python store uses,
// so a reader never observes a half-written record.

import { readFile, writeFile, rename, mkdir } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import type {
  ChatProvider,
  ChatScope,
  ChatThreadResponse,
  TranscriptMessage,
} from "../../shared/api-types";
import type { ChatScopeStore } from "../ports/ChatScopeStore";
import { projectStoredMessage } from "../lib/projectStoredMessage";

const SCOPE_PREFIX = "product:";
const REGISTERED_PROVIDERS: readonly ChatProvider[] = ["pty", "agy"];
const DEFAULT_PROVIDER: ChatProvider = "pty";
// One thread per scope (ADR-002); the thread id within a scope is "chat".
const THREAD_ID = "chat";
// Safe path component, mirroring the Python `validate_store_id` guard.
const SAFE_KEY = /^[A-Za-z0-9_-]+$/;

interface StoredMemory {
  thread_id: string;
  version: number;
  content: {
    participant_context?: Record<string, unknown>;
    [k: string]: unknown;
  };
  created_at: string;
  updated_at: string;
}

/**
 * Derive the `validate_store_id`-safe on-disk key from a wire scope — the
 * mirror of the Python `_scope_key` (each `:` → `_`). Throws on a hostile scope
 * (the routes already validate via `parseChatScope`, so this is the adapter's
 * own backstop, never the user-facing failure).
 */
function scopeKey(scope: ChatScope): string {
  if (!scope.startsWith(SCOPE_PREFIX)) {
    throw new Error(`chat scope ${scope} missing the product: prefix`);
  }
  const body = scope.slice(SCOPE_PREFIX.length);
  if (body === "" || body.includes("/") || body.includes("\\") || body.includes(".")) {
    throw new Error(`chat scope ${scope} is not a safe path component`);
  }
  const key = scope.replace(/:/g, "_");
  if (!SAFE_KEY.test(key)) {
    throw new Error(`derived chat scope key ${key} is not a safe path component`);
  }
  return key;
}

export interface LocalChatScopeStoreOptions {
  /** The chat-store root; defaults to `~/.sulis/chat` (the loopback boundary). */
  chatRoot?: string;
}

/** The durable, local ChatScopeStore (ADR-002). */
export class LocalChatScopeStore implements ChatScopeStore {
  private readonly chatRoot: string;

  constructor(opts: LocalChatScopeStoreOptions = {}) {
    this.chatRoot = opts.chatRoot ?? join(homedir(), ".sulis", "chat");
  }

  private threadsDir(scope: ChatScope): string {
    return join(this.chatRoot, scopeKey(scope), "threads");
  }

  private messagesPath(scope: ChatScope): string {
    return join(this.threadsDir(scope), `${scopeKey(scope)}.messages.jsonl`);
  }

  private memoryPath(scope: ChatScope): string {
    return join(this.threadsDir(scope), `${scopeKey(scope)}.memory.json`);
  }

  async getThread(scope: ChatScope): Promise<ChatThreadResponse> {
    const messages = await this.readMessages(scope);
    const remembered = await this.readRememberedProvider(scope);
    const provider =
      remembered && REGISTERED_PROVIDERS.includes(remembered)
        ? remembered
        : DEFAULT_PROVIDER;
    const productId =
      scope === `${SCOPE_PREFIX}__all__`
        ? null
        : scope.slice(SCOPE_PREFIX.length);
    return { messages, provider, productId };
  }

  async rememberProvider(scope: ChatScope, provider: ChatProvider): Promise<void> {
    const path = this.memoryPath(scope);
    let existing: StoredMemory | null = null;
    try {
      existing = JSON.parse(await readFile(path, "utf8")) as StoredMemory;
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    }
    const version = (existing?.version ?? 0) + 1;
    const context = { ...(existing?.content.participant_context ?? {}), provider };
    const now = new Date().toISOString();
    const record: StoredMemory = {
      thread_id: THREAD_ID,
      version,
      content: {
        ...(existing?.content ?? {}),
        participant_context: context,
      },
      created_at: existing?.created_at ?? now,
      updated_at: now,
    };
    await mkdir(this.threadsDir(scope), { recursive: true });
    // Atomic temp-then-rename (mirrors the Python store's `_write_json`).
    const tmp = `${path}.tmp`;
    await writeFile(tmp, JSON.stringify(record), "utf8");
    await rename(tmp, path);
  }

  async resolveProvider(
    scope: ChatScope,
    picked: ChatProvider | null,
  ): Promise<ChatProvider> {
    if (picked && REGISTERED_PROVIDERS.includes(picked)) return picked;
    const remembered = await this.readRememberedProvider(scope);
    if (remembered && REGISTERED_PROVIDERS.includes(remembered)) return remembered;
    return DEFAULT_PROVIDER;
  }

  private async readRememberedProvider(
    scope: ChatScope,
  ): Promise<ChatProvider | null> {
    try {
      const memory = JSON.parse(
        await readFile(this.memoryPath(scope), "utf8"),
      ) as StoredMemory;
      const value = memory.content.participant_context?.["provider"];
      return typeof value === "string" ? (value as ChatProvider) : null;
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
      return null;
    }
  }

  private async readMessages(scope: ChatScope): Promise<TranscriptMessage[]> {
    let raw: string;
    try {
      raw = await readFile(this.messagesPath(scope), "utf8");
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
      return [];
    }
    const messages: TranscriptMessage[] = [];
    for (const line of raw.split("\n")) {
      if (line.trim() === "") continue;
      let record: unknown;
      try {
        record = JSON.parse(line);
      } catch {
        continue;
      }
      const projected = projectStoredMessage(record);
      if (projected !== null) messages.push(projected);
    }
    return messages;
  }
}
