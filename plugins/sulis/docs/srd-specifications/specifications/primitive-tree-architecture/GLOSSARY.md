# Glossary: Primitive Tree Architecture

**Version:** 1.0.0
**Date:** 2026-03-16

---

## Summary

Domain terms used throughout the Primitive Tree Architecture specification. All artifacts
in this specification folder use these terms as defined here. When a term appears in SRD.md,
NFR.md, or any diagram, its meaning is exactly as stated below.

---

## Terms

| Term | Definition | Context | First Appeared |
|------|-----------|---------|----------------|
| Architectural primitive | A domain-specific building block at the level of abstraction that drives design decisions. The granularity test: "Would an architect put this on a whiteboard?" Examples: a domain entity, an action, an integration point. | Core concept — the leaf nodes of the primitive tree | Turn 14 |
| Artifact affinity | A property of each tree node indicating which SRD artifact types (use-case, sequence-diagram, process-flow, state-diagram, data-flow, nfr, business-rule) the node feeds into. Every node has at least one affinity. | Node common property — drives artifact generation completeness checking | Convergent spec |
| Attack pattern | An adversarial question that tests whether a node's specification is complete, consistent, and buildable. Defined per node type. Used by the agent to frame facilitation questions. Adapted from tria's business model attack patterns. | Node type metadata — drives question formulation in the OODA spiral | Turn 16 (tria context) |
| Bounded context | A scoping mechanism for large systems. When a tree exceeds 40 leaf nodes, the agent partitions it into bounded contexts as intermediate grouping nodes. Borrowed from DDD but used directionally at specification stage, not as a strict implementation boundary. | Scale management — prevents trees from becoming unmanageable | Turn 15 |
| Codebase index | A flat, evidence-based inventory of a target project's technology stack, services, data models, integrations, and routes. Produced by the codebase-mapping skill. Stored as CODEBASE_INDEX.json. Represents facts about what exists, not interpretation. | Input to tree synthesis — the evidence layer | Turn 6 |
| Common properties | Properties that apply to all node types regardless of type: phase, artifactAffinity, source. Adapted from tria's commonProperties (phase, functionAffinity, contentProduction). | Schema structure — ensures every node carries facilitation metadata | Convergent spec |
| DAG | Directed acyclic graph. The primitive tree's actual structure — not a strict tree because typed dependencies (depends-on, enables, conflicts-with) create cross-links between nodes. No cycles permitted. | Tree structure — inherited from tria's PRIMITIVE_TREE_SCHEMA.jsonld | Turn 16 |
| Dependency type | A typed edge between two nodes in the tree. Three types: depends-on (A requires B), enables (A makes B possible but not required), conflicts-with (A and B cannot both succeed). Propagation rules differ by type. Transferred directly from tria. | Tree structure — governs topological ordering and failure propagation | Turn 16 |
| Domain primitive | A building block specific to the target project being specified. Contrasted with SA&D primitives, which are the agent's own analytical methodology. Domain primitives are what the tree decomposes; SA&D primitives are how the agent analyses. | Fundamental distinction — prevents confusing the agent's methodology with the target project's structure | Turn 1 |
| Evidence grading | A three-tier assessment of how reliable the evidence for a node is. STRONG: codebase evidence (node maps to existing code). FAIR: user confirmation during facilitation. WEAK: agent inference from domain knowledge. Parallels tria's WEAK/FAIR/STRONG research evidence grading. | Health status transitions — determines what evidence can validate vs. only invalidate | Convergent spec |
| Exec summary | The human-readable rendering of the tree that the agent presents to the user during facilitation. Groups nodes by health status (validated, in progress, not yet explored, flagged) with counts and one-line descriptions. Never raw JSON. | User-facing presentation — the only way the user interacts with tree state | Turn 10-12 |
| Facilitation phase | An ordered stage of requirements specification that determines when a node first becomes the focus of facilitation. Five phases: discover, define, connect, constrain, verify. Distinct from implementation priority. | Node common property — governs question ordering in the OODA spiral | Turn 19 |
| Fan-out | The number of child nodes (or outgoing depends-on edges) from a single node. Constrained to 7 or fewer per node, following Miller's 7 plus-or-minus 2 and structured analysis conventions. | Scale management — prevents cognitive overload in tree sections | Turn 15 |
| Health status | The specification completeness state of a tree node. Five states: untested, testing, validated, failed, accepted-as-risk. Transferred directly from tria. Transition triggers adapted for requirements context (facilitation conversation and codebase evidence vs. desk research). | Node lifecycle — the core state machine driving facilitation progress | Turn 16 |
| Invalidation signal | A concrete indicator that a node's specification has a gap or structural problem. Defined per node type. When matched during facilitation, triggers health_status transition to failed (or flags for resolution). Adapted from tria's kill_signals. | Node type metadata — the "what's wrong" counterpart to attack patterns' "what to check" | Turn 16 (tria context) |
| Node type | The classification of an architectural building block. Seven standard types: domain-entity, action, integration, data-store, state-machine, policy, event. Plus open vocabulary for custom types following tria's extensibility model. | Tree schema — determines type-specific properties, attack patterns, and invalidation signals | Turn 17-18 |
| OODA spiral | Observe-Orient-Decide-Act applied iteratively to tree gaps. Each pass examines the tree, prioritises nodes by composite score (dependency fan-out, active invalidations, phase alignment, source confidence), selects the highest-priority gap, and formulates a facilitation question. Spiral, not loop — each pass tightens understanding. | Facilitation engine — how the tree drives question selection | Turn 3 |
| Primitive tree | A persisted, structured DAG of architectural primitives for a target project. Produced by synthesising LLM domain knowledge with codebase evidence (brownfield) or user description (greenfield). Lives at `.specifications/{name}/PRIMITIVE_TREE.jsonld`. Evolves during facilitation as a living artifact. | Core artifact — the central data structure this specification defines | Turn 1 |
| SA&D primitives | The agent's own analytical methodology primitives: structural (S1-S7: Actor, Use Case, Business Rule, Data Entity, State Lifecycle, Integration Boundary, Process Flow) and analytical (A1-A7: Precondition, Postcondition, Exception Path, Alternate Path, Trigger, Constraint, Acceptance Criterion). These are how the agent thinks, not what the tree contains. | Methodology layer — governs coaching annotations and analytical quality, separate from domain primitives | Turn 1 |
| Source | A node property recording where evidence for the node came from. Three values: "codebase" (discovered in existing code), "inferred" (agent's domain knowledge), "user" (explicitly specified or confirmed during facilitation). Maps to evidence grading. | Node property — provenance tracking for evidence quality assessment | Convergent spec |
| Tree synthesis | The process of creating the initial PRIMITIVE_TREE.jsonld from inputs. Six steps: seed root, first-pass decomposition, wire dependencies, apply scale constraints, assign facilitation phases, persist. Different paths for brownfield (codebase index + LLM knowledge) and greenfield (user description + LLM knowledge). | Process — how the tree comes into existence | Convergent spec |

---

## Synonyms and Disambiguation

| Preferred Term | Also Known As | NOT the Same As |
|---------------|---------------|-----------------|
| Architectural primitive | Domain primitive, building block, domain building block | SA&D primitive (those are the agent's methodology, not the target project's structure) |
| Primitive tree | Tree, decomposition tree | Codebase index (that's the flat evidence layer, not the structured interpretation) |
| Health status | Node status, specification status | Implementation status (health status tracks specification completeness, not whether code exists) |
| Attack pattern | Adversarial question, specification test | Invalidation signal (attack patterns are questions to ask; invalidation signals are indicators that something is wrong) |
| Facilitation phase | Specification phase, tree phase | Implementation phase, delivery phase (facilitation phases govern when nodes are explored during requirements gathering, not when they're built) |
| Evidence grading | Source confidence, evidence quality | Health status (evidence grading assesses the reliability of information; health status tracks the node's specification completeness) |
| OODA spiral | OODA loop (avoided — "spiral" emphasises iterative deepening) | Six-domain exploration model (OODA spiral provides targeting within the existing six-domain analytical lens, does not replace it) |
| Bounded context | Context boundary, module boundary | Microservice (bounded contexts at specification stage are analytical groupings, not deployment decisions) |
