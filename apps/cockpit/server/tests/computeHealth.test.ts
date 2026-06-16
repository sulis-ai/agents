// WP-002 — computeHealth.ts unit tests (ADR-001 / FR-30 / FR-31 / FR-32).
//
// The cheap, honest change-health rollup. PURE: no I/O. Over the cross
// product of { testsState } × { rigorForStage }, the verdict is:
//
//   - red tests OR rigorForStage.ok === false → off-track (reason names
//     which: tests vs the missing artifact).
//   - testsState === "unknown" AND rigorForStage.determinable === false →
//     unknown (the FR-31 honest read — a fresh change with nothing behind
//     it must NOT read on-track).
//   - else → on-track.
//
// It NEVER emits "worth-a-look" (S-19) — that state is reserved for the
// deferred OODA-spiral drift signal (ADR-001). Reasons are a fixed
// enumerable set, never interpolated from change content (FR-32).

import { describe, it, expect } from "vitest";

import { computeHealth } from "../lib/computeHealth";
import type { RigorForStage } from "../lib/readRigorForStage";

const rigorOk: RigorForStage = { ok: true, missing: null, determinable: true };
const rigorMissingDesign: RigorForStage = {
  ok: false,
  missing: "design",
  determinable: true,
};
const rigorMissingSpec: RigorForStage = {
  ok: false,
  missing: "spec",
  determinable: true,
};
const rigorMissingTests: RigorForStage = {
  ok: false,
  missing: "tests",
  determinable: true,
};
const rigorIndeterminate: RigorForStage = {
  ok: true,
  missing: null,
  determinable: false,
};

describe("computeHealth — off-track (BR-10)", () => {
  it("red tests → off-track, reason names tests", () => {
    const h = computeHealth({ testsState: "red", rigorForStage: rigorOk });
    expect(h.state).toBe("off-track");
    expect(h.reason).toBe("tests failing");
  });

  it("red tests dominate even when rigor is also missing → off-track on tests", () => {
    // Tests-red is the most concrete failure; it names tests, not the
    // missing artifact (most-urgent-first, fixed reason).
    const h = computeHealth({
      testsState: "red",
      rigorForStage: rigorMissingDesign,
    });
    expect(h.state).toBe("off-track");
    expect(h.reason).toBe("tests failing");
  });

  it("missing spec (rigor.ok false) → off-track, reason names the spec", () => {
    const h = computeHealth({
      testsState: "green",
      rigorForStage: rigorMissingSpec,
    });
    expect(h.state).toBe("off-track");
    expect(h.reason).toBe("no spec recorded");
  });

  it("missing design → off-track, reason names the design", () => {
    const h = computeHealth({
      testsState: "unknown",
      rigorForStage: rigorMissingDesign,
    });
    expect(h.state).toBe("off-track");
    expect(h.reason).toBe("no design recorded");
  });

  it("missing tests-alongside-code → off-track, reason names tests", () => {
    const h = computeHealth({
      testsState: "green",
      rigorForStage: rigorMissingTests,
    });
    expect(h.state).toBe("off-track");
    expect(h.reason).toBe("no tests alongside the code");
  });
});

describe("computeHealth — unknown (FR-31, the honest read)", () => {
  it("no test state AND rigor indeterminate → unknown, not on-track", () => {
    const h = computeHealth({
      testsState: "unknown",
      rigorForStage: rigorIndeterminate,
    });
    expect(h.state).toBe("unknown");
    expect(h.reason).toBe("too early to tell");
  });

  it("a fresh change (unknown tests, indeterminate rigor) does not masquerade as on-track", () => {
    const h = computeHealth({
      testsState: "unknown",
      rigorForStage: rigorIndeterminate,
    });
    expect(h.state).not.toBe("on-track");
  });
});

describe("computeHealth — on-track", () => {
  it("green tests + rigor ok → on-track", () => {
    const h = computeHealth({ testsState: "green", rigorForStage: rigorOk });
    expect(h.state).toBe("on-track");
    expect(h.reason).toBe("tests green and on-stage");
  });

  it("unknown tests but rigor determinable-and-ok → on-track (rigor carries it)", () => {
    // Rigor IS determinable and ok, so we are not in the FR-31 unknown
    // hole — the change has the artifacts for its stage, just no test run.
    const h = computeHealth({ testsState: "unknown", rigorForStage: rigorOk });
    expect(h.state).toBe("on-track");
    expect(h.reason).toBe("on track for this stage");
  });

  it("green tests but rigor indeterminate → on-track (a real green test is signal)", () => {
    // Tests are a concrete green; rigor being indeterminate does not pull a
    // green-tested change into the unknown hole (FR-31 needs BOTH absent).
    const h = computeHealth({
      testsState: "green",
      rigorForStage: rigorIndeterminate,
    });
    expect(h.state).toBe("on-track");
  });
});

describe("computeHealth — never worth-a-look (S-19, ADR-001 deferral)", () => {
  it("no input combination ever yields worth-a-look", () => {
    const testsStates: Array<"green" | "red" | "unknown"> = [
      "green",
      "red",
      "unknown",
    ];
    const rigors: RigorForStage[] = [
      rigorOk,
      rigorMissingSpec,
      rigorMissingDesign,
      rigorMissingTests,
      rigorIndeterminate,
    ];
    for (const testsState of testsStates) {
      for (const rigorForStage of rigors) {
        const h = computeHealth({ testsState, rigorForStage });
        expect(h.state).not.toBe("worth-a-look");
        // And the state is always one of the three the producer emits.
        expect(["on-track", "off-track", "unknown"]).toContain(h.state);
      }
    }
  });
});

describe("computeHealth — reasons are a fixed enumerable set (FR-32)", () => {
  it("every reason is drawn from the known fixed strings", () => {
    const allowed = new Set([
      "tests failing",
      "no spec recorded",
      "no design recorded",
      "no tests alongside the code",
      "too early to tell",
      "tests green and on-stage",
      "on track for this stage",
    ]);
    const testsStates: Array<"green" | "red" | "unknown"> = [
      "green",
      "red",
      "unknown",
    ];
    const rigors: RigorForStage[] = [
      rigorOk,
      rigorMissingSpec,
      rigorMissingDesign,
      rigorMissingTests,
      rigorIndeterminate,
    ];
    for (const testsState of testsStates) {
      for (const rigorForStage of rigors) {
        const h = computeHealth({ testsState, rigorForStage });
        expect(allowed.has(h.reason)).toBe(true);
      }
    }
  });
});
