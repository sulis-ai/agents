// WP-002 — deriveLastActivityAt.ts unit tests (FR-40 / FR-42).
//
// The feed carries `lastActivityAt: string | null` (ISO) used for the
// recency text and the working/live split. It is derived PURELY from the
// already-gathered read-time context (no extra I/O — the route already
// parses the transcript for the attention verdict):
//   - the timestamp of the most-recent transcript message, when present,
//   - else the record's own `updatedAt` (the last stage transition),
//   - else null (FR-42 — a never-active change shows "—", not a bogus age).
//
// Pure: no I/O. Never throws on an empty transcript or an absent updatedAt.

import { describe, it, expect } from "vitest";

import { deriveLastActivityAt } from "../lib/deriveLastActivityAt";
import type { TranscriptMessage } from "../../shared/api-types";

function userMsg(timestamp: string): TranscriptMessage {
  return { kind: "user", uuid: "u1", timestamp, text: "hi" };
}

function assistantMsg(timestamp: string): TranscriptMessage {
  return {
    kind: "assistant",
    uuid: "a1",
    timestamp,
    blocks: [{ kind: "text", text: "done" }],
  };
}

describe("deriveLastActivityAt (FR-40)", () => {
  it("uses the last transcript message timestamp when present", () => {
    const transcript: TranscriptMessage[] = [
      userMsg("2026-05-01T10:00:00Z"),
      assistantMsg("2026-05-01T10:05:00Z"),
    ];
    expect(deriveLastActivityAt(transcript, "2026-04-01T00:00:00Z")).toBe(
      "2026-05-01T10:05:00Z",
    );
  });

  it("the last message wins even if earlier than updatedAt — transcript is the activity truth", () => {
    const transcript: TranscriptMessage[] = [userMsg("2026-05-01T09:00:00Z")];
    expect(deriveLastActivityAt(transcript, "2026-05-10T00:00:00Z")).toBe(
      "2026-05-01T09:00:00Z",
    );
  });

  it("falls back to updatedAt when the transcript is empty", () => {
    expect(deriveLastActivityAt([], "2026-05-02T00:00:00Z")).toBe(
      "2026-05-02T00:00:00Z",
    );
  });

  it("returns null when there is no transcript and no updatedAt (FR-42)", () => {
    expect(deriveLastActivityAt([], null)).toBeNull();
  });

  it("returns null when the transcript is empty and updatedAt is empty string", () => {
    expect(deriveLastActivityAt([], "")).toBeNull();
  });
});
