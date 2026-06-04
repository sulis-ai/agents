// Chat-redesign (chat-B2) — turn-summary cache + background generation.
//
// getTurnSummaries is cache-first + non-blocking: the first read kicks off
// generation (via the injected generator), a later read returns the cached
// result. The generator is injected so no real `claude` is spawned.

import { describe, it, expect, vi } from "vitest";
import type { TranscriptMessage } from "../../shared/api-types";
import { getTurnSummaries } from "../lib/turnSummaries";

function turn(uuid: string, text: string): TranscriptMessage {
  return {
    kind: "assistant",
    uuid,
    timestamp: "2026-01-01T00:00:00Z",
    blocks: [{ kind: "text", text }],
  };
}

describe("getTurnSummaries (chat-B2)", () => {
  it("kicks off generation, then serves the generated summary on a later read", async () => {
    // Unique content so the content-addressed cache key can't collide with
    // another test run.
    const said = `did a unique thing ${Date.now()}-${Math.random()}`;
    const messages: TranscriptMessage[] = [turn("t1", said)];
    const SUMMARY = "Shipped the thing. It now works end to end.";
    const generate = vi.fn(async () => SUMMARY);

    // First read: nothing cached yet → empty map, but generation is enqueued
    // and the turn shows as "generating".
    const first = await getTurnSummaries(messages, { generate });
    expect(first.summaries.t1).toBeUndefined();
    expect(first.generating).toContain("t1");

    // Background generation runs; wait for it.
    await vi.waitFor(() => expect(generate).toHaveBeenCalledTimes(1));
    await new Promise((r) => setTimeout(r, 10));

    // Later read: the generated summary is served from cache, keyed by turn.
    const second = await getTurnSummaries(messages, { generate });
    expect(second.summaries.t1).toBe(SUMMARY);
    expect(second.generating).not.toContain("t1");
  });

  it("does not enqueue a turn that's already generated (computed once)", async () => {
    const said = `another unique thing ${Date.now()}-${Math.random()}`;
    const messages: TranscriptMessage[] = [turn("t2", said)];
    const generate = vi.fn(async () => "Done. All good.");

    await getTurnSummaries(messages, { generate });
    await vi.waitFor(() => expect(generate).toHaveBeenCalledTimes(1));
    await new Promise((r) => setTimeout(r, 10));

    // Two more reads — the cached result is reused; the generator is NOT
    // called again for the same content.
    await getTurnSummaries(messages, { generate });
    await getTurnSummaries(messages, { generate });
    expect(generate).toHaveBeenCalledTimes(1);
  });

  it("skips empty turns and user messages (nothing to summarise)", async () => {
    const messages: TranscriptMessage[] = [
      { kind: "user", uuid: "u1", timestamp: "2026-01-01T00:00:00Z", text: "hi" },
    ];
    const generate = vi.fn(async () => "x");
    const out = await getTurnSummaries(messages, { generate });
    expect(out.summaries).toEqual({});
    expect(out.generating).toEqual([]);
    expect(generate).not.toHaveBeenCalled();
  });
});
