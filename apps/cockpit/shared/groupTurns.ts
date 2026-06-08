// Chat-redesign (chat-B2 signed contract) — group a flat transcript into the
// Turn-Cards model. SHARED by the client (renders the turns) and the server
// (summarises them), so the per-turn keys match exactly.
//
// Each founder message is a bubble; each run of consecutive agent messages
// collapses into ONE turn (the agent's prose + a folded list of the steps it
// took). The steps come straight from the recorded tool calls — no model
// needed (the 2–3 sentence summary is generated separately, by the Haiku
// pass, with a first-few-sentences fallback).

import type { TranscriptMessage } from "./api-types";

export type StepKind = "edit" | "read" | "run" | "search" | "todo" | "other";

export interface TurnStep {
  kind: StepKind;
  label: string;
  /** A short object the step acted on (a filename), when known. */
  object?: string;
}

export interface UserItem {
  type: "user";
  key: string;
  text: string;
  timestamp: string;
}

export interface TurnItem {
  type: "turn";
  key: string;
  /** The agent's joined prose for the turn (what it said to you). */
  said: string;
  steps: TurnStep[];
  timestamp: string;
}

export type ConversationItem = UserItem | TurnItem;

/** The first sentence of a block of prose. */
export function firstSentence(text: string): string {
  return firstSentences(text, 1);
}

/**
 * The first `count` sentences of a block of prose — the summary fallback
 * while the generated (Haiku) 2–3 sentence summary isn't ready yet.
 */
export function firstSentences(text: string, count = 3): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (!t) return "";
  const parts = t.match(/[^.!?]+[.!?]+(\s|$)/g);
  if (!parts || parts.length === 0) {
    return t.length > 280 ? `${t.slice(0, 277)}…` : t;
  }
  const out = parts.slice(0, count).join("").trim();
  return out || (t.length > 280 ? `${t.slice(0, 277)}…` : t);
}

function basename(p: string): string {
  const parts = p.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? p;
}

/** Map a recorded tool call to a plain-English step row. */
function stepFromTool(toolName: string, input: unknown): TurnStep {
  const o =
    input && typeof input === "object"
      ? (input as Record<string, unknown>)
      : {};
  const fileField = o.file_path ?? o.path ?? o.notebook_path;
  const file = typeof fileField === "string" ? basename(fileField) : undefined;

  switch (toolName) {
    case "Edit":
    case "MultiEdit":
    case "NotebookEdit":
      return { kind: "edit", label: "Edited a file", object: file };
    case "Write":
      return { kind: "edit", label: "Wrote a file", object: file };
    case "Read":
      return { kind: "read", label: "Read a file", object: file };
    case "Bash": {
      const desc = o.description;
      return {
        kind: "run",
        label: typeof desc === "string" && desc.trim() ? desc.trim() : "Ran a command",
      };
    }
    case "Grep":
    case "Glob":
      return { kind: "search", label: "Searched the code" };
    case "TodoWrite":
      return { kind: "todo", label: "Updated the plan" };
    default:
      return {
        kind: "other",
        label: toolName.replace(/([a-z0-9])([A-Z])/g, "$1 $2"),
      };
  }
}

export function groupTurns(messages: TranscriptMessage[]): ConversationItem[] {
  const items: ConversationItem[] = [];
  let current: TurnItem | null = null;

  const flush = () => {
    if (current) {
      items.push(current);
      current = null;
    }
  };

  for (const m of messages) {
    if (m.kind === "user") {
      // Skip empty/whitespace-only user messages (e.g. tool-result-carrying
      // turns that have no founder text) — they'd render as blank bubbles.
      if (!m.text || !m.text.trim()) continue;
      flush();
      items.push({
        type: "user",
        key: m.uuid,
        text: m.text,
        timestamp: m.timestamp,
      });
      continue;
    }
    if (m.kind === "assistant") {
      if (!current) {
        current = {
          type: "turn",
          key: m.uuid,
          said: "",
          steps: [],
          timestamp: m.timestamp,
        };
      }
      const texts: string[] = [];
      for (const block of m.blocks) {
        if (block.kind === "text" && block.text.trim()) {
          texts.push(block.text.trim());
        } else if (block.kind === "tool-use") {
          current.steps.push(stepFromTool(block.toolName, block.input));
        }
      }
      if (texts.length) {
        current.said = current.said
          ? `${current.said}\n\n${texts.join("\n\n")}`
          : texts.join("\n\n");
      }
      current.timestamp = m.timestamp;
      continue;
    }
    // system messages are agent-lifecycle meta — they don't belong in the
    // founder-facing card stream; skip them here.
  }
  flush();
  return items;
}
