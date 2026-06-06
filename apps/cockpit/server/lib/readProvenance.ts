// WP-P05 — readProvenance(worktreeRoot, changeId) (ADR-011).
//
// The Provenance read PROJECTION: a digest dashboard + a run-log lens + a
// coverage map, computed at READ time over the SAME `.brain/instances` tree the
// brain view reads. It COMPOSES `readBrain` (no new store, no second brain
// walk — ADR-011, EP-03) and classifies the entities:
//
//   digest.did      = completed `lifecyclerun`s ("what it did").
//   digest.covered  = { verified: requirements a PASSING testresult.verifies
//                       covers, total: all requirements } ("what it covered").
//   digest.decided  = `decision` entities ("what it decided").
//   digest.flagged  = from the runs' `_gaps` / `_self_critique` — the count, the
//                     top gap text, and a self-critique snippet ("what it
//                     flagged" — the trust tile).
//   runLog          = `lifecyclerun`s newest-first (by `at`), each mapping its
//                     `_step_runs` → RunStep (tolerating missing fields → null).
//   coverage        = the four Why/What/How/Tested columns.
//
// The `?focus=<reqId>` variant returns a single requirement's FocusedTrace via
// the pure edge resolver (`provenanceEdges`).
//
// Fail-soft like the brain read: an absent `.brain` → digest all-zero + empty
// lenses; a malformed run is skipped by `readBrain`; a dangling edge is omitted.
// Pure read over the on-disk brain — no process start, no write.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type {
  BrainEntity,
  CoverageColumn,
  FocusedTrace,
  ProvenanceDigest,
  ProvenanceView,
  RunLogEntry,
  RunStep,
} from "../../shared/api-types";
import { readBrain } from "./readBrain";
import { normaliseOutcome, resolveFocusedTrace } from "./provenanceEdges";

type Detail = Record<string, unknown>;

function detailOf(entity: BrainEntity): Detail {
  return entity.detail ?? {};
}

function str(detail: Detail, key: string): string | null {
  const v = detail[key];
  return typeof v === "string" && v.length > 0 ? v : null;
}

function num(detail: Detail, key: string): number | null {
  const v = detail[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function idList(detail: Detail, key: string): string[] {
  const v = detail[key];
  if (typeof v === "string") return [v];
  if (Array.isArray(v)) return v.filter((x): x is string => typeof x === "string");
  return [];
}

/** Flatten the brain view's by-kind groups into one entity list. */
async function readEntities(
  worktreeRoot: string,
  changeId: string,
): Promise<BrainEntity[]> {
  const brain = await readBrain(worktreeRoot, changeId);
  return brain.groups.flatMap((g) => g.items);
}

/** Entities of one kind. */
function ofKind(entities: BrainEntity[], kind: string): BrainEntity[] {
  return entities.filter((e) => e.kind === kind);
}

/**
 * The set of requirement ids covered by a PASSING testresult (its `verifies`
 * names them and its `outcome` is "pass").
 */
function verifiedRequirementIds(entities: BrainEntity[]): Set<string> {
  const verified = new Set<string>();
  for (const tr of ofKind(entities, "testresult")) {
    const d = detailOf(tr);
    if (normaliseOutcome(d.outcome) !== "pass") continue;
    for (const reqId of idList(d, "verifies")) verified.add(reqId);
  }
  return verified;
}

function buildDigest(entities: BrainEntity[]): ProvenanceDigest {
  const runs = ofKind(entities, "lifecyclerun");
  const requirements = ofKind(entities, "requirement");
  const verified = verifiedRequirementIds(entities);

  const did = runs.filter((r) => detailOf(r).outcome === "completed").length;
  const decided = ofKind(entities, "decision").length;
  const coveredVerified = requirements.filter((r) =>
    verified.has(r.id),
  ).length;

  // Flagged: every run's _gaps contribute to the count; the first gap's text is
  // the top gap; the first run carrying a _self_critique provides the snippet.
  let flaggedCount = 0;
  let topGap: string | null = null;
  let selfCritique: string | null = null;
  for (const run of runs) {
    const d = detailOf(run);
    const gaps = Array.isArray(d._gaps) ? d._gaps : [];
    for (const gap of gaps) {
      flaggedCount += 1;
      if (topGap === null && gap !== null && typeof gap === "object") {
        const g = gap as Detail;
        topGap = str(g, "claim") ?? str(g, "reason") ?? str(g, "text");
      }
    }
    if (selfCritique === null) selfCritique = str(d, "_self_critique");
  }

  return {
    did,
    covered: { verified: coveredVerified, total: requirements.length },
    decided,
    flagged: { count: flaggedCount, topGap, selfCritique },
  };
}

/** Map a `_step_runs` element → RunStep, tolerating missing fields. */
function toRunStep(raw: unknown): RunStep {
  const d: Detail = raw !== null && typeof raw === "object" ? (raw as Detail) : {};
  return {
    step: str(d, "step") ?? "",
    outcome: str(d, "outcome") ?? "",
    detail: str(d, "detail"),
    gap: str(d, "gap"),
    selfCritique: str(d, "self_critique") ?? str(d, "selfCritique"),
  };
}

function toRunLogEntry(run: BrainEntity): RunLogEntry {
  const d = detailOf(run);
  const stepRuns = Array.isArray(d._step_runs) ? d._step_runs : [];
  return {
    runId: run.id,
    workflow: str(d, "_workflow"),
    stepName: str(d, "step_name") ?? "",
    at: str(d, "at") ?? "",
    outcome: str(d, "outcome") ?? "",
    confidence: num(d, "confidence"),
    finalVerdict: str(d, "_final_verdict"),
    steps: stepRuns.map(toRunStep),
  };
}

/** Runs newest-first by `at` (ISO 8601; lexicographic compare is correct). */
function buildRunLog(entities: BrainEntity[]): RunLogEntry[] {
  return ofKind(entities, "lifecyclerun")
    .map(toRunLogEntry)
    .sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0));
}

function buildCoverage(entities: BrainEntity[]): CoverageColumn[] {
  const verified = verifiedRequirementIds(entities);

  const why: CoverageColumn = {
    axis: "why",
    items: ofKind(entities, "opportunity").map((o) => ({
      id: o.id,
      title: o.title,
    })),
  };

  const what: CoverageColumn = {
    axis: "what",
    items: ofKind(entities, "requirement").map((r) => ({
      id: r.id,
      title: r.title,
      verified: verified.has(r.id),
    })),
  };

  const how: CoverageColumn = {
    axis: "how",
    items: [
      ...ofKind(entities, "design").map((d) => ({
        id: d.id,
        title: d.title,
        kind: "design" as const,
      })),
      ...ofKind(entities, "decision").map((d) => ({
        id: d.id,
        title: d.title,
        kind: "decision" as const,
      })),
    ],
  };

  const tested: CoverageColumn = {
    axis: "tested",
    items: [
      ...ofKind(entities, "scenario").map((s) => ({
        id: s.id,
        title: s.title,
        outcome: normaliseOutcome(detailOf(s).outcome),
      })),
      ...ofKind(entities, "testresult").map((t) => ({
        id: t.id,
        title: t.title,
        outcome: normaliseOutcome(detailOf(t).outcome),
      })),
    ],
  };

  // The empty brain yields no columns at all (the empty-dashboard case).
  if (
    why.items.length === 0 &&
    what.items.length === 0 &&
    how.items.length === 0 &&
    tested.items.length === 0
  ) {
    return [];
  }
  return [why, what, how, tested];
}

/** The full Provenance read projection for a change. */
export async function readProvenance(
  worktreeRoot: string,
  changeId: string,
): Promise<ProvenanceView> {
  const entities = await readEntities(worktreeRoot, changeId);
  return {
    changeId,
    digest: buildDigest(entities),
    runLog: buildRunLog(entities),
    coverage: buildCoverage(entities),
  };
}

/**
 * The `?focus=<reqId>` variant — one requirement's resolved Why/How/Tested
 * trace. Returns null when the requirement id is not present (the route maps
 * that to a 404). Edge resolve stays server-side (ADR-011).
 */
export async function readFocusedTrace(
  worktreeRoot: string,
  changeId: string,
  requirementId: string,
): Promise<FocusedTrace | null> {
  const entities = await readEntities(worktreeRoot, changeId);
  return resolveFocusedTrace(entities, requirementId);
}
