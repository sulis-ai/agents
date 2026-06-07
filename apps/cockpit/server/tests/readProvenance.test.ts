// WP-P05 — readProvenance(worktreeRoot, changeId) tests (ADR-011).
//
// readProvenance is a READ PROJECTION over the same `.brain/instances` tree
// readBrain walks (no second store, no second walk — it composes readBrain).
// It classifies the entities into:
//   - digest:   did (completed lifecycleruns), covered (requirements with a
//               passing testresult.verifies / total requirements), decided
//               (decision count), flagged (gaps + a self-critique from the runs).
//   - runLog:   lifecycleruns newest-first, mapping _step_runs → RunStep.
//   - coverage: Why (opportunity) / What (requirement+verified) / How
//               (design+decision) / Tested (scenario/testresult+outcome).
// And a focused variant resolves one requirement's Why/How/Tested trace.
//
// Fail-soft like the brain read: an absent `.brain` → digest all-zero + empty
// lenses; a malformed run is skipped; a dangling edge is omitted — never throws.
//
// Pure read over the on-disk brain — no process start, no write.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { readProvenance, readFocusedTrace } from "../lib/readProvenance";
import type { ProvenanceView, FocusedTrace } from "../../shared/api-types";

let root: string;

async function writeEntity(
  kind: string,
  ulid: string,
  body: Record<string, unknown>,
): Promise<void> {
  const dir = join(root, ".brain", "instances", "product-development", kind);
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, `${ulid}.jsonld`), JSON.stringify(body), "utf8");
}

/**
 * A small fixture brain mirroring the real instance shapes: two runs (one
 * older, one newer; the newer carries _step_runs + _gaps + _self_critique +
 * confidence + _final_verdict), three requirements (two verified by a passing
 * testresult, one not), one design (satisfies + decisions), one decision, one
 * scenario + one testresult.
 */
async function seedFixtureBrain(): Promise<void> {
  // Why
  await writeEntity("opportunity", "OPP1", {
    id: "dna:opportunity:OPP1",
    title: "Founders lose track of what the agent did",
  });

  // What — three requirements
  await writeEntity("requirement", "REQ1", {
    id: "dna:requirement:REQ1",
    title: "Show a plain-English digest of what happened",
    source: "dna:opportunity:OPP1",
  });
  await writeEntity("requirement", "REQ2", {
    id: "dna:requirement:REQ2",
    statement: "Trace each requirement to its tests",
    source: "dna:opportunity:OPP1",
  });
  await writeEntity("requirement", "REQ3", {
    id: "dna:requirement:REQ3",
    title: "An uncovered requirement",
  });

  // How — one design (satisfies REQ1+REQ2, owns the decision) + one decision
  await writeEntity("design", "DES1", {
    id: "dna:design:DES1",
    title: "Provenance read projection",
    satisfies: ["dna:requirement:REQ1", "dna:requirement:REQ2"],
    decisions: ["dna:decision:DEC1"],
  });
  await writeEntity("decision", "DEC1", {
    id: "dna:decision:DEC1",
    title: "Compose readBrain, no new store",
  });

  // Tested — one scenario verifying REQ1, one passing testresult verifying
  // REQ1+REQ2 (so both count as covered; REQ3 stays uncovered).
  await writeEntity("scenario", "SCN1", {
    id: "dna:scenario:SCN1",
    name: "Open Provenance and read the digest",
    verifies: ["dna:requirement:REQ1"],
    exercises: "dna:design:DES1",
  });
  await writeEntity("testresult", "TR1", {
    id: "dna:testresult:TR1",
    title: "Provenance digest passes",
    outcome: "pass",
    verifies: ["dna:requirement:REQ1", "dna:requirement:REQ2"],
    scenario: "dna:scenario:SCN1",
  });

  // Two runs. The older has no rich fields; the newer is the real-shape run.
  await writeEntity("lifecyclerun", "RUNOLD", {
    id: "dna:lifecyclerun:RUNOLD",
    step_name: "change-started:feat:provenance",
    at: "2026-06-01T08:00:00Z",
    outcome: "completed",
  });
  await writeEntity("lifecyclerun", "RUNNEW", {
    id: "dna:lifecyclerun:RUNNEW",
    step_name: "faithful-generation-harness",
    at: "2026-06-02T00:00:00Z",
    outcome: "completed",
    confidence: 0.88,
    _workflow: "dna:workflow:WF1",
    _final_verdict: "partial-unattributed",
    _step_runs: [
      { step: "observe-manifest", outcome: "completed" },
      { step: "self-critique-grounding", outcome: "completed" },
    ],
    _gaps: [
      {
        claim: "rule-3 branch-protection-on-private-free-plan",
        reason: "no docs source supports the private-free-plan claim",
      },
    ],
    _self_critique:
      "REFUSED to bind rule-3 to org-scoped source (fabricated-provenance refusal upheld).",
  });
}

beforeEach(async () => {
  root = await mkdtemp(join(tmpdir(), "cockpit-prov-"));
});

afterEach(async () => {
  await rm(root, { recursive: true, force: true });
});

describe("readProvenance — digest (ADR-011)", () => {
  it("counts did / covered / decided and surfaces a real flagged gap + self-critique", async () => {
    await seedFixtureBrain();
    const view: ProvenanceView = await readProvenance(root, "01XYZ");

    expect(view.changeId).toBe("01XYZ");
    // did = completed lifecycleruns
    expect(view.digest.did).toBe(2);
    // covered = requirements with a passing testresult / total requirements
    expect(view.digest.covered).toEqual({ verified: 2, total: 3 });
    // decided = decision entities
    expect(view.digest.decided).toBe(1);
    // flagged = gaps from the runs + the top gap text + a self-critique snippet
    expect(view.digest.flagged.count).toBe(1);
    expect(view.digest.flagged.topGap).toContain("branch-protection");
    expect(view.digest.flagged.selfCritique).toContain("REFUSED");
  });

  it("returns digest all-zero + empty lenses for an absent brain (never throws)", async () => {
    const view = await readProvenance(root, "01EMPTY");
    expect(view).toEqual({
      changeId: "01EMPTY",
      digest: {
        did: 0,
        covered: { verified: 0, total: 0 },
        decided: 0,
        flagged: { count: 0, topGap: null, selfCritique: null },
      },
      runLog: [],
      coverage: [],
    });
  });
});

describe("readProvenance — runLog (ADR-011)", () => {
  it("orders runs newest-first and maps _step_runs onto each, tolerating missing fields", async () => {
    await seedFixtureBrain();
    const view = await readProvenance(root, "01XYZ");

    expect(view.runLog.map((r) => r.runId)).toEqual([
      "dna:lifecyclerun:RUNNEW",
      "dna:lifecyclerun:RUNOLD",
    ]);
    const newest = view.runLog[0]!;
    expect(newest.workflow).toBe("dna:workflow:WF1");
    expect(newest.stepName).toBe("faithful-generation-harness");
    expect(newest.outcome).toBe("completed");
    expect(newest.confidence).toBe(0.88);
    expect(newest.finalVerdict).toBe("partial-unattributed");
    expect(newest.steps).toHaveLength(2);
    expect(newest.steps[0]).toEqual({
      step: "observe-manifest",
      outcome: "completed",
      detail: null,
      gap: null,
      selfCritique: null,
    });

    // The older, lean run still maps — missing fields → null / [].
    const oldest = view.runLog[1]!;
    expect(oldest.confidence).toBeNull();
    expect(oldest.workflow).toBeNull();
    expect(oldest.finalVerdict).toBeNull();
    expect(oldest.steps).toEqual([]);
  });

  it("skips a malformed run rather than throwing", async () => {
    await seedFixtureBrain();
    const dir = join(
      root,
      ".brain",
      "instances",
      "product-development",
      "lifecyclerun",
    );
    await writeFile(join(dir, "BAD.jsonld"), "{ not json", "utf8");

    const view = await readProvenance(root, "01XYZ");
    // The two good runs survive; the malformed one is skipped.
    expect(view.runLog).toHaveLength(2);
  });
});

describe("readProvenance — coverage (ADR-011)", () => {
  it("builds the four Why/What/How/Tested columns", async () => {
    await seedFixtureBrain();
    const view = await readProvenance(root, "01XYZ");

    const why = view.coverage.find((c) => c.axis === "why")!;
    expect(why.items).toEqual([
      {
        id: "dna:opportunity:OPP1",
        title: "Founders lose track of what the agent did",
      },
    ]);

    const what = view.coverage.find((c) => c.axis === "what")!;
    if (what.axis !== "what") throw new Error("expected what column");
    expect(what.items).toHaveLength(3);
    const req1 = what.items.find((i) => i.id === "dna:requirement:REQ1")!;
    expect(req1.verified).toBe(true);
    const req3 = what.items.find((i) => i.id === "dna:requirement:REQ3")!;
    expect(req3.verified).toBe(false);
    // statement falls back to a title when no `title` field is present.
    const req2 = what.items.find((i) => i.id === "dna:requirement:REQ2")!;
    expect(req2.title.length).toBeGreaterThan(0);

    const how = view.coverage.find((c) => c.axis === "how")!;
    if (how.axis !== "how") throw new Error("expected how column");
    expect(how.items).toContainEqual({
      id: "dna:design:DES1",
      title: "Provenance read projection",
      kind: "design",
    });
    expect(how.items).toContainEqual({
      id: "dna:decision:DEC1",
      title: "Compose readBrain, no new store",
      kind: "decision",
    });

    const tested = view.coverage.find((c) => c.axis === "tested")!;
    if (tested.axis !== "tested") throw new Error("expected tested column");
    expect(tested.items).toContainEqual({
      id: "dna:testresult:TR1",
      title: "Provenance digest passes",
      outcome: "pass",
      kind: "testresult",
    });
    const scn = tested.items.find((i) => i.id === "dna:scenario:SCN1")!;
    expect(scn.kind).toBe("scenario");
    // A scenario with no recorded outcome defaults to skip (never throws).
    expect(scn.outcome).toBe("skip");
  });
});

describe("readFocusedTrace — one requirement's resolved trace (ADR-011)", () => {
  it("resolves Why (via source), How (design+decisions), Tested (scenario+testresult)", async () => {
    await seedFixtureBrain();
    const trace: FocusedTrace | null = await readFocusedTrace(
      root,
      "01XYZ",
      "dna:requirement:REQ1",
    );

    expect(trace).not.toBeNull();
    expect(trace!.requirementId).toBe("dna:requirement:REQ1");
    expect(trace!.why).toEqual([
      {
        id: "dna:opportunity:OPP1",
        title: "Founders lose track of what the agent did",
      },
    ]);
    // How = the design that satisfies REQ1 + that design's decisions.
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
    // Tested = scenario + testresult verifying REQ1, with outcomes.
    expect(trace!.tested).toContainEqual({
      id: "dna:testresult:TR1",
      title: "Provenance digest passes",
      outcome: "pass",
    });
    expect(trace!.tested.some((t) => t.id === "dna:scenario:SCN1")).toBe(true);
  });

  it("omits a dangling edge rather than throwing", async () => {
    // A requirement whose source points at a non-existent opportunity, and a
    // design satisfying it that names a non-existent decision.
    await writeEntity("requirement", "REQX", {
      id: "dna:requirement:REQX",
      title: "Edge-dangling requirement",
      source: "dna:opportunity:GHOST",
    });
    await writeEntity("design", "DESX", {
      id: "dna:design:DESX",
      title: "Design with a dangling decision",
      satisfies: ["dna:requirement:REQX"],
      decisions: ["dna:decision:GHOST"],
    });

    const trace = await readFocusedTrace(root, "01XYZ", "dna:requirement:REQX");
    expect(trace).not.toBeNull();
    // The ghost opportunity is omitted (no throw).
    expect(trace!.why).toEqual([]);
    // The design resolves; its dangling decision is omitted.
    expect(trace!.how).toEqual([
      {
        id: "dna:design:DESX",
        title: "Design with a dangling decision",
        kind: "design",
      },
    ]);
    expect(trace!.tested).toEqual([]);
  });

  it("returns null for an unknown requirement id", async () => {
    await seedFixtureBrain();
    const trace = await readFocusedTrace(root, "01XYZ", "dna:requirement:NOPE");
    expect(trace).toBeNull();
  });
});
