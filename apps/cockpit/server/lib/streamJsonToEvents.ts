// WP-005 — stream-json → ChatStreamEvent mapping (ADR-001/002).
//
// Both SessionBridge adapters consume the SAME headless `claude -p
// --output-format stream-json --include-partial-messages` line shapes — the
// recorded fixture replays them, the prod adapter reads them off the child's
// stdout. The mapping from one stream-json record to zero-or-one
// ChatStreamEvent is therefore extracted here once (EP-03: 2-consumer
// threshold reached at authoring time — recorded + prod), rather than
// duplicated in each adapter.
//
// The mapping (TDD §3.1, ADR-001):
//   system/init                        → state ("ready" | "resuming" | "spawning")
//   stream_event (content_block_delta) → chunk { text }
//   result/success                     → complete { resumed }
//   result/error | is_error            → (caller emits error; see adapters)
//
// `resumed` is decided by the RESOLUTION, never synthesised from the stream
// (FR-N5): a resumable/mid-step resolution yields resumed=true; live/fresh
// yields false. The adapter passes the resolution kind in.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { ChatStreamEvent } from "../../shared/api-types";
import type { SessionResolution } from "../ports/SessionBridge";

/** One parsed stream-json record (the subset the cockpit reads). */
export interface StreamJsonRecord {
  type?: string;
  subtype?: string;
  resumed?: boolean;
  is_error?: boolean;
  event?: {
    type?: string;
    delta?: { text?: string };
  };
}

/** The leading lifecycle state for a resolution (FR-23, honest about resume). */
export function leadingStateFor(
  kind: SessionResolution["kind"],
): Extract<ChatStreamEvent, { type: "state" }>["state"] {
  if (kind === "resumable") return "resuming";
  if (kind === "fresh") return "spawning";
  return "replying";
}

/** True when the resolution means the founder is honestly told it resumed (FR-26). */
export function resumedFor(kind: SessionResolution["kind"]): boolean {
  return kind === "resumable";
}

/**
 * Map one stream-json record to zero-or-one ChatStreamEvent. `init` records
 * are swallowed here (the adapter emits the leading `state` itself from the
 * resolution, so the state is honest about resume/spawn rather than guessed
 * from the stream). Returns `null` for records that carry no founder-facing
 * event (e.g. tool-use bookkeeping).
 */
export function streamJsonToEvent(
  record: StreamJsonRecord,
  resolutionKind: SessionResolution["kind"],
): ChatStreamEvent | null {
  if (record.type === "stream_event") {
    const text = record.event?.delta?.text;
    if (typeof text === "string" && text.length > 0) {
      return { type: "chunk", text };
    }
    return null;
  }
  if (record.type === "result") {
    if (record.subtype === "success" && !record.is_error) {
      return { type: "complete", resumed: resumedFor(resolutionKind) };
    }
    // An error result is handled by the adapter (it owns the typed code).
    return null;
  }
  // system/init and anything else carry no founder-facing chunk/complete.
  return null;
}

/** Parse one NDJSON line into a record, or null if it isn't valid JSON. */
export function parseStreamJsonLine(line: string): StreamJsonRecord | null {
  const trimmed = line.trim();
  if (trimmed === "") return null;
  try {
    return JSON.parse(trimmed) as StreamJsonRecord;
  } catch {
    return null;
  }
}
