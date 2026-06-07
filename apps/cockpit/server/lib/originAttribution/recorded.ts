// WP-P13 — pure parsers for a RECORDED origin (ADR-013).
//
// The recorded origin is stamped (WP-P12) as a `Sulis-Origin:` commit trailer,
// with a `.sulis/origin/<sha>.json` sidecar fallback. This module maps EITHER
// source to the cockpit's `Origin` shape with `attribution: "recorded"`. It is
// PURE (no I/O) so it is testable in isolation and shared by both:
//   - `correlate` (the inferred path's recorded short-circuit — a stamped commit
//     read through inference still reports the truth), and
//   - `RecordedOriginAttribution` (the recorded adapter, WP-P13).
//
// Extracting it here is the EP-03 shared-primitive move: the trailer-shape parse
// lived inline in `correlate.ts`; both readers now share one parser, so the
// inferred and recorded paths can never drift on how a stamp is read.
//
// Shape (CF-11):
//   Sulis-Origin: autonomous; run=<ulid>; confidence=<0..1>
//   Sulis-Origin: assisted; conversation=<id>; turn=<n>

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { Origin } from "../../../shared/api-types";

/** The trailer key the write paths stamp — the same family as Co-Authored-By. */
export const ORIGIN_TRAILER_KEY = "Sulis-Origin";

/**
 * True if `value` carries any control character (newline, carriage return, tab,
 * NUL, etc.). A trailer is a single line; a control char in the value is either
 * malformed input or a trailer-injection attempt (a smuggled `\n` +
 * `Forged-Trailer:` line). The mirror of the Python writer's guard
 * (`_origin_stamp._has_control_char`): such a value is treated as no/unknown
 * origin rather than parsed into a forged result.
 */
function hasControlChar(value: string): boolean {
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    if (code < 0x20 || code === 0x7f) return true;
  }
  return false;
}

/** Pull the `Sulis-Origin:` trailer VALUE from a full commit message, or null. */
export function trailerValueFromMessage(message: string): string | null {
  const re = new RegExp(`^${ORIGIN_TRAILER_KEY}:\\s*(.+)$`, "im");
  const m = re.exec(message);
  return m ? m[1]!.trim() : null;
}

/**
 * Parse a trailer VALUE (everything after `Sulis-Origin:`) into a recorded
 * `Origin`, or null when absent / unparseable. The bare leading token is the
 * `kind`; the rest are `key=value` segments split on `;`.
 */
export function originFromTrailerValue(value: string | null): Origin | null {
  if (value === null) return null;
  // A trailer is a SINGLE line. A control character anywhere in the value (a
  // smuggled `\n` + forged trailer, a `\r`, etc.) is malformed or an injection
  // attempt — treat as no/unknown origin (mirrors the Python writer's guard).
  if (hasControlChar(value)) return null;
  const trimmed = value.trim();
  if (trimmed === "") return null;

  let kind = "";
  const fields = new Map<string, string>();
  for (const part of trimmed.split(";")) {
    const seg = part.trim();
    if (seg === "") continue;
    const eq = seg.indexOf("=");
    if (eq === -1) {
      if (kind === "") kind = seg;
      continue;
    }
    fields.set(seg.slice(0, eq).trim(), seg.slice(eq + 1).trim());
  }

  if (kind === "autonomous") {
    const runId = fields.get("run") ?? "";
    if (runId === "") return null;
    const confRaw = fields.get("confidence");
    const conf = confRaw !== undefined ? Number.parseFloat(confRaw) : NaN;
    return {
      kind: "autonomous",
      run: { runId, workflow: null, outcome: "" },
      confidence: Number.isFinite(conf) ? conf : null,
      attribution: "recorded",
    };
  }
  if (kind === "assisted") {
    const conversationId = fields.get("conversation") ?? "";
    if (conversationId === "") return null;
    const turn = Number.parseInt(fields.get("turn") ?? "", 10);
    return {
      kind: "assisted",
      conversation: {
        conversationId,
        turn: Number.isFinite(turn) ? turn : 0,
        summary: null,
      },
      attribution: "recorded",
    };
  }
  return null;
}

/**
 * Parse a parsed sidecar JSON object (`.sulis/origin/<sha>.json`) into a
 * recorded `Origin`, or null when the shape is unrecognised. The sidecar uses
 * the same field names the trailer carries (`kind` / `run` / `confidence` /
 * `conversation` / `turn`).
 */
export function originFromSidecar(obj: unknown): Origin | null {
  if (obj === null || typeof obj !== "object") return null;
  const o = obj as Record<string, unknown>;
  if (o.kind === "autonomous") {
    const runId = typeof o.run === "string" ? o.run : "";
    if (runId === "") return null;
    const conf =
      typeof o.confidence === "number" && Number.isFinite(o.confidence)
        ? o.confidence
        : null;
    return {
      kind: "autonomous",
      run: { runId, workflow: null, outcome: "" },
      confidence: conf,
      attribution: "recorded",
    };
  }
  if (o.kind === "assisted") {
    const conversationId =
      typeof o.conversation === "string" ? o.conversation : "";
    if (conversationId === "") return null;
    const turn = typeof o.turn === "number" ? o.turn : 0;
    return {
      kind: "assisted",
      conversation: { conversationId, turn, summary: null },
      attribution: "recorded",
    };
  }
  return null;
}
