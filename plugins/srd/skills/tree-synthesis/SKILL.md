---
name: tree-synthesis
description: >
  Synthesise a PRIMITIVE_TREE.jsonld from a codebase index (brownfield) or user
  description (greenfield). Produces a directed acyclic graph of domain-specific
  architectural building blocks with typed nodes, dependency edges, health statuses,
  and facilitation phases. Used by the requirements-analyst agent to drive gap-targeted
  facilitation via an OODA spiral.
---

# Tree Synthesis

When invoked, synthesise a PRIMITIVE_TREE.jsonld from available inputs. Two paths:
brownfield (CODEBASE_INDEX.json exists) and greenfield (user description only).

If arguments are provided, treat them as the path to the specification folder.
If no path is provided, use the most recently modified folder in `.specifications/`.

The tree is the agent's structured hypothesis about the target system's architectural
building blocks. It drives facilitation question selection and evolves from user input.

---

## Node Type Schema

Seven standard node types cover the software architecture domain. Each type has specific
properties, attack patterns (questions that probe the node's specification completeness),
and invalidation signals (conditions that indicate the node's specification is flawed).

### Common Properties (All Node Types)

Every node carries these properties regardless of type:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| id | string | yes | Unique identifier within the tree (e.g., `node-auth-service`) |
| name | string | yes | Human-readable name |
| type | string | yes | One of: domain-entity, action, integration, data-store, state-machine, policy, event, custom |
| definition | string | yes | What this node represents in the target domain |
| success_criterion | string | yes | Measurable condition confirming this node is correctly specified |
| health_status | string | yes | untested, testing, validated, failed, accepted-as-risk |
| phase | string | yes | discover, define, connect, constrain, verify |
| artifactAffinity | string[] | yes | Which SRD artifact types this node feeds into |
| source | string | yes | codebase, inferred, user |
| parent | string | no | ID of parent node (null for root) |
| dependencies | object[] | no | Array of `{target, type}` — see Dependency Wiring Rules |
| leaf_category | string | conditional | One of `external-system | genesis-bootstrap | primitive-component | external-spec | existing-impl`. **Required** when `health_status: validated` AND the node has zero outgoing depends-on edges to non-terminated nodes. Set by the SRD analyst's Two-Model OODA Reconciliation rule during the Decide step, not at synthesis. Nodes synthesised from CODEBASE_INDEX.json are candidates for `existing-impl` but the category is committed during reconciliation. The five-value vocabulary is the irreducible-primitive taxonomy: external-system (outside our boundary, e.g. Stripe), genesis-bootstrap (one-time system seed, admin-plane), primitive-component (validated atom per whiteboard test + scale constraints), external-spec (specified in another SRD), existing-impl (code ships it; spec describes configuration not implementation). |


### domain-entity

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


### action

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


### integration

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


### data-store

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


### state-machine

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


### policy

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


### event

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


### Custom Types (Open Vocabulary)

Custom node types are permitted when the 7 standard types do not fit. Use:

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

## Evidence Grading

Three tiers of evidence quality govern what can trigger health status transitions.

| Grade | Source | Can Validate? | Can Invalidate? | Rationale |
|-------|--------|---------------|-----------------|-----------|
| STRONG | Codebase evidence — node maps to existing code | Yes | Yes | Strongest: the thing exists and can be verified |
| FAIR | User confirmation — user has specified or confirmed | Yes | Yes | User has domain authority; explicit confirmation is reliable |
| WEAK | Agent inference — LLM domain knowledge suggests this | No | Yes (can flag gaps) | Agent can hypothesise but cannot self-validate |

**Key constraint (BR-07):** A node cannot transition from "testing" to "validated" with
WEAK evidence only. The user must confirm (FAIR) or the codebase must evidence (STRONG)
before validation.


---

## Brownfield Synthesis Process

When CODEBASE_INDEX.json exists and is valid, follow the brownfield path.

### Step 1: Read CODEBASE_INDEX.json

Read the index from the specification folder. Parse the technology stack, services,
integrations, data models, and routes.

### Step 2: Seed Root Node

Create the root node from the project name in the codebase index:

```json
{
  "id": "root",
  "name": "{project name}",
  "type": "domain-entity",
  "definition": "Root node representing the {project name} system",
  "success_criterion": "All child nodes validated or accepted-as-risk",
  "health_status": "untested",
  "phase": "discover",
  "artifactAffinity": ["use-case"],
  "source": "codebase",
  "parent": null
}
```

### Step 3: Create Capability Nodes from Services

For each service in `services[]`, create a child node under root:

- Map service responsibilities to the most appropriate node type:
  - Services that primarily manage data → `domain-entity`
  - Services that primarily perform actions → `action`
  - Services that mediate between systems → `integration`
  - Services that enforce rules → `policy`
- Set `source: "codebase"` for all service-derived nodes
- Set `parent: "root"`
- Assign default artifact affinities and phase from the node type

### Step 4: Create Leaf Nodes from Evidence

**From data models:** For each entry in `data_models[]`, create a `domain-entity` node
with key fields as attributes. Wire `depends-on` edges to the service that manages it.

**From integrations:** For each entry in `integrations.external[]`, create an `integration`
node with external_system, direction, and protocol (if available from the index).

**From status fields:** If data models have fields suggesting lifecycle states (status,
state, phase, stage), create `state-machine` nodes governing those entities.

All nodes created from codebase evidence get `source: "codebase"`.

### Step 5: Apply Domain Knowledge

Use LLM domain knowledge to infer nodes that the codebase evidence implies but does
not explicitly contain:

- Common policies for the domain (e.g., authentication policy, data validation)
- Events that likely exist between identified services
- Missing integration points suggested by the technology stack

All inferred nodes get `source: "inferred"`.

### Step 6: Wire Dependency Edges

Analyse import graphs and service relationships from the codebase index:

- Services that call other services → `depends-on`
- Services that enhance other services' capabilities → `enables`
- Services with mutually exclusive configurations → `conflicts-with`

See Dependency Wiring Rules below for edge semantics.


---

## Greenfield Synthesis Process

When no CODEBASE_INDEX.json exists, follow the greenfield path.

### Step 1: Parse User Description

Extract key concepts from the user's Phase 1 description of their system:

- What the system does (capabilities)
- Who uses it (actors)
- What it connects to (integrations)
- What rules govern it (policies)
- What data it manages (entities)

### Step 2: Seed Root Node

Create the root node from the stated scope:

```json
{
  "id": "root",
  "name": "{stated system name or scope}",
  "type": "domain-entity",
  "definition": "Root node representing the {system} as described by user",
  "success_criterion": "All child nodes validated or accepted-as-risk",
  "health_status": "untested",
  "phase": "discover",
  "artifactAffinity": ["use-case"],
  "source": "inferred",
  "parent": null
}
```

### Step 3: Decompose via Domain Knowledge

Use LLM domain knowledge to decompose the user's description into architectural
building blocks:

- Identify the most likely domain entities, actions, integrations, data stores,
  state machines, policies, and events
- Create nodes for each, all with `source: "inferred"`
- Wire dependency edges based on domain conventions

The greenfield tree is a hypothesis — every node is `source: "inferred"` and
`health_status: "untested"`. Facilitation will confirm, refine, or reject each node.


---

## Dependency Wiring Rules

Three dependency types connect nodes in the tree:

**depends-on** — A requires B to function. If B fails, A is affected.
- Direction: A → B
- Propagation: Failure of B propagates to A. If B transitions to `failed`, A must be
  re-evaluated.
- Example: "Payment processing" depends-on "Payment gateway integration"

**enables** — A makes B possible or more effective. B can exist without A but is weaker.
- Direction: A → B
- Propagation: Removal of A weakens B but does not kill it.
- Example: "Caching layer" enables "Search performance"

**conflicts-with** — A and B cannot both succeed simultaneously. Validating A may
invalidate B.
- Direction: A ↔ B (bidirectional)
- Propagation: Validation of one may invalidate the other.
- Example: "Synchronous processing" conflicts-with "Event-driven architecture"


---

## Scale Constraint Enforcement

After synthesis (and after every subsequent tree mutation), validate:

**BR-01: Fan-out ≤ 7** — No node may have more than 7 direct children. If a node
exceeds 7 children, introduce an intermediate grouping node to partition the children
into conceptual clusters.

**BR-02: Depth ≤ 5** — No path from root to leaf may exceed 5 levels. If depth exceeds
5, flatten by merging intermediate nodes or promoting leaf nodes.

**NFR-Q03: Bounded context partitioning at > 40 leaves** — When the tree exceeds 40
leaf nodes, partition into bounded contexts. Each bounded context becomes a subtree
with its own intermediate root node under the global root.


---

## Phase Assignment

Default phase by node type. Phase governs when a node is typically explored during
facilitation.

| Node Type | Default Phase | Rationale |
|-----------|--------------|-----------|
| domain-entity | define | Core entities defined early |
| action | define | Behaviours defined alongside entities |
| integration | connect | External boundaries explored after core is defined |
| data-store | connect | Storage decisions follow entity identification |
| state-machine | define | Lifecycles defined alongside the entities they govern |
| policy | define (business rules) or constrain (NFR-type) | Rules defined early; constraints explored later |
| event | connect | Events connect components after they are identified |


---

## Initial Health Status

All nodes start with `health_status: "untested"` regardless of source (BR-04). Even
codebase-evidenced nodes are "untested" — evidence that the code exists does not mean
the specification is correct for the new feature.


---

## Graceful Degradation

If CODEBASE_INDEX.json exists but is malformed, empty, or unreadable:

1. Log a warning: "CODEBASE_INDEX.json is malformed — falling back to greenfield synthesis"
2. Proceed with the greenfield synthesis process using whatever user description is
   available from Phase 1
3. Do not fail or block the facilitation session


---

## Output Format

The tree is written as PRIMITIVE_TREE.jsonld with JSON-LD structure:

```json
{
  "@context": {
    "@vocab": "https://sulis.co/ontology/primitive-tree/",
    "schema": "http://schema.org/",
    "prim": "https://sulis.co/ontology/primitive-tree/",
    "name": "schema:name",
    "description": "schema:description"
  },
  "@id": "prim:tree-{project-name}",
  "@type": "prim:PrimitiveTree",
  "name": "{Project Name} — Primitive Tree",
  "synthesised_at": "{ISO-8601 timestamp}",
  "synthesis_path": "brownfield | greenfield",
  "source_index": "CODEBASE_INDEX.json | null",
  "@graph": [
    {
      "@id": "root",
      "@type": "prim:domain-entity",
      "name": "{Project Name}",
      "definition": "Root node representing the system",
      "success_criterion": "All child nodes validated or accepted-as-risk",
      "health_status": "untested",
      "phase": "discover",
      "artifactAffinity": ["use-case"],
      "source": "codebase",
      "parent": null,
      "dependencies": []
    }
  ]
}
```

Each node in `@graph` includes all common properties plus type-specific properties.
Dependency edges are embedded in each node's `dependencies` array as
`{"target": "{node-id}", "type": "depends-on|enables|conflicts-with"}`.


---

## Persistence

Write the completed tree to `.specifications/{name}/PRIMITIVE_TREE.jsonld`.

If the file already exists, overwrite it — tree synthesis produces a fresh tree each
time it runs. Tree evolution during facilitation is handled by the agent, not by
re-running synthesis.


---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2026-03-17 | Initial version — tree synthesis skill | Standards team |
| 2026-03-17 | Clarified invocation: brownfield runs synchronously after codebase mapping; greenfield runs in-conversation when scope is sufficient (what + who + 2 of: integrations, entities, workflows, rules). | Standards team |
