// WP-002/WP-004 — LocalChatScopeStore: the durable, local ChatScopeStore
// adapter (ADR-002, ADR-003; WP-004 closes the persistence round-trip +
// cwd grounding — folded CONCERN DAT-PERSIST-01 / ADV-CWD-01).
//
// Binds the `ChatScopeStore` port to the SHIPPED Python store's ON-DISK
// contract. It reads the durable bytes the Python
// `_session_manager.chat_scope_store` resolver (over `LocalThreadStore`) lays
// down at the chat-scoped root, and keys the record FILENAMES by the THREAD id
// ("chat") — exactly as the Python `LocalThreadStore` does:
//
//   {chatRoot}/{scope-key}/threads/chat.messages.jsonl   (append-only turn log)
//   {chatRoot}/{scope-key}/threads/chat.memory.json       (provider stamp)
//
// where `chatRoot` defaults to `~/.sulis/chat` and `scope-key` is the wire scope
// with each `:` mapped to `_` (the Python `_scope_key` derivation, mirrored).
// When the hosted communication-service REST adapter lands (the future second
// adapter behind the same port), this read/write moves behind that transport
// with no change to the routes.
//
// This adapter performs THREE writes:
//   - `rememberProvider` (PUT /provider) — a checkpoint write of
//     `participant_context.provider` onto the scope's memory record (monotonic
//     `version`, atomic temp-then-rename, mirroring the Python `put_memory`).
//   - `appendTurn` (WP-004) — persists one chat turn through the Python
//     REDACTING store path by shelling the vendored `sulis-chat-append` CLI
//     (so the secret catalogue stays single-source; the cockpit never
//     re-implements redaction in TS). This is the ONE place the adapter starts
//     a process — allow-listed in the read-only gate as a sanctioned WRITE seam.
//   - `groundCwd` (WP-004) — ensures the scope's threads dir exists and returns
//     it, so the chat relay runs in a real, scope-keyed cwd (never `""`).

import { execFile } from "node:child_process";
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
import { resolvePluginScriptsDir } from "./resolvePluginScripts";

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

  // The durable record filenames are keyed by the THREAD id ("chat"), matching
  // the Python `LocalThreadStore` exactly (`{thread_id}.messages.jsonl` /
  // `{thread_id}.memory.json`) — the store the WP-004 append path writes
  // through. (WP-002 keyed these by the scope key; that disagreed with the
  // Python writer, so the round-trip read the wrong file. Aligned here as part
  // of closing the seam — DAT-PERSIST-01.)
  private messagesPath(scope: ChatScope): string {
    return join(this.threadsDir(scope), `${THREAD_ID}.messages.jsonl`);
  }

  async getThread(scope: ChatScope): Promise<ChatThreadResponse> {
    const messages = await this.readMessages(scope);
    const remembered = await this.readMemoryProvider(this.threadsDir(scope));
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

  async appendTurn(
    scope: ChatScope,
    role: "user" | "assistant",
    content: string,
  ): Promise<void> {
    // Persist through the Python REDACTING store path (the shipped
    // `LocalThreadStore.append_message` → secret-scrub). The cockpit NEVER
    // re-implements redaction in TS — the secret catalogue stays single-source
    // (EP-03). The vendored `sulis-chat-append` CLI is the one append seam; the
    // turn content goes over STDIN so a secret never lands in argv.
    const script = resolveChatAppendScript();
    if (script === "") {
      throw new Error("sulis-chat-append not found (cannot persist the chat turn)");
    }
    // `scopeKey` is the adapter's own backstop (the routes already validated via
    // parseChatScope); it throws on a hostile scope before any shell-out.
    scopeKey(scope);
    await new Promise<void>((resolve, reject) => {
      const child = execFile(
        "python3",
        [
          script,
          "--scope",
          scope,
          "--role",
          role,
          "--chat-root",
          this.chatRoot,
        ],
        { shell: false, env: { ...process.env } },
        (error, _stdout, stderr) => {
          if (error) {
            reject(
              new Error(
                `chat turn append failed: ${stderr?.trim() || String(error)}`,
              ),
            );
            return;
          }
          resolve();
        },
      );
      child.stdin?.end(content);
    });
  }

  async groundCwd(scope: ChatScope): Promise<string> {
    // The real directory the scope's chat session runs in (ADV-CWD-01). Ensure
    // the scope's chat-store threads dir exists and hand it back, so the relay
    // runs in a real, scope-keyed place — never the server's own dir (the prior
    // `resolveChange(scope) === null → cwd:""`). Distinct scopes → distinct
    // dirs (histories physically separate, ADR-002).
    const dir = this.threadsDir(scope);
    await mkdir(dir, { recursive: true });
    return dir;
  }

  async rememberProvider(scope: ChatScope, provider: ChatProvider): Promise<void> {
    await this.writeMemoryProvider(this.threadsDir(scope), provider);
  }

  async resolveProvider(
    scope: ChatScope,
    picked: ChatProvider | null,
  ): Promise<ChatProvider> {
    if (picked && REGISTERED_PROVIDERS.includes(picked)) return picked;
    const remembered = await this.readMemoryProvider(this.threadsDir(scope));
    if (remembered && REGISTERED_PROVIDERS.includes(remembered)) return remembered;
    return DEFAULT_PROVIDER;
  }

  // ── Change-scoped provider remember/resolve (CH-R5EE44 Fix 3) ──────────────
  //
  // The per-change live terminal opens on a daemon/pty provider resolved at
  // session-open (index.ts `resolveProvider(changeId)`, previously the hardcoded
  // `() => "pty"` literal). The per-change picker persists its choice HERE,
  // reusing the SAME on-disk memory-record substrate as the per-product
  // remember (`writeMemoryProvider`/`readMemoryProvider`) — only the root
  // differs: `{chatRoot}/change/{changeId}/threads/chat.memory.json`. A change id
  // is NOT a `ChatScope` (the `product:` wire vocabulary is unchanged — no fork),
  // so the change path is its own pair of methods over the shared writer.

  /** Remember the per-change provider choice (AI-03: applies to the next open). */
  async rememberChangeProvider(
    changeId: string,
    provider: ChatProvider,
  ): Promise<void> {
    await this.writeMemoryProvider(this.changeThreadsDir(changeId), provider);
  }

  /** Resolve which provider to OPEN the change's session on: the remembered
   *  choice if registered, else the safe default `pty` (ADR-003 order, minus the
   *  per-call `picked` — the change picker persists via `rememberChangeProvider`
   *  then the daemon path resolves the remembered value at open). */
  async resolveChangeProvider(changeId: string): Promise<ChatProvider> {
    const remembered = await this.readMemoryProvider(
      this.changeThreadsDir(changeId),
    );
    if (remembered && REGISTERED_PROVIDERS.includes(remembered)) return remembered;
    return DEFAULT_PROVIDER;
  }

  /** The change's memory-record dir, under a `change/` root distinct from the
   *  per-product scope roots. `changeId` must be a safe single path component
   *  (the same `validate_store_id` posture as the scope key) — a hostile id is
   *  rejected before any fs touch rather than escaping the chat root. */
  private changeThreadsDir(changeId: string): string {
    if (
      changeId === "" ||
      changeId.includes("/") ||
      changeId.includes("\\") ||
      changeId.includes("..") ||
      !SAFE_KEY.test(changeId)
    ) {
      throw new Error(`change id ${changeId} is not a safe path component`);
    }
    return join(this.chatRoot, "change", changeId, "threads");
  }

  /**
   * Checkpoint-write the provider stamp onto the memory record at
   * `{memoryDir}/chat.memory.json` (monotonic `version`, atomic temp-then-rename,
   * mirroring the Python `put_memory`). Shared by the per-product + per-change
   * remember paths (EP-03, extracted at the 2-consumer threshold).
   */
  private async writeMemoryProvider(
    memoryDir: string,
    provider: ChatProvider,
  ): Promise<void> {
    const path = join(memoryDir, `${THREAD_ID}.memory.json`);
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
    await mkdir(memoryDir, { recursive: true });
    // Atomic temp-then-rename (mirrors the Python store's `_write_json`).
    const tmp = `${path}.tmp`;
    await writeFile(tmp, JSON.stringify(record), "utf8");
    await rename(tmp, path);
  }

  /** Read the remembered provider stamp from `{memoryDir}/chat.memory.json`, or
   *  `null` when absent/unreadable. Shared by the per-product + per-change resolve
   *  paths (EP-03). */
  private async readMemoryProvider(
    memoryDir: string,
  ): Promise<ChatProvider | null> {
    try {
      const memory = JSON.parse(
        await readFile(join(memoryDir, `${THREAD_ID}.memory.json`), "utf8"),
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

/**
 * Resolve the absolute `sulis-chat-append` script path — the vendored Python
 * entrypoint the per-product chat round-trip persists through (the REDACTING
 * store path). Delegates the env-override → in-repo → latest-plugin-cache search
 * to the shared `resolvePluginScriptsDir` (the same primitive the change-start
 * + emitter adapters use), then joins the script onto the resolved dir. Honours
 * `SULIS_CHAT_APPEND_SCRIPT` (which may name the scripts dir OR the script
 * file). Returns "" when unresolved.
 */
export function resolveChatAppendScript(): string {
  const dir = resolvePluginScriptsDir({
    scriptName: "sulis-chat-append",
    envOverride: process.env.SULIS_CHAT_APPEND_SCRIPT,
  });
  if (dir === "") return "";
  return join(dir, "sulis-chat-append");
}
