# Non-Functional Requirements: Primitive Tree Architecture

**Version:** 1.0.0
**Date:** 2026-03-16

---

## Summary

Non-functional requirements for the primitive tree system. Since this system operates as an
LLM agent feature (not a deployed service), traditional NFR categories like "availability"
and "security" are reframed for the agent context. The primary concerns are: tree quality
constraints (structural integrity), facilitation performance (cognitive load management),
scale limits (tree size boundaries), and data integrity (persistence and consistency).

---

## Tree Quality Constraints

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-Q01 | Fan-out constraint: no node may have more than 7 children | Children per node | ≤ 7 | Validate after every tree mutation (synthesis, update, restructure) |
| NFR-Q02 | Depth constraint: tree must not exceed 5 levels from root to deepest leaf | Maximum path length | ≤ 5 | Validate after every tree mutation |
| NFR-Q03 | Bounded context trigger: trees with more than 40 leaf nodes must be partitioned | Leaf node count | Partition triggered at > 40 | Count leaves after synthesis and after new nodes created |
| NFR-Q04 | Acyclicity: the dependency graph must remain a DAG (no cycles) | Cycle detection | 0 cycles | Topological sort validation after every dependency edge added |
| NFR-Q05 | Completeness coverage: every validated node must appear in at least one SRD artifact matching its artifact affinity | Unrepresented validated nodes | 0 | Cross-reference tree against generated artifacts during UC-07 |

---

## Facilitation Performance

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-F01 | Exec summary size: summaries presented to user must not exceed 20 displayed nodes | Nodes in summary | ≤ 20 | Count nodes in rendered output; overflow shown as "(+N more)" |
| NFR-F02 | Reflection checkpoint frequency: tree state summarised to user every 3-4 facilitation exchanges | Exchanges between summaries | 3-4 | Count exchanges since last summary |
| NFR-F03 | One question per turn: OODA spiral selects exactly one target node per facilitation turn | Questions per turn | 1 | Agent behaviour constraint |
| NFR-F04 | Completeness verification passes: maximum 3 passes before accepting current state | Verification iterations | ≤ 3 | Pass counter in UC-06 |
| NFR-F05 | Phase 2 circuit breaker: divergent exploration must not exceed 40 turns | Turns in Phase 2 | ≤ 40 | Turn counter |
| NFR-F06 | Phase 3 circuit breaker: convergent specification must not exceed 25 turns | Turns in Phase 3 | ≤ 25 | Turn counter |

---

## Scale Limits

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-S01 | Maximum tree size: tree should remain navigable for the agent within context window constraints | Total nodes | ≤ 200 nodes (advisory) | Count after mutations; warn if approaching |
| NFR-S02 | Batch advisory: when presenting multiple nodes (exec summary, completeness report), limit to 8 items per batch | Items per batch | ≤ 8 (following tria convention) | Count in rendering |

---

## Data Integrity

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-D01 | Persistence: PRIMITIVE_TREE.jsonld must be written to disk after every tree mutation | Unpersisted mutations | 0 | Persist step in every process flow that modifies the tree |
| NFR-D02 | Evidence/interpretation separation: CODEBASE_INDEX.json and PRIMITIVE_TREE.jsonld must remain as separate files with distinct purposes | Files in spec folder | Both present (brownfield) or only tree (greenfield) | File existence check |
| NFR-D03 | Session continuity: PRIMITIVE_TREE.jsonld must contain sufficient state to resume facilitation in a new session without re-asking questions | Resumability | Agent can read tree and continue from current state | Manual verification: start new session, verify agent picks up from tree state |
| NFR-D04 | Source provenance: every leaf node must have a source property recording its evidence origin | Nodes without source | 0 | Schema validation on tree |
| NFR-D05 | Health status consistency: no node may have health_status "validated" with source "inferred" (WEAK evidence cannot validate) | Validated-but-inferred nodes | 0 | Constraint check after every health transition |

---

## Schema Compliance

| ID | Requirement | Metric | Target | Measurement Method |
|----|-------------|--------|--------|-------------------|
| NFR-SC01 | JSON-LD format: PRIMITIVE_TREE.jsonld must be valid JSON-LD with @context, @graph, typed nodes, and typed edges | Validation errors | 0 | JSON-LD parser validation |
| NFR-SC02 | Node type vocabulary: every node must use one of the 7 standard types or a valid custom type with declared category | Unknown types | 0 | Schema validation against type list |
| NFR-SC03 | Dependency type vocabulary: every edge must use one of the 3 dependency types (depends-on, enables, conflicts-with) | Unknown edge types | 0 | Schema validation against dependency type list |
| NFR-SC04 | Required properties: every node must have definition, success_criterion, health_status, phase, artifactAffinity, and source | Missing required properties | 0 | Schema validation per node |

---

**NFR Quality Criteria:** Every requirement above specifies a measurable target and a
measurement method. Requirements that cannot be measured are not requirements.
