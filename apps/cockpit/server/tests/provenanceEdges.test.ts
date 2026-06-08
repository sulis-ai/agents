// WP-P05 — provenanceEdges pure edge resolver tests (ADR-011).
//
// The coverage focused-trace is resolved entirely server-side from each
// entity's `detail` edges (ADR-011). `resolveFocusedTrace` is a PURE function
// over an already-read set of brain entities (no filesystem, no I/O) so the
// edge discipline is testable in isolation (boring-code):
//   - why     = the opportunity named by requirement.source
//   - how      = designs whose `satisfies` includes the requirement, plus
//                those designs' `decisions`
//   - tested   = scenarios whose `verifies` includes the requirement, plus the
//                testresults whose `verifies` includes it, each with an outcome
//
// A dangling edge (a target id with no matching entity) is omitted, never
// throws.

import { describe, it, expect } from "vitest";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits)
import type { BrainEntity } from "../../shared/api-types";
import { resolveFocusedTrace } from "../lib/provenanceEdges";

function entity(
  kind: string,
  id: string,
  detail: Record<string, unknown>,
): BrainEntity {
  return {
    id,
    kind,
    title: (detail.title as string) ?? (detail.name as string) ?? id,
    detail: { id, ...detail },
  };
}

const fixture: BrainEntity[] = [
  entity("opportunity", "dna:opportunity:OPP1", {
    title: "Founders lose track of what the agent did",
  }),
  entity("requirement", "dna:requirement:REQ1", {
    title: "Show a digest",
    source: "dna:opportunity:OPP1",
  }),
  entity("design", "dna:design:DES1", {
    title: "Provenance read projection",
    satisfies: ["dna:requirement:REQ1"],
    decisions: ["dna:decision:DEC1"],
  }),
  entity("decision", "dna:decision:DEC1", {
    title: "Compose readBrain, no new store",
  }),
  entity("scenario", "dna:scenario:SCN1", {
    name: "Open Provenance",
    verifies: ["dna:requirement:REQ1"],
  }),
  entity("testresult", "dna:testresult:TR1", {
    title: "Digest passes",
    outcome: "pass",
    verifies: ["dna:requirement:REQ1"],
  }),
];

describe("resolveFocusedTrace (ADR-011)", () => {
  it("resolves why / how / tested for a requirement from detail edges", () => {
    const trace = resolveFocusedTrace(fixture, "dna:requirement:REQ1");
    expect(trace).not.toBeNull();
    expect(trace!.requirementId).toBe("dna:requirement:REQ1");

    expect(trace!.why).toEqual([
      {
        id: "dna:opportunity:OPP1",
        title: "Founders lose track of what the agent did",
      },
    ]);

    expect(trace!.how).toContainEqual({
      id: "dna:design:DES1",
      title: "Provenance read projection",
      kind: "design",
    });
    expect(trace!.how).toContainEqual({
      id: "dna:decision:DEC1",
      title: "Compose readBrain, no new store",
      kind: "decision",
    });

    expect(trace!.tested).toContainEqual({
      id: "dna:testresult:TR1",
      title: "Digest passes",
      outcome: "pass",
    });
    expect(trace!.tested).toContainEqual({
      id: "dna:scenario:SCN1",
      title: "Open Provenance",
      outcome: "skip",
    });
  });

  it("omits a dangling edge target without throwing", () => {
    const entities: BrainEntity[] = [
      entity("requirement", "dna:requirement:REQX", {
        title: "Dangling req",
        source: "dna:opportunity:GHOST",
      }),
      entity("design", "dna:design:DESX", {
        title: "Dangling design",
        satisfies: ["dna:requirement:REQX"],
        decisions: ["dna:decision:GHOST"],
      }),
    ];
    const trace = resolveFocusedTrace(entities, "dna:requirement:REQX");
    expect(trace).not.toBeNull();
    expect(trace!.why).toEqual([]);
    expect(trace!.how).toEqual([
      { id: "dna:design:DESX", title: "Dangling design", kind: "design" },
    ]);
    expect(trace!.tested).toEqual([]);
  });

  it("returns null when the requirement is not present", () => {
    expect(resolveFocusedTrace(fixture, "dna:requirement:NOPE")).toBeNull();
  });

  it("maps a fail / skip testresult outcome through, defaulting unknowns to skip", () => {
    const entities: BrainEntity[] = [
      entity("requirement", "dna:requirement:R", { title: "R" }),
      entity("testresult", "dna:testresult:FAIL", {
        title: "Failing",
        outcome: "fail",
        verifies: ["dna:requirement:R"],
      }),
      entity("testresult", "dna:testresult:WEIRD", {
        title: "Unknown outcome",
        outcome: "errored",
        verifies: ["dna:requirement:R"],
      }),
    ];
    const trace = resolveFocusedTrace(entities, "dna:requirement:R");
    expect(trace!.tested).toContainEqual({
      id: "dna:testresult:FAIL",
      title: "Failing",
      outcome: "fail",
    });
    // An outcome outside pass|skip|fail degrades to skip (never throws).
    expect(trace!.tested).toContainEqual({
      id: "dna:testresult:WEIRD",
      title: "Unknown outcome",
      outcome: "skip",
    });
  });
});
