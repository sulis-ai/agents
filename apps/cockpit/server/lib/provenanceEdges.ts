// WP-P05 — provenanceEdges: the pure edge resolver for the focused trace.
//
// The Provenance coverage map's per-requirement focused trace (ADR-011) is
// resolved entirely SERVER-SIDE from each entity's `detail` edges — the client
// never walks edges. This module is a PURE function over an already-read set of
// brain entities (no filesystem, no I/O), so the edge discipline is testable in
// isolation (the "boring-code" half of the Blue DoD).
//
// Edges (all live in an entity's `detail`):
//   requirement.source  → opportunity          (the Why)
//   design.satisfies[]  ⊇ requirement          (a How: the design)
//   design.decisions[]  → decision             (a How: the design's decisions)
//   scenario.verifies[] ⊇ requirement          (a Tested: scenario, outcome skip)
//   testresult.verifies[] ⊇ requirement        (a Tested: testresult + outcome)
//
// Fail-soft (the brain read's posture): a dangling edge (a target id with no
// matching entity) is omitted; an unknown requirement returns null; a missing
// `detail` or missing field is treated as absent. Never throws.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { BrainEntity, FocusedTrace } from "../../shared/api-types";

type Detail = Record<string, unknown>;

/** The detail object, or {} when an entity carries none. */
function detailOf(entity: BrainEntity): Detail {
  return entity.detail ?? {};
}

/** A string field, or null when absent / not a string. */
function str(detail: Detail, key: string): string | null {
  const v = detail[key];
  return typeof v === "string" && v.length > 0 ? v : null;
}

/** A field as an array of id strings (tolerating a single string or absent). */
function idList(detail: Detail, key: string): string[] {
  const v = detail[key];
  if (typeof v === "string") return [v];
  if (Array.isArray(v)) return v.filter((x): x is string => typeof x === "string");
  return [];
}

/** Coerce any testresult/scenario outcome to the contract's tri-state. */
export function normaliseOutcome(raw: unknown): "pass" | "skip" | "fail" {
  if (raw === "pass" || raw === "fail" || raw === "skip") return raw;
  return "skip";
}

/**
 * Resolve the Why → How → Tested focused trace for one requirement from the
 * `detail` edges across the supplied entities. Returns null when the
 * requirement id is not present in the set.
 */
export function resolveFocusedTrace(
  entities: BrainEntity[],
  requirementId: string,
): FocusedTrace | null {
  const byId = new Map(entities.map((e) => [e.id, e]));
  const requirement = byId.get(requirementId);
  if (!requirement) return null;

  // Why: the opportunity named by requirement.source (omit a dangling ref).
  const why: FocusedTrace["why"] = [];
  const sourceId = str(detailOf(requirement), "source");
  if (sourceId) {
    const opp = byId.get(sourceId);
    if (opp) why.push({ id: opp.id, title: opp.title });
  }

  // How: designs that satisfy the requirement, plus each design's decisions.
  const how: FocusedTrace["how"] = [];
  const seenHow = new Set<string>();
  const pushHow = (id: string, title: string, kind: "design" | "decision") => {
    if (seenHow.has(id)) return;
    seenHow.add(id);
    how.push({ id, title, kind });
  };
  for (const entity of entities) {
    if (entity.kind !== "design") continue;
    const d = detailOf(entity);
    if (!idList(d, "satisfies").includes(requirementId)) continue;
    pushHow(entity.id, entity.title, "design");
    for (const decisionId of idList(d, "decisions")) {
      const decision = byId.get(decisionId);
      if (decision) pushHow(decision.id, decision.title, "decision");
    }
  }

  // Tested: scenarios + testresults whose `verifies` includes the requirement.
  const tested: FocusedTrace["tested"] = [];
  const seenTested = new Set<string>();
  for (const entity of entities) {
    if (entity.kind !== "scenario" && entity.kind !== "testresult") continue;
    const d = detailOf(entity);
    if (!idList(d, "verifies").includes(requirementId)) continue;
    if (seenTested.has(entity.id)) continue;
    seenTested.add(entity.id);
    tested.push({
      id: entity.id,
      title: entity.title,
      // A scenario has no recorded outcome → skip; a testresult carries one.
      outcome: normaliseOutcome(d.outcome),
    });
  }

  return { requirementId, why, how, tested };
}
