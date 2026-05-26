// WP-009 — parse Claude Code session transcripts into TranscriptMessage[].
//
// Per WP-009 Contract "Parser" section + TDD §5.1 (TranscriptMessage
// shape) + TDD §13.6 (streaming line-by-line — no slurp) + ADR-004
// §Consequences (projection rules).
//
// For each file in `paths`, stream NDJSON line-by-line, parse each
// record, project content-bearing records into the wire-shape
// `TranscriptMessage`, then merge all messages across files and sort
// by timestamp ascending. Malformed lines are skipped silently
// (debug-level logging would belong here in a richer build).
//
// Projection rules:
//   - type: "user"       → { kind: "user", uuid, timestamp, text }
//   - type: "assistant"  → { kind: "assistant", uuid, timestamp, blocks }
//   - type: "system"     → { kind: "system", uuid, timestamp, subtype, text }
//   - type: "attachment" → suppressed (MVP doesn't render attachments)
//   - meta types         → skipped
//
// Streaming discipline (TDD §13.6): we use `readline` over a
// `createReadStream`. A 50 MB transcript stays at O(line-length)
// memory; only the parsed `TranscriptMessage` objects accumulate.

import { createReadStream } from "node:fs";
import { createInterface } from "node:readline";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type {
  AssistantBlock,
  TranscriptMessage,
} from "../../shared/api-types";

/**
 * Read each JSONL file in `paths`, project each content-bearing
 * record into a `TranscriptMessage`, then merge + sort by
 * `timestamp` ascending. Empty `paths` returns `[]`.
 *
 * Resilience: malformed lines, records missing required fields, and
 * unknown content shapes are skipped silently — never thrown — so a
 * single bad record never blocks an otherwise-readable transcript.
 */
export async function parseTranscripts(
  paths: string[],
): Promise<TranscriptMessage[]> {
  if (paths.length === 0) return [];

  const all: TranscriptMessage[] = [];
  for (const path of paths) {
    const fileMessages = await parseOneFile(path);
    all.push(...fileMessages);
  }
  all.sort((a, b) => (a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0));
  return all;
}

async function parseOneFile(path: string): Promise<TranscriptMessage[]> {
  const stream = createReadStream(path, { encoding: "utf8" });
  const lines = createInterface({ input: stream, crlfDelay: Infinity });

  const messages: TranscriptMessage[] = [];
  try {
    for await (const line of lines) {
      if (line.trim() === "") continue;

      let record: unknown;
      try {
        record = JSON.parse(line);
      } catch {
        continue; // malformed line — skip
      }

      const projected = projectRecord(record);
      if (projected !== null) {
        messages.push(projected);
      }
    }
  } finally {
    stream.destroy();
  }
  return messages;
}

/**
 * Project one raw JSONL record into a `TranscriptMessage`. Returns
 * `null` if the record is a meta type, an attachment (MVP suppresses
 * these), or is missing required fields.
 */
function projectRecord(record: unknown): TranscriptMessage | null {
  if (typeof record !== "object" || record === null) return null;
  const r = record as Record<string, unknown>;

  const type = r.type;
  if (typeof type !== "string") return null;

  // Required for every content-bearing kind.
  const uuid = typeof r.uuid === "string" ? r.uuid : null;
  const timestamp = typeof r.timestamp === "string" ? r.timestamp : null;

  if (type === "user") {
    if (uuid === null || timestamp === null) return null;
    return {
      kind: "user",
      uuid,
      timestamp,
      text: extractUserText(r.message),
    };
  }

  if (type === "assistant") {
    if (uuid === null || timestamp === null) return null;
    return {
      kind: "assistant",
      uuid,
      timestamp,
      blocks: extractAssistantBlocks(r.message),
    };
  }

  if (type === "system") {
    if (uuid === null || timestamp === null) return null;
    const subtype = typeof r.subtype === "string" ? r.subtype : "";
    const text = typeof r.content === "string" ? r.content : "";
    return { kind: "system", uuid, timestamp, subtype, text };
  }

  // attachment + meta types: suppressed.
  return null;
}

/**
 * Pull the text out of a user record's `message`. Claude Code emits
 * two shapes:
 *   - `{ role: "user", content: "<string>" }`
 *   - `{ role: "user", content: [{ type: "text", text: "..." }, ...] }`
 * Coalesce both to a single string.
 */
function extractUserText(message: unknown): string {
  if (typeof message !== "object" || message === null) return "";
  const content = (message as { content?: unknown }).content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((block) => {
        if (typeof block !== "object" || block === null) return "";
        const b = block as { type?: unknown; text?: unknown };
        return b.type === "text" && typeof b.text === "string" ? b.text : "";
      })
      .filter((s) => s !== "")
      .join("\n");
  }
  return "";
}

/**
 * Project an assistant record's `message.content[]` into the
 * `AssistantBlock[]` wire shape. Drops anything unrecognised.
 */
function extractAssistantBlocks(message: unknown): AssistantBlock[] {
  if (typeof message !== "object" || message === null) return [];
  const content = (message as { content?: unknown }).content;
  if (!Array.isArray(content)) return [];

  const blocks: AssistantBlock[] = [];
  for (const raw of content) {
    if (typeof raw !== "object" || raw === null) continue;
    const b = raw as Record<string, unknown>;
    const t = b.type;

    if (t === "text" && typeof b.text === "string") {
      blocks.push({ kind: "text", text: b.text });
      continue;
    }
    if (t === "tool_use" && typeof b.name === "string") {
      blocks.push({ kind: "tool-use", toolName: b.name, input: b.input });
      continue;
    }
    if (t === "tool_result" && typeof b.tool_use_id === "string") {
      blocks.push({
        kind: "tool-result",
        toolUseId: b.tool_use_id,
        content: b.content,
      });
      continue;
    }
    // Unknown block kind — drop it. The MVP renderer would have
    // nothing to do with it anyway.
  }
  return blocks;
}
