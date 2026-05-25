# Requirements Completeness Assessment

**Specification:** primitive-tree-architecture
**Date:** 2026-03-16
**Passes completed:** 1

**VERDICT:** GAPS_FOUND

---

## Summary

The specification is strong across core capabilities (tree synthesis, OODA spiral, health
status lifecycle, node type schema) and supporting concerns (exec summary, completeness
verification, artifact generation integration). Three gaps remain that require decisions
during implementation rather than further facilitation.

---

## Perspective 1: Requirement Traceability

[COMPLETE] G-01 (Structured decomposition drives facilitation) -> UC-01, UC-02, UC-03 -> PF-01, PF-02, DF-01
[COMPLETE] G-02 (Tree evolves from hypothesis to ground truth) -> UC-04 -> PF-03, ST-01
[COMPLETE] G-03 (User sees progress, not internals) -> UC-05 -> DF-02
[COMPLETE] G-04 (Completeness verified before artifact generation) -> UC-06 -> PF-04
[COMPLETE] G-05 (Artifacts structurally complete) -> UC-07 -> DF-01
[COMPLETE] G-06 (Tree useful for execution team) -> UC-08 -> HANDOVER.md reference

[COMPLETE] UC-01 -> PF-01 process flow + DF-01 data flow
[COMPLETE] UC-02 -> PF-01 process flow (greenfield branch)
[COMPLETE] UC-03 -> PF-02 process flow + SD-02 sequence diagram
[COMPLETE] UC-04 -> PF-03 process flow + ST-01 state diagram
[COMPLETE] UC-05 -> Functional requirements FR-24 through FR-29
[COMPLETE] UC-06 -> PF-04 process flow
[COMPLETE] UC-07 -> DF-01 data flow + FR-36 through FR-39
[COMPLETE] UC-08 -> FR-40 through FR-43

[COMPLETE] ST-01 (Health status lifecycle) -> Fully specified with 5 states, 10 transitions, 5 invalid transitions
[COMPLETE] ST-02 (Facilitation phase progression) -> Fully specified with 5 states, 4 transitions

---

## Perspective 2: Integration Completeness

This system has one integration boundary: the interface between the primitive tree and the
existing codebase-mapping skill (CODEBASE_INDEX.json).

[COMPLETE] CODEBASE_INDEX.json integration:
- Protocol: File-based (JSON on disk) — specified
- Format: JSON — specified (existing format, unchanged)
- Error handling: Malformed index falls back to greenfield path (EF-01 in UC-01) — specified
- Sync model: Synchronous file read — specified
- No authentication required (local file system)

No other external system integrations exist. The primitive tree is an internal feature of the
SRD agent, not a service that communicates with external systems.

---

## Perspective 3: NFR Coverage

[COMPLETE] Tree Quality — NFR-Q01 through NFR-Q05: fan-out, depth, bounded context, acyclicity, coverage (all measurable)
[COMPLETE] Facilitation Performance — NFR-F01 through NFR-F06: summary size, checkpoint frequency, question count, verification passes, circuit breakers (all measurable)
[COMPLETE] Scale Limits — NFR-S01, NFR-S02: max nodes, batch size (measurable)
[COMPLETE] Data Integrity — NFR-D01 through NFR-D05: persistence, separation, continuity, provenance, consistency (all measurable)
[COMPLETE] Schema Compliance — NFR-SC01 through NFR-SC04: JSON-LD, node types, dependency types, required properties (all measurable)

---

## Content Quality

[COMPLETE] SRD.md — summary section present and self-sufficient; stable identifiers (FR-xx, UC-xx, BR-xx) throughout; sentence rhythm varied
[COMPLETE] NFR.md — summary present; all requirements have measurable targets
[COMPLETE] GLOSSARY.md — summary present; terms precisely defined with disambiguation
[COMPLETE] All diagrams — Mermaid syntax valid; node counts within limits; meaningful names used

---

## Remaining Gaps

1. **[IMPLEMENTATION_DETAIL] JSON-LD @context definition** — The SRD specifies JSON-LD format
   and references tria's @context as precedent, but does not define the exact @context URI or
   namespace for the SRD primitive tree schema. This is an implementation decision, not a
   requirements gap — the schema structure and semantics are fully specified.
   **Severity:** Low. **Resolution:** Define @context during implementation, following tria's
   pattern (`https://sulis.co/ontology/primitive-tree/` adapted for SRD namespace).

2. **[IMPLEMENTATION_DETAIL] LLM domain knowledge coverage boundaries** — The SRD assumes LLM
   domain knowledge is sufficient for initial decomposition (Assumption A-01). The validation
   method is specified (test with 5+ project types), but the fallback behaviour for domains
   the LLM does not recognise well is only partially specified (minimal skeleton + facilitation
   fills gaps). Edge case: what happens with highly specialised domains (e.g., avionics,
   medical devices) where the LLM's architecture knowledge may be thin.
   **Severity:** Low. **Resolution:** The graceful degradation path (thin tree, facilitation
   fills gaps) handles this — it just produces a less useful initial tree. No specification
   change needed; monitor during early usage.

3. **[OPEN_QUESTION] Conflict resolution between nodes** — The conflicts-with dependency type
   is specified (propagation: "Validation of one may kill the other"), but the exact agent
   behaviour when a conflict is detected during facilitation is not specified step-by-step.
   Should the agent surface conflicts to the user immediately? Wait for a reflection
   checkpoint? Resolve silently if one node has stronger evidence?
   **Severity:** Medium. **Resolution:** Recommended default: surface at next reflection
   checkpoint with both nodes presented side by side. The user decides which to keep. Document
   this as a process rule during implementation.
