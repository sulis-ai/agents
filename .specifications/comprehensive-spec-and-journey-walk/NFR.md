# Non-Functional Requirements: Comprehensive Spec & Two-Surface Journey Walk

**Change:** CH-CQRWWR · primitive `harden` · slug `comprehensive-spec-and-journey-walk`

## Summary

These NFRs constrain the methodology's non-functional properties: depth
classification must stay deterministic, the always-comprehensive document must
add only bounded cost, the gates must be fast, and the tool-surface walk must use
real round-trips. Every target is measurable.

---

## Performance

| ID | Requirement | Target | Verification |
|----|-------------|--------|--------------|
| NFR-01 | Depth classification MUST be fast and deterministic. | `classify_depth` returns in < 5 ms; identical inputs always yield identical output (pure function, no I/O). | Unit test: 1000 calls < 5 s total; same input ⇒ same `DepthDecision` across runs. |
| NFR-02 | The always-comprehensive document MUST add bounded token cost over the legacy thin SPEC. | Producing the full section set at lite depth adds ≤ 1.6× the token cost of the legacy lite SPEC for an equivalent change (the structure scaffold + section headers + n/a justifications, not full interview-derived detail). | Measure produced-doc token count for a fixture change at lite depth vs the legacy SPEC baseline. |
| NFR-03 | The coverage gates MUST be fast enough to run on every ship without friction. | UC-flow-coverage + scenario-required + journey-coverage gates complete in < 3 s combined for a change with ≤ 20 use-case flows. | Time the three gates on a fixture change; assert < 3 s. |
| NFR-S01 | The two-surface journey walk MUST not unboundedly inflate design time. | Walking both surfaces for a journey of ≤ 15 hops adds ≤ 1 agent turn over the single-surface walk. | Compare walk turn count single-surface vs two-surface on a fixture. |

## Determinism & Reproducibility

| ID | Requirement | Target | Verification |
|----|-------------|--------|--------------|
| NFR-04 | Hop classification (EXISTS/planned-WP/GAP) MUST be reproducible from the same codebase + TDD state. | Re-running the walk on an unchanged worktree yields an identical classification table. | Run the walk twice on a frozen fixture; diff the tables ⇒ empty. |
| NFR-05 | Scenario derivation MUST be stable: re-authoring with the same `seed` yields the same scenario IDs. | Same `(slug, scenario-name)` seed ⇒ same `dna:scenario:` id. | Re-emit scenarios with identical seeds; assert id stability (reuses existing `seed` contract). |

## Security

| ID | Requirement | Target | Verification |
|----|-------------|--------|--------------|
| NFR-S02 | A tool-surface hop MUST NOT be classifiable EXISTS without its ServiceSpec binding cited. | 0 hops classified EXISTS with a missing binding citation. | Fixture: handler present, binding absent ⇒ classifier returns GAP. |
| NFR-S03 | A tool scenario MUST NOT report green without a real driven round-trip. | 0 green tool scenarios without a deposited passing TestResult from a real drive (observed) or an explicit attestation. | Drive a tool scenario; green requires a passing TestResult on record (reuses #98 evidence). |
| NFR-S04 | The coverage gate MUST fail closed: any uncovered flow with no out-of-scope record ⇒ blocking `gaps`. | Default-deny — absence of coverage is a gap, never silently passed. | Fixture with one uncovered flow ⇒ verdict `gaps`, non-zero exit. |

## Reliability

| ID | Requirement | Target | Verification |
|----|-------------|--------|--------------|
| NFR-R01 | The always-comprehensive document MUST degrade detail, never section existence, under token pressure. | Under a constrained budget, all mandatory sections remain present (possibly with `n/a — <justification>`); none are dropped. | Fixture with a tight budget ⇒ section set complete, detail reduced. |
| NFR-R02 | An undrivable tool scenario MUST be recorded as a deferred infrastructure need, never silently skipped. | 0 silently-dropped tool scenarios; each undrivable one has a `### Infrastructure needs surfaced (deferred)` entry. | Fixture tool scenario with no sandbox ⇒ deferred entry present. |

## Data / Integrity

| ID | Requirement | Target | Verification |
|----|-------------|--------|--------------|
| NFR-D01 | The scenario set + coverage truth MUST be sourced from the brain, not an agent claim. | Coverage verdict derives from `find_scenarios_for_journey` + `find_passing_testresults_for_scenario`; no agent-asserted coverage. | Code inspection + a driven check that the verdict changes only when brain state changes. |
| NFR-D02 | Both journey-walk tables MUST be persisted in the design document (`## Journey Walk`), not transient. | The produced document contains a UI table AND a tool table, each with every hop classified. | Parse the produced `## Journey Walk` section; assert two tables, all hops classified. |

---

## Traceability

| NFR | Supports FR | Supports UC |
|-----|-------------|-------------|
| NFR-01 | FR-03 | UC-02 |
| NFR-02 | FR-01, FR-11 | UC-01 |
| NFR-03 | FR-12, FR-13 | UC-06 |
| NFR-04 | FR-07, FR-08 | UC-03, UC-04 |
| NFR-05 | FR-10 | UC-05 |
| NFR-S01 | FR-08 | UC-04 |
| NFR-S02 | FR-09 | UC-04 |
| NFR-S03 | FR-10, FR-14 | UC-05 |
| NFR-S04 | FR-12 | UC-06 |
| NFR-R01 | FR-01 | UC-01 |
| NFR-R02 | FR-10 | UC-05 |
| NFR-D01 | FR-12, FR-14 | UC-06 |
| NFR-D02 | FR-07, FR-08 | UC-03, UC-04 |
