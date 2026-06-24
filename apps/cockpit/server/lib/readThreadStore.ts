// CH-GJ9KQR WP-006 — read the cockpit raw transcript view from OUR durable
// ThreadStore (WP-002) instead of Claude's provider transcript files.
//
// SUBSTITUTE-Strangle (data-source re-point): the durable store is the
// authoritative record the cockpit owns. It is the local-first LocalThreadStore
// (ADR-002 hybrid) — an append-only JSONL log on disk at
//
//   {sulisStateDir}/changes/{changeId}/threads/{changeId}.messages.jsonl
//
// one ThreadMessage per line, offset-ordered (the Python contract,
// `_session_manager/thread_contract.py` `store_root_for_change` +
// `messages_record_filename`). There is ONE thread per change (ADR-004), so the
// thread id is the change id — the same key the session-manager already uses.
//
// We read that log over the SAME local trust boundary as the brief + Working
// Set (loopback, single founder, OS file perms; ADR-002) and project each
// ThreadMessage onto the SAME wire-shape `TranscriptMessage[]` the UI already
// renders — so the raw view is behaviour-preserving (WP Contract: no visual
// change, same `TranscriptMessage[]`). The store's `ThreadMemory` is the rich
// view's source elsewhere; this is the raw message log.
//
// Dependency direction: this lib reads the durable bytes the Python store wrote
// (the on-disk contract is the seam, ADR-002 local binding) — it does not import
// or shell the Python store. When the hosted communication-service REST adapter
// lands (the future second adapter behind the same contract), this read moves
// behind that transport with no change to the projection.
//
// Discipline mirrors parseTranscripts: stream-tolerant line parsing, malformed
// lines skipped silently (a single bad record never blocks an otherwise-readable
// log).

import { readFile } from "node:fs/promises";
import { join } from "node:path";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { TranscriptMessage } from "../../shared/api-types";

/**
 * A ThreadMessage as the durable LocalThreadStore writes it to the JSONL log
 * (`dataclasses.asdict` of `thread_contract.ThreadMessage`). Mirrors the pinned
 * contract field-for-field; we read the fields the raw view needs.
 */
interface StoredThreadMessage {
  id: string;
  participant_id: string;
  participant_type: "studio_agent" | "user";
  content: string;
  role: "question" | "answer" | "observation" | "decision" | null;
  created_at: string;
  order: number;
}

/**
 * Safe-path-component guard, mirroring the store's convention
 * (`thread_contract.validate_store_id`): a change id is interpolated into a
 * filesystem path, so it MUST be a full-string match of `[A-Za-z0-9_-]+` — no
 * path separators, no `.`/`..`, no embedded newline. A traversing id is treated
 * as "no store" (returns `[]`) rather than building a path that escapes the
 * threads dir — the read-side twin of the store's write-side refusal.
 */
const SAFE_ID = /^[A-Za-z0-9_-]+$/;

/**
 * Read the durable thread message log for `changeId` from OUR store and project
 * it onto the `TranscriptMessage[]` wire shape. Returns `[]` when no log exists
 * for the change (the store has never been written for it — the strangle's
 * fallback signal) or when `changeId` is not a safe path component.
 *
 * The log is already offset-ordered on disk (append-only, monotonic `order`),
 * so the projection preserves order without re-sorting.
 */
export async function readThreadStore(
  sulisStateDir: string,
  changeId: string,
): Promise<TranscriptMessage[]> {
  if (!SAFE_ID.test(changeId)) return [];

  const logPath = join(
    sulisStateDir,
    "changes",
    changeId,
    "threads",
    `${changeId}.messages.jsonl`,
  );

  let raw: string;
  try {
    raw = await readFile(logPath, "utf8");
  } catch (err) {
    // No durable log for this change yet → empty (the strangle falls back to
    // the provider transcript). Any other read error is also degraded to empty
    // so the raw view never hard-fails on a store-read problem.
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
      continue; // malformed line — skip (mirrors parseTranscripts)
    }
    const projected = projectStoredMessage(record);
    if (projected !== null) messages.push(projected);
  }
  return messages;
}

/**
 * Project one stored ThreadMessage onto a `TranscriptMessage`. Returns `null`
 * for a record missing the required identity fields.
 *
 * Projection (vendor-neutral — no Claude-JSONL structure):
 *   - `uuid`      ← the message id (`{thread_id}-{order}`, stable + unique).
 *   - `timestamp` ← `created_at`.
 *   - `studio_agent` → an `assistant` message carrying its content as a single
 *     text block (the agent/tool record the raw view renders).
 *   - `user`         → a `user` message carrying its content as text.
 */
function projectStoredMessage(record: unknown): TranscriptMessage | null {
  if (typeof record !== "object" || record === null) return null;
  const r = record as Partial<StoredThreadMessage>;

  if (typeof r.id !== "string" || typeof r.created_at !== "string") return null;
  const content = typeof r.content === "string" ? r.content : "";

  if (r.participant_type === "user") {
    return { kind: "user", uuid: r.id, timestamp: r.created_at, text: content };
  }
  // Default (studio_agent and any other participant) renders as an assistant
  // record — the durable log is overwhelmingly agent/tool content.
  return {
    kind: "assistant",
    uuid: r.id,
    timestamp: r.created_at,
    blocks: [{ kind: "text", text: content }],
  };
}
