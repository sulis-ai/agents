// WP-011 — intent → {primitive, slug} classification (FR-29 / FR-34 / FR-N9).
//
// The DETERMINISTIC, server-side classifier that turns a founder's plain-English
// intent into a change primitive + a valid change slug. This is the "use the
// existing classifier + change-primitives vocabulary" half of start-from-intent
// — it must NEVER guess: an intent with too little to go on returns
// INTENT_AMBIGUOUS (the route asks ONE clarifying question, FR-29), and an
// investigation kind resolves to a CHANGE primitive (a contained investigation,
// never inline work — FR-34 / FR-N9).
//
// Pure: no fs / process / bridge. The same unit-test discipline as conciergeRead
// (detectRoute) — a vocabulary + word-boundary matching, fully deterministic.

import { describe, it, expect } from "vitest";

import { classifyIntent } from "../lib/discovery/startFromIntent";

// The classifier's output slug must be a VALID change slug (CW-02): 2-5
// kebab-case words, the first starting with a letter. `sulis-change start`
// rejects anything else, so a regression here would 502 at the start step.
const SLUG_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+){1,4}$/;

describe("classifyIntent — intent → {primitive, slug} (FR-29)", () => {
  it("a build/add intent resolves to the `create` primitive + a valid slug", () => {
    const result = classifyIntent("add saved payment cards to checkout", "change");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.primitive).toBe("create");
      expect(result.slug).toMatch(SLUG_RE);
      // The slug is derived from the meaningful words, not the leading verb.
      expect(result.slug).not.toContain("add");
    }
  });

  it("a fix intent resolves to the `fix` primitive (the bug-fix vocabulary)", () => {
    const result = classifyIntent("fix the login redirect loop", "change");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.primitive).toBe("fix");
      expect(result.slug).toMatch(SLUG_RE);
    }
  });

  it("an investigation kind resolves to a CHANGE primitive — never inline work (FR-34/N9)", () => {
    // "look into why checkout is slow" is an investigation: it still becomes a
    // real change (a contained investigation), so it MUST classify to a valid
    // change primitive + slug, not refuse and not run inline.
    const result = classifyIntent("look into why checkout is slow", "investigation");
    expect(result.ok).toBe(true);
    if (result.ok) {
      // A contained investigation maps to a non-behaviour-changing primitive
      // (the work is exploration, not a feature/fix) — but it IS a change.
      expect(result.primitive).toBe("chore");
      expect(result.slug).toMatch(SLUG_RE);
    }
  });

  it("an investigation VERB in a change-kinded intent still routes to a contained investigation", () => {
    // Even without the explicit kind flag, an investigation phrase resolves to
    // the contained-investigation primitive (FR-N9 — investigation is a change).
    const result = classifyIntent("investigate the flaky webhook retries", "change");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.primitive).toBe("chore");
      expect(result.slug).toMatch(SLUG_RE);
    }
  });

  it("an AMBIGUOUS intent (too little to go on) ⇒ INTENT_AMBIGUOUS, never a guess (FR-29)", () => {
    const result = classifyIntent("do the thing", "change");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.code).toBe("INTENT_AMBIGUOUS");
      // The refusal carries ONE clarifying question for the founder (no guess).
      expect(result.clarifyingQuestion).toBeTruthy();
      expect(typeof result.clarifyingQuestion).toBe("string");
    }
  });

  it("an empty / whitespace intent ⇒ INTENT_AMBIGUOUS (nothing to classify)", () => {
    expect(classifyIntent("   ", "change").ok).toBe(false);
    expect(classifyIntent("", "change").ok).toBe(false);
  });

  it("clamps a very long intent to a 2-5 word slug (CW-02 ceiling)", () => {
    const result = classifyIntent(
      "build a brand new fully featured multi tenant billing dashboard system",
      "change",
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.slug).toMatch(SLUG_RE);
      expect(result.slug.split("-").length).toBeLessThanOrEqual(5);
    }
  });

  it("is deterministic — the same intent classifies identically every time", () => {
    const a = classifyIntent("fix the broken signup email", "change");
    const b = classifyIntent("fix the broken signup email", "change");
    expect(a).toEqual(b);
  });
});
