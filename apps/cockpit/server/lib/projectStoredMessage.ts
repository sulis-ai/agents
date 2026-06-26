// WP-002 (BLUE/EP-03) — the shared durable-message → wire projection.
//
// Extracted at the 2-consumer threshold (EP-03): the change-scoped raw view
// (`readThreadStore.ts`) and the per-product chat store (`LocalChatScopeStore.ts`)
// both read the durable LocalThreadStore JSONL log and project each stored
// `ThreadMessage` onto the SAME `TranscriptMessage` wire shape. The projection
// is the on-disk contract's read side (vendor-neutral — no Claude-JSONL
// structure), so it lives once.
//
// Projection:
//   - `uuid`/`timestamp` ← the message id + `created_at`.
//   - `user`         → a `user` message carrying its content as text.
//   - `studio_agent` (and any other participant) → an `assistant` message
//     carrying its content as a single text block (the durable log is
//     overwhelmingly agent/tool content).
// Returns `null` for a record missing the required identity fields (the caller
// skips it — a single bad record never blocks an otherwise-readable log).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import type { TranscriptMessage } from "../../shared/api-types";

/**
 * A ThreadMessage as the durable LocalThreadStore writes it to the JSONL log
 * (`dataclasses.asdict` of `thread_contract.ThreadMessage`). We read only the
 * fields the wire projection needs.
 */
export interface StoredThreadMessage {
  id: string;
  participant_type: "studio_agent" | "user";
  content: string;
  created_at: string;
}

/** Project one stored ThreadMessage onto a `TranscriptMessage`, or `null` for a
 *  record missing the required identity fields. */
export function projectStoredMessage(record: unknown): TranscriptMessage | null {
  if (typeof record !== "object" || record === null) return null;
  const r = record as Partial<StoredThreadMessage>;
  if (typeof r.id !== "string" || typeof r.created_at !== "string") return null;
  const content = typeof r.content === "string" ? r.content : "";
  if (r.participant_type === "user") {
    return { kind: "user", uuid: r.id, timestamp: r.created_at, text: content };
  }
  return {
    kind: "assistant",
    uuid: r.id,
    timestamp: r.created_at,
    blocks: [{ kind: "text", text: content }],
  };
}
