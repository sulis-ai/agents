// WP-003 — ConversationIdentity seam + relay-origin helper (ADR-016, ADR-018).
//
// The two small units this WP introduces, tested without an HTTP server or a
// child process (the whole point of isolating them):
//
//   - LocalTranscriptConversationIdentity (the ONLY adapter this change ships):
//     maps a resolved session + its transcript to a ThreadIdentity, deriving the
//     identity LOCALLY and read-only (ADR-018 D1). `conversation` is a
//     `thread_`-shaped Thread id over the session's stable identity (the
//     `lastSessionRef` stem); `turn` is the 1-based Message ordinal
//     (`groupTurns(transcript).filter(isTurn).length + 1`, ADR-016).
//   - assistedOriginEnv (the relay helper): calls the port and formats the
//     assisted `SULIS_ORIGIN` body in #216's grammar, or returns null when the
//     identity can't be derived (caller spawns unstamped — ADR-013 degrade).
//
// Grammar fit is asserted by parsing the emitted value back through the cockpit's
// OWN #216-grammar reader (`originFromTrailerValue`) — the same parser the
// recorded read path uses — so this test catches any drift from the accepted
// shape locally. WP-006 locks the cross-language (Python) round-trip separately.

import { describe, it, expect } from "vitest";

import { LocalTranscriptConversationIdentity } from "../adapters/LocalTranscriptConversationIdentity";
import { assistedOriginEnv } from "../lib/relayOrigin";
import { deriveThreadId, sessionStemFromRef } from "../lib/threadIdentity";
import type { SessionResolution } from "../ports/SessionBridge";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/)
import type { TranscriptMessage } from "../../shared/api-types";

const CWD = "/tmp/worktree-wp003";

/** A `resumable` resolution carrying a transcript path as `lastSessionRef`. */
function resolution(sessionId: string): SessionResolution {
  return {
    kind: "resumable",
    session: {
      changeId: "01KTHP2NYQ1A3WHPJD75VP31NT",
      cwd: CWD,
      lastSessionRef: `/Users/x/.claude/projects/-mangled/${sessionId}.jsonl`,
    },
  };
}

/** A `fresh` resolution (no transcript yet → no `lastSessionRef`). */
function freshResolution(): SessionResolution {
  return {
    kind: "fresh",
    session: {
      changeId: "01KTHP2NYQ1A3WHPJD75VP31NT",
      cwd: CWD,
    },
  };
}

/** A user message (a founder bubble — counts toward turns). */
function user(uuid: string, text: string): TranscriptMessage {
  return { kind: "user", uuid, timestamp: "2026-06-07T10:00:00Z", text };
}

/** An assistant message (collapses with adjacent assistant msgs into one turn). */
function assistant(uuid: string, said: string): TranscriptMessage {
  return {
    kind: "assistant",
    uuid,
    timestamp: "2026-06-07T10:00:01Z",
    blocks: [{ kind: "text", text: said }],
  };
}

/** Build a transcript with `n` user/assistant turn-pairs (n grouped turns). */
function transcriptWithTurns(n: number): TranscriptMessage[] {
  const msgs: TranscriptMessage[] = [];
  for (let i = 0; i < n; i++) {
    msgs.push(user(`u${i}`, `prompt ${i}`));
    msgs.push(assistant(`a${i}`, `reply ${i}.`));
  }
  return msgs;
}

describe("threadIdentity (the single shared derivation rule — EP-03)", () => {
  it("deriveThreadId carries the thread_ shape and is a pure function of the stem", () => {
    expect(deriveThreadId("xyz")).toBe("thread_xyz");
    expect(deriveThreadId("xyz")).toBe(deriveThreadId("xyz")); // pure
    expect(deriveThreadId("aaa")).not.toBe(deriveThreadId("bbb")); // distinct
  });

  it("deriveThreadId returns null for an empty / whitespace-only stem", () => {
    expect(deriveThreadId("")).toBeNull();
    expect(deriveThreadId("   ")).toBeNull();
  });

  it("sessionStemFromRef recovers the stem from a transcript path or raw id", () => {
    expect(sessionStemFromRef("/a/b/sess-1.jsonl")).toBe("sess-1");
    expect(sessionStemFromRef("sess-2.jsonl")).toBe("sess-2");
    expect(sessionStemFromRef("sess-3")).toBe("sess-3"); // raw id, no suffix
  });

  it("sessionStemFromRef returns null for undefined / empty refs", () => {
    expect(sessionStemFromRef(undefined)).toBeNull();
    expect(sessionStemFromRef("")).toBeNull();
    expect(sessionStemFromRef(".jsonl")).toBeNull(); // suffix only → empty stem
  });
});

describe("LocalTranscriptConversationIdentity", () => {
  const identity = new LocalTranscriptConversationIdentity();

  it("derives a thread_-shaped threadId that is a pure function of the session id stem", () => {
    const r = identity.forResolvedSession(
      resolution("abc123-session-id"),
      transcriptWithTurns(2),
    );
    expect(r).not.toBeNull();
    expect(r!.threadId).toMatch(/^thread_/);
    // Pure function of the stem: the same stem renders the same id via the
    // SINGLE shared derivation helper the inferred path (WP-004) will reuse.
    expect(r!.threadId).toBe(deriveThreadId("abc123-session-id"));
  });

  it("returns turn === existing-turn-count + 1 (the Message ordinal)", () => {
    const r = identity.forResolvedSession(
      resolution("sess-turns"),
      transcriptWithTurns(3),
    );
    expect(r).not.toBeNull();
    expect(r!.turn).toBe(4); // 3 existing turns + the in-flight one
  });

  it("yields distinct threadIds for two distinct transcript stems (multi-session gap)", () => {
    const a = identity.forResolvedSession(
      resolution("session-A"),
      transcriptWithTurns(1),
    );
    const b = identity.forResolvedSession(
      resolution("session-B"),
      transcriptWithTurns(1),
    );
    expect(a).not.toBeNull();
    expect(b).not.toBeNull();
    expect(a!.threadId).not.toBe(b!.threadId);
  });

  it("returns null for a fresh resolution (no lastSessionRef → unstamped → inferred)", () => {
    expect(
      identity.forResolvedSession(freshResolution(), transcriptWithTurns(2)),
    ).toBeNull();
  });

  it("is best-effort: a malformed transcript never throws (degrades to null or a value)", () => {
    // A bogus transcript shape must not crash the helper (ADR-013 non-fatal).
    const bogus = [{ kind: "nope" }] as unknown as TranscriptMessage[];
    expect(() =>
      identity.forResolvedSession(resolution("sess-bogus"), bogus),
    ).not.toThrow();
  });
});

describe("assistedOriginEnv", () => {
  const identity = new LocalTranscriptConversationIdentity();

  it("emits a SULIS_ORIGIN body that parses to {kind:'assisted', conversation:<threadId>, turn:<n>} with turn as an integer", async () => {
    // Parse the emitted value back through the cockpit's OWN #216-grammar reader
    // (the recorded read path's parser) — local grammar-fit guard.
    const { originFromTrailerValue } = await import(
      "../lib/originAttribution/recorded"
    );

    const env = assistedOriginEnv(
      identity,
      resolution("grammar-session"),
      transcriptWithTurns(2),
    );
    expect(env).not.toBeNull();
    const body = env!["SULIS_ORIGIN"];
    expect(body).toBeDefined();

    const parsed = originFromTrailerValue(body!);
    expect(parsed).not.toBeNull();
    expect(parsed!.kind).toBe("assisted");
    if (parsed!.kind === "assisted") {
      expect(parsed!.conversation.conversationId).toBe(
        deriveThreadId("grammar-session"),
      );
      expect(parsed!.conversation.turn).toBe(3); // 2 existing + in-flight
      expect(Number.isInteger(parsed!.conversation.turn)).toBe(true);
    }
  });

  it("returns null when the identity cannot be derived (fresh → spawn unstamped)", () => {
    expect(
      assistedOriginEnv(identity, freshResolution(), transcriptWithTurns(2)),
    ).toBeNull();
  });

  // ── Blue (DoD hardening) ──────────────────────────────────────────────────

  it("passes the threadId through AS-IS — no second sanitiser (the #216 parser is the boundary guard)", () => {
    // The emitted body must carry the EXACT derived threadId, unmodified — the
    // helper does not strip / transform / re-encode it (no second sanitiser;
    // §3 hardening). #216's parser performs the control-char / shape guard.
    const env = assistedOriginEnv(
      identity,
      resolution("verbatim-stem"),
      transcriptWithTurns(0),
    );
    expect(env).not.toBeNull();
    const expectedId = deriveThreadId("verbatim-stem");
    expect(env!["SULIS_ORIGIN"]).toBe(
      `assisted; conversation=${expectedId}; turn=1`,
    );
  });

  it("derives the threadId via the SINGLE shared rule (EP-03) — the adapter does not re-implement it", () => {
    // The adapter's id MUST equal deriveThreadId(sessionStemFromRef(ref)) — i.e.
    // it delegates to the shared lib/threadIdentity rule rather than carrying its
    // own copy. WP-004's inferred path imports the same `deriveThreadId`, so
    // recorded and inferred render the SAME id for the same file.
    const ref = "/Users/x/.claude/projects/-mangled/shared-rule-stem.jsonl";
    const r = identity.forResolvedSession(
      {
        kind: "resumable",
        session: { changeId: "c", cwd: CWD, lastSessionRef: ref },
      },
      transcriptWithTurns(1),
    );
    expect(r).not.toBeNull();
    expect(r!.threadId).toBe(
      deriveThreadId(sessionStemFromRef(ref) as string),
    );
  });
});
