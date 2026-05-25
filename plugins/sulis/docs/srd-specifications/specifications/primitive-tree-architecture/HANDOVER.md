# Handover Brief: Primitive Tree Architecture

**Version:** 1.0.0
**Date:** 2026-03-16

---

## Summary

This handover provides everything needed to implement the primitive tree feature in the SRD
plugin. The feature adapts a proven pattern from the tria project (business model decomposition)
for software architecture decomposition. The core deliverable is a structured DAG of
architectural primitives that drives facilitation question selection, tracks specification
completeness, and ships as a first-class execution artifact.

The specification is strong across all areas. Three minor gaps remain (see Completeness
Report) — none block implementation.

---

## Artifact Reading Order

Read the specification artifacts in this order. Each document builds on the ones before it.

| Order | Artifact | Why Read This | Time |
|-------|----------|--------------|------|
| 1 | [GLOSSARY.md](GLOSSARY.md) | Domain terms. Prevents misinterpretation of key concepts (especially: domain primitive vs. SA&D primitive, health status vs. implementation status, facilitation phase vs. implementation phase). | 5 min |
| 2 | [SRD.md](SRD.md) Section 7 (Node Type Schema) | The core data model. Seven node types with properties, attack patterns, and invalidation signals. This is what the tree contains. | 15 min |
| 3 | [SRD.md](SRD.md) Sections 1-6, 8-10 | Full specification: features, functional requirements, business rules, evidence grading, traceability. | 25 min |
| 4 | [diagrams/state-diagrams.md](diagrams/state-diagrams.md) | Node health status lifecycle (ST-01) and facilitation phase progression (ST-02). These two state machines govern the entire system's behaviour. | 10 min |
| 5 | [diagrams/process-flows.md](diagrams/process-flows.md) | Four process flows: tree synthesis, OODA spiral, tree update, completeness verification. The "how it works" view. | 10 min |
| 6 | [diagrams/data-flows.md](diagrams/data-flows.md) | Artifact pipeline and facilitation loop. Where data comes from and where it goes. | 5 min |
| 7 | [diagrams/sequence-diagrams.md](diagrams/sequence-diagrams.md) | End-to-end session and single-turn detail. How components interact over time. | 5 min |
| 8 | [diagrams/use-cases.md](diagrams/use-cases.md) | All 8 use cases with flows. The "who does what" reference. | 10 min |
| 9 | [NFR.md](NFR.md) | Constraints: scale limits, quality gates, data integrity rules. | 5 min |
| 10 | [COMPLETENESS_REPORT.md](COMPLETENESS_REPORT.md) | Known gaps and their severity. | 3 min |

---

## Key Decisions

Decisions made during facilitation that shaped the specification. These are settled — do not
re-litigate without new evidence.

| Decision | Why This Way | Alternatives Considered |
|----------|-------------|------------------------|
| **Adapt tria's pattern, not design from scratch** | Tria has a mature, tested PRIMITIVE_TREE implementation. The structural pattern (DAG, typed dependencies, health statuses, extensible types, attack patterns) is proven. Only the domain vocabulary changes. | Design from scratch — rejected because the structural problems are identical and already solved. |
| **7 node types from C4 + DDD + structured analysis composite** | No single framework covers software architecture primitives at the right granularity. C4 focuses on zoom levels, DDD on domain patterns, structured analysis on data/process. The composite (domain-entity, action, integration, data-store, state-machine, policy, event) covers the domain with open extensibility for gaps. | C4 alone (too zoom-oriented), DDD alone (too pattern-oriented), structured analysis alone (too data/process-oriented). |
| **Facilitation phases, not implementation priority** | The tree's phase property governs when nodes become relevant during requirements specification, not when they should be built. Implementation ordering is a well-understood separate concern that does not need encoding in the tree. | Implementation phases — rejected because delivery ordering is downstream of specification and changes independently. |
| **Evidence/interpretation separation (index + tree as separate files)** | CODEBASE_INDEX.json captures facts. PRIMITIVE_TREE.jsonld captures interpretation. Keeping them separate makes both auditable and debuggable. If the tree seems wrong, you can check what evidence it was based on. | Single merged file — rejected because it conflates evidence with interpretation and makes debugging harder. |
| **OODA spiral with composite scoring formula** | Deterministic question selection prevents the agent from wandering. The formula (fan_out * 3 + invalidations * 2 + phase * 1 + confidence * 1) prioritises architecturally significant nodes, nodes with known problems, and nodes matching the current facilitation phase. | Domain-rotation (current approach) — not replaced but restructured; the six-domain lens still applies as the analytical framework, but the tree provides targeting within it. |
| **Exec summary, not raw tree** | Users should see progress and gaps, not JSON. The exec summary groups by status, shows counts, and ends with the next target. Tree internals (dependencies, phases, scores) are the agent's working model, not the user's interface. | Expose tree structure — rejected because it adds cognitive load without improving facilitation quality. |

---

## Assumptions

| Assumption | Validation Method | Impact if False |
|------------|-------------------|----------------|
| A-01: LLM domain knowledge produces meaningful decompositions for common software domains | Test with 5+ project types: e-commerce, SaaS API, mobile app, data pipeline, microservice architecture | If false: initial trees will be thin, requiring more facilitation turns to build up. Graceful degradation — no specification change needed. |
| A-02: 7 node types cover the software architecture domain | Monitor custom type usage across 20+ facilitation sessions | If false: promote frequent custom types to standard (extensibility model handles this). |
| A-03: Fan-out ≤ 7 and depth ≤ 5 constraints are sufficient for cognitive manageability | Monitor during facilitation — does the agent struggle with tree navigation within context window? | If false: tighten constraints. Easy to adjust without structural changes. |
| A-04: Users engage meaningfully with exec summary format | User feedback during sessions | If false: adjust rendering. The underlying tree mechanics are independent of presentation format. |

---

## Known Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Context window pressure from large trees (> 100 nodes) | Medium | The agent may struggle to hold the full tree in context alongside the conversation | NFR-S01 sets advisory limit at 200 nodes. Bounded context partitioning at 40 leaves reduces per-context working set. Monitor context utilisation during implementation. |
| Over-reliance on LLM inference for greenfield projects | Medium | Without codebase evidence, initial trees may not match the user's mental model | All greenfield nodes start as "inferred" and require user confirmation (FAIR evidence) to validate. The tree is explicitly a hypothesis to be refined. |
| conflicts-with dependency underspecified | Low | Agent may not handle conflict detection gracefully during facilitation | COMPLETENESS_REPORT.md gap #3 recommends: surface at reflection checkpoint, let user decide. Implement this as the default. |
| Scoring formula weights may need tuning | Medium | If fan-out weight (3) is too dominant, the agent may always chase high-dependency nodes even when other nodes are more urgent | Weights are parameters, not hardcoded logic. Adjust based on facilitation quality observations. Start with specified weights and tune. |

---

## Recommended Implementation Sequence

Based on dependency analysis of the features:

**Phase 1: Schema and synthesis (F-01)**
Build the PRIMITIVE_TREE.jsonld schema (Section 7 of SRD.md) and the tree synthesis process
(PF-01). This is the foundation — everything else depends on a tree existing.

Deliverables:
- JSON-LD schema definition with all 7 node types and common properties
- Brownfield synthesis from CODEBASE_INDEX.json
- Greenfield synthesis from user description
- Scale constraint enforcement
- Persistence to disk

**Phase 2: OODA integration (F-02, F-03)**
Wire the tree into the facilitation loop: question selection (PF-02) and tree update from
user input (PF-03). This is where the tree starts driving facilitation.

Deliverables:
- Composite scoring function
- Topological ordering
- Attack-pattern-framed question generation
- Health status transitions from user answers
- Tree persistence after every mutation

**Phase 3: User-facing features (F-04, F-05)**
Add exec summary rendering (UC-05) and completeness verification (PF-04). These make the
tree visible to the user and verifiable.

Deliverables:
- Exec summary renderer (grouped by status, max 20 nodes)
- Completeness verification against attack patterns and invalidation signals
- COMPLETENESS_REPORT.md generation

**Phase 4: Artifact and handover integration (F-06, F-07)**
Wire the tree into artifact generation as a structural checklist and into the handover as a
first-class deliverable.

Deliverables:
- Artifact generation checklist from artifactAffinity
- Cross-reference verification (every validated node in at least one artifact)
- HANDOVER.md tree section with new-vs-existing summary

---

## Tria Pattern Reference

The following tria artifacts are the source patterns. The implementation should read these
for structural guidance — the mechanics transfer, only the domain vocabulary changes.

| Tria Artifact | What Transfers | What Changes |
|--------------|----------------|-------------|
| `PRIMITIVE_TREE_SCHEMA.jsonld` | DAG structure, dependency types, health statuses, extensibility model, custom type template | Node types (Osterwalder business types -> software architecture types), phases (business lifecycle -> facilitation stages), commonProperties (functionAffinity -> artifactAffinity, contentProduction -> source) |
| `primitive-testing/OUTCOME.md` | Health status transition mechanics, evidence grading tiers, topological ordering, dual-path routing concept | Evidence source (desk research -> facilitation conversation + codebase), testing mechanism (adversarial research -> facilitation questions framed by attack patterns) |
| `product-capability-decomposition/OUTCOME.md` | Structural concept of bridging from primitives to buildable outputs | Not directly adapted — the SRD's artifact generation serves this role, using artifactAffinity instead of capability mapping |
