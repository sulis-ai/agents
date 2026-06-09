# ADR-001 — The seam-close gate's trigger unit is the seam, not the Scenario

- **Status:** accepted
- **Change:** CH-01KTP7 (`feat` · `seam-dod-gate`)
- **Date:** 2026-06-09

## Context

The handoff flagged this as the **#1 resolve-first uncertainty**: *do enumerated
Scenarios tile the seam set 1:1?* If each seam were the last hop of exactly one
Scenario, the gate could key off a Scenario id. If not, the gate must key off
the contract-WP seam boundary and drive *the relevant Scenarios* at that
boundary.

## Decision

**The gate's trigger unit is the seam (the contract-WP boundary), not the
Scenario.** At a closing seam the gate drives the Scenarios that verify the
requirements the seam's two sides implement.

## Why (the recommendation, lead position)

Examining the code and this repo's `*.scenarios.jsonld` confirms Scenarios key
to **requirements** (`verifies: [dna:requirement:…]`) and to a **journey**
(`journey: dna:workflow:…`) — they do **not** carry a seam id and do **not**
tile seams 1:1. A single Scenario typically verifies several requirements that
may span more than one seam; a single seam may be covered by several Scenarios
or by none. There is no reliable 1:1 mapping to key a per-seam trigger off a
Scenario id.

The seam, by contrast, **is** structurally identifiable from the build loop's
own state: `kind: contract` + the `dependsOn` graph + per-WP `status` in
INDEX.md (CF-05/CF-07). The build loop already knows when a WP reaches `done`;
"did a seam close?" is a pure read over that state. So the seam is the unit the
loop can actually detect and fire on.

The seam→Scenario hop then goes **through requirements** (ADR-004):
seam → requirements it implements → `find_scenarios_verifying(req)` → drive.

## Alternatives considered

- **Gate unit = the Scenario id** (the handoff's branch-1). **Rejected:**
  Scenarios don't tile seams 1:1 (verified in code), so a Scenario-keyed trigger
  can't reliably fire *per seam* — the exact thing the gate must do. It would
  either miss seams (no Scenario ends at them) or fire redundantly (one Scenario
  spans several seams).

## Consequences

- The gate keys off the CONTRACT_FIRST seam boundary, detected from INDEX.
- A seam with no covering Scenario is a real, detectable state → it must have a
  defined verdict (blocked — ADR-005), rather than being invisible as it would
  be under a Scenario-keyed trigger.
- The seam→Scenario resolution needs a requirement bridge (ADR-004), because
  WPs don't carry requirement ids directly.
