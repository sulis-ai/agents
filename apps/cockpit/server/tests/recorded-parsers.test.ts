// WP-P13 — pure recorded-origin parser tests (ADR-013).
//
// `recorded.ts` owns the single `Sulis-Origin:` trailer parse. These tests pin
// the parser directly (no git, no fs — it is pure), including the security
// guard that a trailer VALUE carrying a control character (a trailer-injection
// attempt, the mirror of the Python writer's guard) is treated as no/unknown
// origin rather than parsed into a forged result.

import { describe, it, expect } from "vitest";

import {
  ORIGIN_TRAILER_KEY,
  originFromTrailerValue,
  trailerValueFromMessage,
} from "../lib/originAttribution/recorded";

describe("recorded.ts — originFromTrailerValue", () => {
  it("parses a well-formed autonomous value", () => {
    const o = originFromTrailerValue("autonomous; run=RUN1; confidence=0.9");
    expect(o?.kind).toBe("autonomous");
    if (o?.kind !== "autonomous") throw new Error("narrowing");
    expect(o.run.runId).toBe("RUN1");
    expect(o.confidence).toBe(0.9);
    expect(o.attribution).toBe("recorded");
  });

  it("parses a well-formed assisted value", () => {
    const o = originFromTrailerValue("assisted; conversation=c1; turn=4");
    expect(o?.kind).toBe("assisted");
    if (o?.kind !== "assisted") throw new Error("narrowing");
    expect(o.conversation.conversationId).toBe("c1");
    expect(o.conversation.turn).toBe(4);
  });

  it("returns null for null / empty / unknown-kind", () => {
    expect(originFromTrailerValue(null)).toBeNull();
    expect(originFromTrailerValue("")).toBeNull();
    expect(originFromTrailerValue("autonomous; confidence=0.5")).toBeNull(); // no run
    expect(originFromTrailerValue("nonsense")).toBeNull();
  });

  it("rejects a value carrying a control character (no forged origin)", () => {
    // A smuggled newline + forged trailer line must NOT parse to an origin.
    expect(
      originFromTrailerValue(
        "autonomous; run=abc\nMalicious-Trailer: pwned; confidence=0.9",
      ),
    ).toBeNull();
    // A carriage return is equally rejected.
    expect(
      originFromTrailerValue("autonomous; run=abc\rconfidence=0.9"),
    ).toBeNull();
    // Any other control char (vertical tab) is rejected too.
    expect(originFromTrailerValue("autonomous; run=ab\x0bc")).toBeNull();
  });
});

describe("recorded.ts — trailerValueFromMessage", () => {
  it("pulls the trailer value out of a full commit message", () => {
    const msg = `feat: a thing\n\n${ORIGIN_TRAILER_KEY}: autonomous; run=R1`;
    expect(trailerValueFromMessage(msg)).toBe("autonomous; run=R1");
  });

  it("returns null when no trailer is present", () => {
    expect(trailerValueFromMessage("feat: nothing here")).toBeNull();
  });
});
