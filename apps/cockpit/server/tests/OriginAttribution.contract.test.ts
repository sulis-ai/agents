// WP-P08/P09 — shared contract for OriginAttribution (ADR-012).
//
// The behaviour EVERY implementation of the port must satisfy. The inferred
// adapter test (and, at WP-P13, the recorded adapter test) imports `runContract`
// and supplies a factory that seeds its own world. Same assertions, two
// implementations — the fake-vs-adapter parity discipline that guarantees the
// inferred and recorded paths are behaviourally interchangeable from the
// consumer's view (ADR-012): the badge can flip inferred→recorded with no UI
// change.
//
// The contract asserts the SHAPE + the honesty invariant + the three categories,
// NOT the specific attribution value — the inferred adapter returns "inferred",
// the recorded adapter "recorded"; both are valid here. The per-adapter test
// pins its own attribution value on top of this shared suite.

import { describe, it, expect, beforeAll, afterAll } from "vitest";

import type { OriginAttribution } from "../ports/OriginAttribution";

export interface OriginContractWorld {
  attribution: OriginAttribution;
  changeId: string;
  /** A file the implementation will classify autonomous. */
  autonomousPath: string;
  /** A file the implementation will classify assisted. */
  assistedPath: string;
  /** A file the implementation will classify unknown. */
  unknownPath: string;
}

export interface OriginContractFactory {
  setup: () => Promise<OriginContractWorld>;
  teardown?: () => Promise<void>;
}

export function runContract(
  name: string,
  factory: OriginContractFactory,
): void {
  describe(`OriginAttribution contract — ${name}`, () => {
    let world: OriginContractWorld;

    beforeAll(async () => {
      world = await factory.setup();
    });
    afterAll(async () => {
      if (factory.teardown) await factory.teardown();
    });

    it("classifies an autonomous file with a run reference + honesty flag", async () => {
      const origin = await world.attribution.originFor(
        world.changeId,
        world.autonomousPath,
      );
      expect(origin.kind).toBe("autonomous");
      if (origin.kind !== "autonomous") throw new Error("narrowing");
      expect(typeof origin.run.runId).toBe("string");
      expect(origin.run.runId.length).toBeGreaterThan(0);
      // The honesty flag is ALWAYS present (TDD §3.3) — never undefined.
      expect(["inferred", "recorded"]).toContain(origin.attribution);
    });

    it("classifies an assisted file with a conversation reference + honesty flag", async () => {
      const origin = await world.attribution.originFor(
        world.changeId,
        world.assistedPath,
      );
      expect(origin.kind).toBe("assisted");
      if (origin.kind !== "assisted") throw new Error("narrowing");
      expect(typeof origin.conversation.conversationId).toBe("string");
      expect(origin.conversation.conversationId.length).toBeGreaterThan(0);
      expect(typeof origin.conversation.turn).toBe("number");
      expect(["inferred", "recorded"]).toContain(origin.attribution);
    });

    it("returns a plain-English unknown (never an error) when nothing correlates", async () => {
      const origin = await world.attribution.originFor(
        world.changeId,
        world.unknownPath,
      );
      expect(origin.kind).toBe("unknown");
      if (origin.kind !== "unknown") throw new Error("narrowing");
      expect(origin.reason.length).toBeGreaterThan(0);
      expect(["inferred", "recorded"]).toContain(origin.attribution);
    });

    it("never throws for a path it cannot resolve (fail-soft → unknown)", async () => {
      const origin = await world.attribution.originFor(
        world.changeId,
        "this/path/never/existed.txt",
      );
      expect(origin.kind).toBe("unknown");
      expect(["inferred", "recorded"]).toContain(origin.attribution);
    });

    it("always carries a non-empty attribution honesty flag on every variant", async () => {
      for (const p of [
        world.autonomousPath,
        world.assistedPath,
        world.unknownPath,
      ]) {
        const origin = await world.attribution.originFor(world.changeId, p);
        expect(origin.attribution).toBeDefined();
        expect(typeof origin.attribution).toBe("string");
      }
    });
  });
}

// vitest's include pattern matches this file; a trivial self-suite stops the
// runner failing "no test suite found" (the substantive coverage runs through
// the importing per-adapter test files — same pattern as the ChangeStoreReader
// contract module).
describe("OriginAttribution contract module", () => {
  it("exports runContract", () => {
    expect(typeof runContract).toBe("function");
  });
});
