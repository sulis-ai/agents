# Software Requirements Document: Primitive Tree Architecture

**Version:** 1.0.0
**Date:** 2026-03-16
**Status:** Draft
**Author:** Iain (facilitated by Requirements Analyst)

---

## Summary

This document specifies the evolution of the SRD plugin's codebase mapping and facilitation
model from a flat inventory (CODEBASE_INDEX.json) into a structured primitive tree — a
directed acyclic graph of domain-specific architectural building blocks that drives question
generation, gap detection, and artifact production. The design adapts a proven pattern from
the tria project's business model decomposition (PRIMITIVE_TREE_SCHEMA.jsonld v1.2.0) for
software architecture decomposition.

The primitive tree sits between the codebase evidence layer and the facilitation conversation.
It synthesises LLM domain knowledge with codebase evidence (or user description for greenfield
projects) into a structured decomposition, then uses gaps in that decomposition to drive
targeted facilitation questions via an OODA spiral. The tree is a living artifact — it
evolves during facilitation and ships in the handover as a structural inventory complementing
the SRD's behavioural specification.

---

### 1. Introduction

#### 1.1 Purpose

This SRD specifies a new feature for the SRD plugin: the primitive tree. The feature
transforms the plugin's approach to codebase understanding and facilitation targeting. Instead
of a flat inventory that the agent references during conversation, the plugin will produce a
structured decomposition that actively drives which questions are asked, in what order, and
how completeness is verified.

#### 1.2 Scope

**In scope:**
- PRIMITIVE_TREE.jsonld schema definition (7 node types + open vocabulary, 3 dependency types, 5 health statuses, 5 facilitation phases)
- Tree synthesis process from CODEBASE_INDEX.json (brownfield) or user description (greenfield)
- OODA spiral integration: gap-driven question selection using tree state
- Exec summary rendering for user-facing tree presentation
- Health status lifecycle and transition rules
- Completeness verification using tree attack patterns and invalidation signals
- Tree as a first-class handover artifact
- Per-node-type properties, attack patterns, and invalidation signals

**Out of scope:**
- Changes to the codebase-mapping skill itself (CODEBASE_INDEX.json production is unchanged)
- Changes to the SRD template structure (the tree feeds into existing artifact types)
- Implementation of adversarial testing (tria's primitive-testing outcome is not adapted; health status transitions happen through facilitation, not through separate testing)
- Implementation of capability bridging (tria's product-capability-decomposition is not adapted; the tree feeds directly into SRD artifacts)

#### 1.3 Intended Audience

- **Execution agent / developer implementing this feature:** Primary audience. Needs exact schema, process steps, decision logic, and business rules.
- **SRD plugin maintainers:** Need to understand how the tree integrates with existing facilitation phases and artifact generation.
- **Users of the SRD plugin:** Need to understand what the tree provides (structural inventory) and how it appears during facilitation (exec summary).

#### 1.4 Definitions and Acronyms

See [GLOSSARY.md](GLOSSARY.md) for the full domain glossary.

#### 1.5 References

| Document | Location | Relevance |
|----------|----------|-----------|
| Tria PRIMITIVE_TREE_SCHEMA.jsonld v1.2.0 | `/Users/iain/Documents/repos/platform/methodology/standards/PRIMITIVE_TREE_SCHEMA.jsonld` | Source pattern for DAG structure, dependency types, health statuses, open vocabulary |
| Tria primitive-testing OUTCOME.md | `/Users/iain/Documents/repos/platform/methodology/outcomes/blueprint/primitive-testing/OUTCOME.md` | Source for health status transition mechanics, evidence grading, topological ordering |
| SRD Plugin requirements-analyst agent | `srd/agents/requirements-analyst.md` | Current facilitation model this feature extends |
| Codebase-mapping skill | `srd/skills/codebase-mapping/` | Upstream dependency — produces CODEBASE_INDEX.json consumed by tree synthesis |

---

### 2. Overall Description

#### 2.1 Product Perspective

The primitive tree is a new layer in the SRD plugin's architecture, sitting between the
existing codebase-mapping skill (which produces evidence) and the existing facilitation model
(which produces specifications). It does not replace either — it adds structured interpretation
between them.

**Current architecture:**
Codebase mapping -> CODEBASE_INDEX.json -> Agent references during conversation -> SRD artifacts

**New architecture:**
Codebase mapping -> CODEBASE_INDEX.json -> **Tree synthesis -> PRIMITIVE_TREE.jsonld -> OODA spiral drives conversation** -> SRD artifacts

The tree is both an internal working model (it drives question selection) and an external
artifact (it ships in the handover for the execution agent).

#### 2.2 Product Functions (Summary)

| Function | Description |
|----------|-------------|
| F-01 | Tree synthesis: produce PRIMITIVE_TREE.jsonld from codebase evidence or user description |
| F-02 | Gap-driven facilitation: OODA spiral selects questions based on tree gaps |
| F-03 | Tree evolution: update tree from user input during facilitation |
| F-04 | Exec summary: render tree as human-readable progress report at reflection checkpoints |
| F-05 | Completeness verification: check tree against attack patterns and invalidation signals |
| F-06 | Artifact generation integration: use tree as structural completeness checklist for SRD output |
| F-07 | Handover integration: ship tree as structural inventory alongside SRD |

#### 2.3 User Classes and Characteristics

| Actor | Description | Frequency of Use | Technical Proficiency |
|-------|-------------|-------------------|----------------------|
| SRD Agent | The LLM-based requirements analyst that synthesises, maintains, and uses the tree | Every facilitation session | N/A (automated) |
| Facilitation User | The person providing domain knowledge and confirming specifications | Every facilitation session | Varies (Level 1-3 per coaching calibration) |
| Execution Agent / Dev Team | Downstream consumer reading the tree as a structural inventory | Post-facilitation | High |

#### 2.4 Operating Environment

The primitive tree operates within the SRD plugin, which runs as a Claude Code agent skill.
No separate runtime, database, or service is required. All artifacts are files on disk in the
`.specifications/{name}/` folder.

#### 2.5 Design and Implementation Constraints

| Constraint | Rationale |
|------------|-----------|
| JSON-LD format for tree | Consistency with tria's schema; semantic web compatibility; self-describing with @context |
| 7 standard node types + open vocabulary | Composite of C4, DDD, and structured analysis — covers software architecture domain without over-fitting |
| Facilitation phases (not implementation phases) | Tree phase property governs when nodes are explored during specification, not when they are built |
| Evidence/interpretation separation | CODEBASE_INDEX.json (facts) and PRIMITIVE_TREE.jsonld (interpretation) must remain distinct files |
| Fan-out ≤ 7, depth ≤ 5 | Cognitive load management — Miller's law, structured analysis conventions |

#### 2.6 Assumptions and Dependencies

| Assumption | Validation Method | Impact if False |
|------------|-------------------|----------------|
| LLM domain knowledge is sufficient to produce a meaningful initial decomposition for common software domains | Test with 5+ diverse project types (e-commerce, SaaS, API, mobile, data pipeline) | Tree synthesis falls back to minimal skeleton; facilitation fills gaps manually |
| CODEBASE_INDEX.json provides sufficient signal to identify services, models, and integrations | Already validated by existing codebase-mapping skill usage | Brownfield trees are no better than greenfield; less grounded facilitation |
| 7 node types cover the software architecture domain adequately | Monitor custom type usage; promote to standard after 10+ uses (following tria's extensibility model) | Add standard types as patterns emerge |
| Users can meaningfully engage with the exec summary format | User feedback during facilitation sessions | Adjust rendering format based on feedback |

---

### 3. External Interface Requirements

#### 3.1 User Interfaces

The tree has no direct user interface. Users interact with the tree exclusively through:

- **Exec summary** — Plain-language rendering at reflection checkpoints (see UC-05). Grouped by health status. Maximum 20 nodes displayed. Ends with next question target.
- **Facilitation questions** — The tree drives which questions are asked, but the user sees only the question, not the tree logic behind it.
- **HANDOVER.md** — The tree is referenced in the handover as a structural inventory, with a rendered summary for human consumption and a pointer to the raw JSON-LD for programmatic use.

#### 3.2 Software Interfaces

| Interface | Direction | Format | Description |
|-----------|-----------|--------|-------------|
| CODEBASE_INDEX.json | Input | JSON | Flat codebase inventory produced by codebase-mapping skill |
| PRIMITIVE_TREE.jsonld | Output / Bidirectional | JSON-LD | The tree itself — written at synthesis, read and updated during facilitation |
| SRD artifacts (SRD.md, diagrams/, NFR.md) | Output | Markdown | Generated from conversation content, verified against tree for completeness |

---

### 4. System Features

#### 4.1 Tree Synthesis [F-01]

**Priority:** High

##### 4.1.1 Description

Produces the initial PRIMITIVE_TREE.jsonld from available inputs. Two paths: brownfield
(codebase evidence + LLM knowledge) and greenfield (user description + LLM knowledge). The
tree serves as the agent's structured hypothesis about the target system's architectural
building blocks, to be refined through facilitation.

##### 4.1.2 Use Cases

See [diagrams/use-cases.md](diagrams/use-cases.md) — UC-01 (brownfield), UC-02 (greenfield).
See [diagrams/process-flows.md](diagrams/process-flows.md) — PF-01 (tree synthesis process).
See [diagrams/data-flows.md](diagrams/data-flows.md) — DF-01 (artifact pipeline).

##### 4.1.3 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-01 | The system shall produce PRIMITIVE_TREE.jsonld from CODEBASE_INDEX.json when the index exists (brownfield path) | H | Given a valid CODEBASE_INDEX.json, the system produces a tree with at least one node per service, data model, and integration identified in the index |
| FR-02 | The system shall produce PRIMITIVE_TREE.jsonld from user description when no codebase index exists (greenfield path) | H | Given a user description of a system, the system produces a tree with at least 3 leaf nodes |
| FR-03 | Each leaf node shall have a type from the 7 standard types or a valid custom type | H | No node has an empty or unrecognised type without a declared custom category |
| FR-04 | Each leaf node shall have all required properties: definition, success_criterion, health_status, phase, artifactAffinity, source | H | Schema validation passes with 0 missing required properties |
| FR-05 | Dependencies shall be wired with typed edges (depends-on, enables, conflicts-with) based on codebase import graphs (brownfield) or domain inference (greenfield) | H | Every node with logical dependencies has at least one edge; no untyped edges exist |
| FR-06 | Scale constraints shall be enforced: fan-out ≤ 7 per node, depth ≤ 5, bounded context partitioning at > 40 leaves | H | Post-synthesis validation: no node exceeds 7 children, no path exceeds 5 levels, trees > 40 leaves have bounded context grouping |
| FR-07 | Codebase-evidenced nodes shall have source "codebase"; LLM-inferred nodes shall have source "inferred" | H | Every node's source matches its provenance |
| FR-08 | All initial nodes shall have health_status "untested" | H | No node starts with any status other than "untested" |
| FR-09 | The system shall gracefully degrade from brownfield to greenfield if CODEBASE_INDEX.json is malformed or empty | M | Agent logs warning and produces a greenfield tree instead of failing |

---

#### 4.2 Gap-Driven Facilitation [F-02]

**Priority:** High

##### 4.2.1 Description

The OODA spiral reads the tree, scores candidate nodes by composite priority, selects the
highest-priority gap, and formulates a facilitation question using the node's attack patterns.
This replaces the current approach where the agent selects questions based on exploration
domain coverage alone.

##### 4.2.2 Use Cases

See [diagrams/use-cases.md](diagrams/use-cases.md) — UC-03.
See [diagrams/process-flows.md](diagrams/process-flows.md) — PF-02 (OODA spiral).
See [diagrams/sequence-diagrams.md](diagrams/sequence-diagrams.md) — SD-02 (single turn detail).

##### 4.2.3 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-10 | The system shall score candidate nodes using: (fan_out * 3) + (active_invalidations * 2) + (phase_match * 1) + (low_confidence * 1) | H | Given a tree with known node states, the system selects the node with the highest composite score |
| FR-11 | Tie-breaking shall use topological order (upstream first), then time since last exploration | H | Given two nodes with identical scores, the system selects the one with more dependants; if equal, the one explored least recently |
| FR-12 | Questions shall be framed using the target node's attack patterns | H | Each facilitation question references at least one attack pattern from the target node type |
| FR-13 | The selected node shall transition to health_status "testing" when selected | H | Node status changes to "testing" before the question is presented |
| FR-14 | Topological ordering shall be respected: upstream dependencies explored before downstream dependants within the same priority tier | H | No node with depends-on edges to untested nodes is selected when those upstream nodes have equal or higher scores |
| FR-15 | When all nodes are validated or accepted-as-risk, the system shall signal readiness for artifact generation | M | OODA spiral returns "complete" instead of a question when no gaps remain |

---

#### 4.3 Tree Evolution [F-03]

**Priority:** High

##### 4.3.1 Description

Incorporates user answers into the tree — updates node properties, transitions health
statuses, creates new nodes when the user introduces new concepts, and removes or restructures
nodes when the user corrects the decomposition.

##### 4.3.2 Use Cases

See [diagrams/use-cases.md](diagrams/use-cases.md) — UC-04.
See [diagrams/process-flows.md](diagrams/process-flows.md) — PF-03 (tree update).
See [diagrams/state-diagrams.md](diagrams/state-diagrams.md) — ST-01 (health status lifecycle).

##### 4.3.3 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-16 | User confirmation of an inferred node shall transition source from "inferred" to "user" | H | Source property updated; evidence grade rises from WEAK to FAIR |
| FR-17 | Full specification of a node (all attack patterns addressed, no invalidation signals) shall transition health_status from "testing" to "validated" | H | Node marked validated only when all type-specific attack patterns addressed and evidence grade is FAIR or STRONG |
| FR-18 | Matched invalidation signals or user rejection shall transition health_status from "testing" to "failed" | H | Node marked failed; depends-on dependants flagged for re-evaluation |
| FR-19 | User risk acceptance shall transition health_status from "testing" to "accepted-as-risk" with documented justification | H | Risk recorded on node; node flagged in COMPLETENESS_REPORT.md |
| FR-20 | New concepts introduced by user shall create new nodes with source "user", appropriate type, and wired dependencies | H | New nodes have all required properties; scale constraints re-validated |
| FR-21 | Tree restructuring (reparenting, splitting, merging nodes) shall maintain DAG integrity — no cycles introduced | H | Topological sort succeeds after every restructure |
| FR-22 | PRIMITIVE_TREE.jsonld shall be persisted after every tree mutation | H | File written to disk after every update operation |
| FR-23 | A validated node shall revert to "testing" if new information contradicts the previous specification | M | Contradiction detection triggers status reversal; previous validation recorded as historical |

---

#### 4.4 Exec Summary Rendering [F-04]

**Priority:** Medium

##### 4.4.1 Description

Renders the tree as a plain-language progress report at reflection checkpoints. Groups nodes
by health status, shows counts, ends with the next question target. The user never sees raw
JSON — only this human-friendly summary.

##### 4.4.2 Use Cases

See [diagrams/use-cases.md](diagrams/use-cases.md) — UC-05.

##### 4.4.3 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-24 | Summary shall group nodes by health status: validated, in progress (testing), not yet explored (untested), flagged (failed/accepted-as-risk) | H | All four groups present in output (empty groups omitted) |
| FR-25 | Each group shall show count and total: "{n} of {total}" | H | Counts are accurate against tree state |
| FR-26 | Each node in summary shall show name and one-line description | H | No node rendered as an ID or JSON path |
| FR-27 | Maximum 20 nodes displayed per summary; overflow shown as "(+N more)" | M | Summary never exceeds 20 node entries |
| FR-28 | Summary shall end with next question target and rationale from OODA scoring | H | Every summary concludes with "Next, I'd like to explore..." |
| FR-29 | Summary shall not expose tree internals: no JSON, no dependency edges, no phase assignments | H | Summary is plain language only |

---

#### 4.5 Completeness Verification [F-05]

**Priority:** High

##### 4.5.1 Description

Systematically checks the tree against attack patterns and invalidation signals to identify
gaps before artifact generation. Uses the existing requirements-validation skill's three
perspectives (traceability, integration completeness, NFR coverage) augmented with tree-specific
checks.

##### 4.5.2 Use Cases

See [diagrams/use-cases.md](diagrams/use-cases.md) — UC-06.
See [diagrams/process-flows.md](diagrams/process-flows.md) — PF-04 (completeness verification).

##### 4.5.3 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-30 | For each node, every attack pattern defined for its type shall be evaluated against the facilitation record | H | Checklist of attack patterns with addressed/unaddressed status per node |
| FR-31 | Active invalidation signals shall be flagged with specific evidence | H | Each active signal references the evidence that triggered it |
| FR-32 | Gaps fixable from conversation context shall be fixed inline with a recorded fix | M | Fix applied; fix recorded in COMPLETENESS_REPORT.md |
| FR-33 | Gaps requiring user input shall be presented one at a time | H | No multi-part gap questions |
| FR-34 | Maximum 3 verification passes before accepting current state | H | Pass counter enforced; remaining gaps documented |
| FR-35 | COMPLETENESS_REPORT.md shall list all checks, passes, fixes, and remaining gaps | H | Report follows requirements-validation output format |

---

#### 4.6 Artifact Generation Integration [F-06]

**Priority:** High

##### 4.6.1 Description

Uses the tree as a structural completeness checklist during artifact generation. Every validated
node must appear in at least one SRD artifact matching its artifact affinity. The conversation
remains the primary content source; the tree provides structure.

##### 4.6.2 Use Cases

See [diagrams/use-cases.md](diagrams/use-cases.md) — UC-07.
See [diagrams/data-flows.md](diagrams/data-flows.md) — DF-01 (artifact pipeline).

##### 4.6.3 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-36 | The system shall build an artifact generation checklist from the artifactAffinity of each validated node | H | Checklist maps each validated node to its required artifact types |
| FR-37 | Every validated node shall be represented in at least one artifact | H | Cross-reference check: 0 unrepresented validated nodes |
| FR-38 | The conversation (not the tree) shall be the primary source for artifact content | H | Artifacts contain facilitation-derived specifications, not tree property values |
| FR-39 | Nodes with health_status "accepted-as-risk" shall be included in artifacts with risk annotations | M | Risk-accepted nodes appear with documented caveats |

---

#### 4.7 Handover Integration [F-07]

**Priority:** Medium

##### 4.7.1 Description

Ships the primitive tree as a first-class execution artifact in the handover, positioned as a
structural inventory complementing the SRD's behavioural specification. The handover includes
a rendered summary for human consumption and a pointer to the raw JSON-LD.

##### 4.7.2 Use Cases

See [diagrams/use-cases.md](diagrams/use-cases.md) — UC-08.

##### 4.7.3 Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-40 | HANDOVER.md shall include the tree in its recommended reading order | H | Tree referenced between GLOSSARY.md and SRD.md in reading order |
| FR-41 | HANDOVER.md shall include a rendered summary distinguishing new components (source "user"/"inferred") from existing (source "codebase") | H | Summary shows new vs. existing with counts |
| FR-42 | HANDOVER.md shall explain how to use depends-on edges for implementation sequencing | M | Implementation ordering guidance present with example |
| FR-43 | PRIMITIVE_TREE.jsonld shall be listed as a deliverable artifact alongside SRD.md | H | File listed in artifact manifest |

---

### 5. Non-Functional Requirements

See [NFR.md](NFR.md) for full non-functional requirements specification.

| Category | Summary |
|----------|---------|
| Tree Quality | Fan-out ≤ 7, depth ≤ 5, DAG acyclicity, bounded context partitioning at > 40 leaves |
| Facilitation Performance | Exec summary ≤ 20 nodes, reflection every 3-4 turns, one question per turn, ≤ 3 verification passes |
| Scale Limits | ≤ 200 nodes advisory, ≤ 8 items per batch display |
| Data Integrity | Persist after every mutation, evidence/interpretation separation, source provenance on every node |
| Schema Compliance | Valid JSON-LD, 7 standard types + custom, 3 dependency types, required properties enforced |

---

### 6. Diagrams

| Diagram Type | File | Purpose |
|-------------|------|---------|
| Use Case | [diagrams/use-cases.md](diagrams/use-cases.md) | 8 use cases covering all actors and system capabilities |
| Process Flow | [diagrams/process-flows.md](diagrams/process-flows.md) | Tree synthesis, OODA spiral, tree update, completeness verification |
| Sequence | [diagrams/sequence-diagrams.md](diagrams/sequence-diagrams.md) | End-to-end session, single facilitation turn detail |
| State | [diagrams/state-diagrams.md](diagrams/state-diagrams.md) | Node health status lifecycle, facilitation phase progression |
| Data Flow | [diagrams/data-flows.md](diagrams/data-flows.md) | Artifact pipeline, facilitation loop |

---

### 7. Node Type Schema

This section specifies the complete schema for each of the 7 standard node types, including
type-specific properties, attack patterns, and invalidation signals. This is the core
reference for the PRIMITIVE_TREE.jsonld schema implementation.

#### 7.1 Common Properties (All Node Types)

Every node, regardless of type, carries these properties:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| id | string | yes | Unique identifier within the tree |
| name | string | yes | Human-readable name |
| type | string | yes | One of: domain-entity, action, integration, data-store, state-machine, policy, event, custom |
| definition | string | yes | What this node represents in the target domain |
| success_criterion | string | yes | Measurable condition confirming this node is correctly specified |
| health_status | string | yes | untested, testing, validated, failed, accepted-as-risk |
| phase | string | yes | discover, define, connect, constrain, verify |
| artifactAffinity | string[] | yes | Which SRD artifact types this node feeds into |
| source | string | yes | codebase, inferred, user |
| parent | string | no | ID of parent node (null for root) |
| dependencies | object[] | no | Array of {target: node_id, type: depends-on|enables|conflicts-with} |

#### 7.2 domain-entity

An entity in the target domain that the system stores, manages, or transforms.

**Type-specific properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| attributes | string[] | no | Key attributes at architectural level |
| relationships | string[] | no | Named relationships to other domain entities |

**Default artifact affinities:** use-case, data-flow

**Default phase:** define

**Attack patterns:**
1. "What are the boundaries of this entity? Could it be two separate entities?"
2. "Which actions read or write this entity? Are there actions with no entity connection?"
3. "Does every attribute belong to this entity, or does one leak from a different bounded context?"

**Invalidation signals:**
- Entity has no actions that reference it (orphaned entity)
- Entity has attributes belonging to different lifecycle stages (needs splitting)
- Two entities share the same attributes with different names (duplication)

#### 7.3 action

Something the system does — a behaviour triggered by an actor or event.

**Type-specific properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| actor | string | yes | Who or what initiates this action |
| inputs | string[] | no | Data or preconditions required |
| outputs | string[] | no | What the action produces or changes |

**Default artifact affinities:** use-case, process-flow

**Default phase:** define

**Attack patterns:**
1. "What happens if this action fails mid-execution? Is the failure mode specified?"
2. "Can two actors trigger this action simultaneously? Is concurrency addressed?"
3. "Are there preconditions that must be true, and what happens if they're violated?"

**Invalidation signals:**
- Action has no defined error path (happy path only)
- Action modifies state in multiple entities with no transaction or compensation strategy
- Action has no identified actor (passive voice)

#### 7.4 integration

A point where the target system meets an external system.

**Type-specific properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| external_system | string | yes | Name of the external system or service |
| direction | string | yes | inbound, outbound, bidirectional |
| protocol | string | no | REST, GraphQL, gRPC, webhook, queue, file-transfer |

**Default artifact affinities:** sequence-diagram, data-flow

**Default phase:** connect

**Attack patterns:**
1. "What happens when the external system is unavailable?"
2. "Is the data contract between systems specified precisely enough to implement?"
3. "What is the authentication and authorisation model for this integration?"

**Invalidation signals:**
- No error handling specified
- Protocol or data format not specified
- No timeout, retry, or circuit breaker policy

#### 7.5 data-store

A place where the system persists data.

**Type-specific properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| store_type | string | yes | relational, document, key-value, graph, file, cache, queue |
| entities | string[] | no | Which domain-entity nodes this store persists |

**Default artifact affinities:** data-flow

**Default phase:** connect

**Attack patterns:**
1. "What is the expected data volume, and does the store type support it?"
2. "Is there a single source of truth for each piece of data, or are there conflicting stores?"
3. "What are the data retention and backup requirements?"

**Invalidation signals:**
- Same data written to multiple stores with no consistency strategy
- No retention or deletion policy
- Store type mismatched with access pattern

#### 7.6 state-machine

An entity that moves through defined stages over time.

**Type-specific properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| entity | string | yes | Which domain-entity this state machine governs |
| states | string[] | yes | Named states at architectural level |

**Default artifact affinities:** state-diagram

**Default phase:** define

**Attack patterns:**
1. "Can the entity reach a state from which no transition is possible (dead state)?"
2. "Are there transitions that should be disallowed but are not explicitly forbidden?"
3. "What triggers each transition, and what guards must be true?"

**Invalidation signals:**
- State has no outgoing transitions and is not terminal (dead state)
- Two triggers cause conflicting transitions from the same state (non-determinism)
- Transitions with no specified trigger or guard

#### 7.7 policy

A rule, constraint, or validation that governs system behaviour.

**Type-specific properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| policy_type | string | yes | validation, authorization, rate-limit, business-rule, compliance |
| scope | string | no | What part of the system this policy applies to |

**Default artifact affinities:** business-rule, nfr

**Default phase:** define (business rules) or constrain (NFR-type policies)

**Attack patterns:**
1. "What happens when this policy is violated? Is the violation path specified?"
2. "Does this policy conflict with any other policy in the system?"
3. "Is this policy testable — can someone write a test that proves it works?"

**Invalidation signals:**
- Policy described in vague terms with no measurable criterion
- Policy contradicts another policy
- Policy has no enforcement point

#### 7.8 event

Something that happens that other parts of the system need to know about.

**Type-specific properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| trigger | string | yes | What causes this event to fire |
| consumers | string[] | no | Which nodes react to this event |

**Default artifact affinities:** sequence-diagram, data-flow

**Default phase:** connect

**Attack patterns:**
1. "What happens if this event is published but no consumer processes it?"
2. "What happens if a consumer receives this event out of order or duplicated?"
3. "Is this event necessary, or could the consumer query the source directly?"

**Invalidation signals:**
- Event has no consumers (published but never consumed)
- Event carries data that could become stale, with no versioning or timestamp
- Event duplicates data available through synchronous query

#### 7.9 Custom Types (Open Vocabulary)

Following tria's extensibility model, custom node types are permitted using:

```json
{
  "type": "custom",
  "custom_type_name": "{Custom Type Name}",
  "category": "{Closest standard type}",
  "definition": "...",
  "success_criterion": "...",
  "health_status": "...",
  "phase": "...",
  "artifactAffinity": ["..."],
  "source": "..."
}
```

Custom types used in 10 or more analyses are candidates for promotion to standard types.

---

### 8. Business Rules

| ID | Rule | Applies To | Verification |
|----|------|------------|--------------|
| BR-01 | Fan-out ≤ 7 children per node | Tree synthesis (FR-06), tree update (FR-20) | Structural validation after every mutation |
| BR-02 | Tree depth ≤ 5 levels from root to deepest leaf | Tree synthesis (FR-06), tree update (FR-20) | Path length check after every mutation |
| BR-03 | Codebase-evidenced nodes get source "codebase"; LLM-inferred nodes get source "inferred" | Tree synthesis (FR-07) | Source assignment check |
| BR-04 | All initial nodes start with health_status "untested" | Tree synthesis (FR-08) | Status check at creation |
| BR-05 | Greenfield nodes all get source "inferred" | Tree synthesis greenfield path (FR-02) | Source assignment check |
| BR-06 | Topological ordering: upstream dependencies before downstream dependants | OODA spiral (FR-14) | Ordering validation in question selection |
| BR-07 | WEAK evidence (source "inferred") can identify gaps but cannot validate | Health transitions (FR-17) | Validation guard: source must be "codebase" or "user" |
| BR-08 | Composite score: (fan_out * 3) + (active_invalidations * 2) + (phase_match * 1) + (low_confidence * 1) | OODA spiral (FR-10) | Score calculation verification |
| BR-09 | User confirmation transitions source from "inferred" to "user" | Tree update (FR-16) | Source transition check |
| BR-10 | New user-introduced nodes get source "user" | Tree update (FR-20) | Source assignment check |
| BR-11 | Exec summary maximum 20 nodes | Rendering (FR-27) | Count check |
| BR-12 | Plain language only in summaries — no JSON, edges, or phases | Rendering (FR-29) | Content check |
| BR-13 | Summary ends with next question target | Rendering (FR-28) | Presence check |
| BR-14 | Maximum 3 completeness verification passes | Verification (FR-34) | Pass counter |
| BR-15 | Small gaps fixed inline; large gaps surfaced to user | Verification (FR-32, FR-33) | Classification check |
| BR-16 | Every validated node in at least one artifact | Artifact generation (FR-37) | Cross-reference check |
| BR-17 | Conversation is primary content source; tree is structural checklist | Artifact generation (FR-38) | Content provenance check |

---

### 9. Evidence Grading

Adapted from tria's three-tier evidence quality model. Governs what evidence can trigger
which health status transitions.

| Grade | Source | Can Validate? | Can Invalidate? | Rationale |
|-------|--------|---------------|-----------------|-----------|
| STRONG | Codebase evidence — node maps to existing code | Yes | Yes | Strongest evidence: the thing exists and can be verified |
| FAIR | User confirmation — user has specified or confirmed details | Yes | Yes | User has domain authority; their explicit confirmation is reliable |
| WEAK | Agent inference — LLM domain knowledge suggests this node | No | Yes (can flag gaps) | Agent can hypothesise and identify missing pieces, but cannot self-validate |

**Key constraint (BR-07):** A node cannot transition from "testing" to "validated" with WEAK
evidence only. The agent's inference alone is insufficient — the user must confirm (FAIR) or
the codebase must evidence (STRONG) before validation.

---

### 10. Traceability Matrix

| Goal | Use Cases | Diagrams | NFRs | Features |
|------|-----------|----------|------|----------|
| G-01: Structured decomposition drives facilitation | UC-01, UC-02, UC-03 | PF-01, PF-02, DF-01 | NFR-Q01-Q05 | F-01, F-02 |
| G-02: Tree evolves from hypothesis to ground truth | UC-04 | PF-03, ST-01 | NFR-D01, NFR-D03 | F-03 |
| G-03: User sees progress, not internals | UC-05 | DF-02 | NFR-F01-F03 | F-04 |
| G-04: Completeness verified before artifact generation | UC-06 | PF-04 | NFR-F04, NFR-Q05 | F-05 |
| G-05: Artifacts structurally complete | UC-07 | DF-01 | NFR-Q05 | F-06 |
| G-06: Tree useful for execution team | UC-08 | — | NFR-D02-D04 | F-07 |

---

### 11. Appendices

#### 11.1 Exploration Journal
See [EXPLORATION_JOURNAL.md](EXPLORATION_JOURNAL.md) for the facilitation record.

#### 11.2 Completeness Report
See [COMPLETENESS_REPORT.md](COMPLETENESS_REPORT.md) for the verification assessment.

#### 11.3 Handover Brief
See [HANDOVER.md](HANDOVER.md) for the execution agent handover.
