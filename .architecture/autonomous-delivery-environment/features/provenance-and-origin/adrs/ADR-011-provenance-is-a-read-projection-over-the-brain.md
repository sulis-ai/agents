# ADR-011 — Provenance is a read projection over the existing brain, not a new store

- **Status:** accepted
- **Date:** 2026-06-05
- **Change:** CH-01KT50 · feature: provenance-and-origin
- **Deciders:** SEA

## Decision

The **Provenance view** (digest dashboard + run-log lens + coverage-map lens)
is a **read projection computed at read time over the existing brain tree**
(`.brain/instances/<domain>/<kind>/<ULID>.jsonld`), served by **one new endpoint
`GET /api/changes/:id/provenance`**. It composes the existing `readBrain` read
plus a pure edge resolver (`provenanceEdges.ts`) over each entity's `detail`.
No new persistent store, no new write, no precomputed checkpoint.

- **Digest tiles** (did / covered / decided / flagged) are counts + a real
  surfaced gap: *did* = completed `lifecyclerun`s; *covered* = requirements with
  a verifying scenario/testresult; *decided* = `decision` entities; *flagged* =
  the real `_gaps` / `_self_critique` / non-`pass` `_final_verdict` from the runs.
- **Run-log** = `lifecyclerun`s ordered by `at`, each expanding to its
  `_step_runs` with the step's produced/gap/self-critique detail.
- **Coverage-map** = Why (opportunity) → What (requirement) → How (design +
  decision) → Tested (scenario/testresult), with a **single focused trace** per
  selected requirement resolved from `detail` edges (never an all-edges blob).

## Why this is the convention

The brain *is* the system of record; the cockpit's discipline (parent §2.1) is
to **compose existing reads, not add stores**. The `lifecyclerun` entity already
carries exactly the fields the design needs (`outcome`, `confidence`,
`_step_runs`, `_gaps`, `_self_critique`, `_final_verdict`, `at`) — verified
against real instances. A projection over the source of truth can never drift
from it.

## Alternatives considered

- **A precomputed provenance snapshot/store (rejected).** Introduces a second
  source of truth that can drift from the brain; violates NFR-DATA-01 (no new
  store). The projection is cheap (read + group + resolve).
- **Three separate endpoints (dashboard / run-log / coverage) (rejected).**
  The three lenses read the **same** entity set; one endpoint returning one
  `ProvenanceView` (with the three lens projections) avoids three round-trips
  and three fail-soft code paths. The client picks the lens (C → B → A,
  brainstorm).
- **Keep the flat group-by-kind `BrainView` and bolt the dashboard on top
  (rejected).** The brainstorm's chosen direction replaces the front door
  (digest-first); keeping the flat view as the entry point fights the approved
  design. See ADR-014 for the front-door replacement.

## Consequences

- One new GET endpoint + one new lib (`readProvenance.ts`) + one edge resolver;
  the `…/brain` endpoint **stays** (the projection composes it).
- Fail-soft like the brain read: malformed run skipped, absent brain → empty
  dashboard state (the design renders it).
