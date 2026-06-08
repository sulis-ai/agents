---
id: WP-P01
title: "Agree the data shapes for diffs + provenance (contract)"
kind: contract
contract_type: data
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Create
group: expand
estimate: 3h
blast_radius: low
dependsOn: [WP-P00]
adr: [ADR-010, ADR-011]
verification:
  adapter: backend
  na: true
  justification: "Contract WP — defines shapes + stubs; conformance is verified by the producer/consumer WPs (P02/P03/P05/P06) against these examples (CF-07)."
estimated_token_cost: { input: "~20k", output: "~14k" }
status: pending
---

## Context

The contract-first seam for Slice 1 (CF-01/02/03/04). Defines, **before any
implementation**, the wire shapes + three-category error examples + happy/empty/
error stubs that WP-P02/P03 (files diffs) and WP-P05/P06 (provenance) build
against in parallel. Extends `contracts/openapi.yaml` + the runtime mirror in
`shared/api-types.ts` (CF-02 — the contract is the single source of truth).

## Contract (the shapes this WP pins)

**Files diff counts (extend `ChangedFile`):**
```ts
interface ChangedFile {
  path: string;
  status: "new" | "edited" | "removed";
  added: number | null;     // NEW — null = binary/unknown (numstat "-")
  removed: number | null;   // NEW
}
```

**Provenance (new shapes for `GET /api/changes/:id/provenance`):**
```ts
interface ProvenanceView {
  changeId: string;
  digest: ProvenanceDigest;       // the dashboard front door
  runLog: RunLogEntry[];          // lens A
  coverage: CoverageColumn[];     // lens B (Why/What/How/Tested)
}
interface ProvenanceDigest {
  did: number;                    // completed runs
  covered: { verified: number; total: number };  // e.g. 1 of 49
  decided: number;                // decision entities
  flagged: { count: number; topGap: string | null; selfCritique: string | null };
}
interface RunLogEntry {
  runId: string; workflow: string | null; stepName: string;
  at: string; outcome: string; confidence: number | null;
  finalVerdict: string | null;
  steps: RunStep[];               // from _step_runs
}
interface RunStep { step: string; outcome: string; detail: string | null; gap: string | null; selfCritique: string | null }
type CoverageColumn =
  | { axis: "why"; items: { id: string; title: string }[] }
  | { axis: "what"; items: { id: string; title: string; verified: boolean }[] }
  | { axis: "how"; items: { id: string; title: string; kind: "design" | "decision" }[] }
  | { axis: "tested"; items: { id: string; title: string; outcome: "pass" | "skip" | "fail" }[] };
interface FocusedTrace {           // the single per-requirement trace (lens B)
  requirementId: string;
  why: { id: string; title: string }[];
  how: { id: string; title: string; kind: "design" | "decision" }[];
  tested: { id: string; title: string; outcome: "pass" | "skip" | "fail" }[];
}
```
The focused trace is fetched per requirement (a `?focus=<reqId>` variant on the
provenance endpoint, OR resolved client-side from the returned `coverage` —
pinned here as the `?focus=` server variant so the edge resolve stays server-side).

**Errors (three categories, CF-03):** `NOT_FOUND` (Expected, unknown change),
the existing typed envelope. Empty cases: `digest` all-zero + empty lenses for a
change with no brain; `added/removed: null` for a binary file.

## Stubs (CF-04 — happy + empty + error, as JSON examples in openapi.yaml)
- changed-with-counts (happy); binary-file (null counts); clean change (`[]`).
- provenance happy (1-of-49 covered + a real flagged gap); empty-brain dashboard.
- `NOT_FOUND` for an unknown change id.

## Shared artifacts (CF-11)
- Endpoint paths pinned: `GET /api/changes/:id/changed` (extended),
  `GET /api/changes/:id/provenance` (new, `?focus=` variant).
- `shared/api-types.ts` is the **one** runtime mirror; producer + consumer WPs
  import these types verbatim, never re-declare.

## Definition of Done

### Red
- [ ] `openapi.yaml` + `shared/api-types.ts` do not yet carry these shapes; a
      type-check referencing `ChangedFile.added` / `ProvenanceView` fails.

### Green
- [ ] `openapi.yaml` carries every shape + the happy/empty/error stubs (CF-04).
- [ ] `shared/api-types.ts` mirrors them verbatim (CF-02); `tsc` passes.
- [ ] The OpenAPI doc validates (existing lint).

### Blue
- [ ] No shape declared inline per-endpoint — all are named, reusable schemas (CF-02).
- [ ] Error + empty examples present, not happy-path-only (CF-04).
- [ ] The `?focus=` decision is recorded in the openapi description (edge resolve
      stays server-side, ADR-011).
