# Process Flow Diagrams: Primitive Tree Architecture

**Version:** 1.0.0
**Date:** 2026-03-16

---

## Summary

Four process flows capture the key workflows of the primitive tree system: tree synthesis
(how the tree is created), the OODA spiral (how facilitation questions are selected),
tree update (how user input changes the tree), and completeness verification (how the
tree is checked for gaps before artifact generation).

---

## PF-01: Tree Synthesis Process

**Related Use Case:** UC-01, UC-02
**Trigger:** CODEBASE_INDEX.json produced (brownfield) or user describes system in orientation (greenfield)
**End State:** PRIMITIVE_TREE.jsonld persisted to specification folder

```mermaid
flowchart TD
    Start([Start: Codebase index available or user description received])
    DetectType{"Codebase index exists?"}

    subgraph Brownfield["Brownfield Path"]
        B1[Read CODEBASE_INDEX.json]
        B2[Seed root from project name]
        B3[Create capability nodes from services]
        B4[Create leaf nodes from data models, integrations, status fields]
        B5[Apply LLM domain knowledge: infer missing nodes]
    end

    subgraph Greenfield["Greenfield Path"]
        G1[Parse user description from Phase 1]
        G2[Seed root from stated scope]
        G3[Apply LLM domain knowledge: decompose into expected building blocks]
    end

    WireDeps[Wire dependency edges: depends-on, enables, conflicts-with]
    CheckScale{"Fan-out > 7 or depth > 5 or leaves > 40?"}
    ApplyConstraints[Apply scale constraints: group, flatten, or partition]
    AssignPhases[Assign facilitation phases by node type]
    Persist[Persist PRIMITIVE_TREE.jsonld]
    End([End: Tree ready for facilitation])

    Start --> DetectType
    DetectType -->|Yes| B1
    DetectType -->|No| G1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> B5
    B5 --> WireDeps
    G1 --> G2
    G2 --> G3
    G3 --> WireDeps
    WireDeps --> CheckScale
    CheckScale -->|Yes| ApplyConstraints
    CheckScale -->|No| AssignPhases
    ApplyConstraints --> AssignPhases
    AssignPhases --> Persist
    Persist --> End
```

#### Process Steps

| Step | Description | Actor/System | Inputs | Outputs | Business Rules |
|------|-------------|-------------|--------|---------|----------------|
| 1 | Detect brownfield vs. greenfield | System | Presence of CODEBASE_INDEX.json | Path selection | — |
| 2a | Read codebase index | System | CODEBASE_INDEX.json | Parsed services, models, integrations | — |
| 2b | Parse user description | System | Phase 1 conversation | System scope description | — |
| 3 | Create initial nodes | System | Parsed evidence or description | Tree nodes with types and sources | BR-03, BR-05 |
| 4 | Apply LLM inference | System | Domain knowledge + evidence | Additional "inferred" nodes | BR-03 |
| 5 | Wire dependencies | System | Node list | Typed edges | — |
| 6 | Apply scale constraints | System | Tree structure | Restructured tree | BR-01, BR-02 |
| 7 | Assign phases | System | Node types | Phase assignments | — |
| 8 | Persist | System | Complete tree | PRIMITIVE_TREE.jsonld | — |

#### Decision Points

| Decision | Criteria | Yes Path | No Path |
|----------|----------|----------|---------|
| Codebase index exists? | File present and parseable in `.specifications/{name}/` | Brownfield path | Greenfield path |
| Scale constraints violated? | Fan-out > 7 at any node, depth > 5, or leaf count > 40 | Apply constraints then assign phases | Assign phases directly |

---

## PF-02: OODA Spiral — Question Selection

**Related Use Case:** UC-03
**Trigger:** Previous facilitation exchange completed; tree has untested or invalidated nodes
**End State:** One facilitation question formulated and presented to user

```mermaid
flowchart TD
    Start([Start: Previous exchange completed])
    Observe[Observe: Read tree, catalogue nodes by health_status]
    HasGaps{"Any untested or invalidated nodes?"}
    NoGaps([Signal: Ready for artifact generation])

    Orient[Orient: Score each candidate node]
    Score["Score = fan_out*3 + invalidations*2 + phase_match*1 + low_confidence*1"]
    Decide{"Multiple nodes tied?"}
    TieBreak[Break tie: topological order, then recency]
    SelectNode[Select highest-scoring node]
    MapDomain[Map node type to exploration domain]
    SelectAttack[Select attack pattern to frame question]
    Act[Formulate question, set node to health_status testing]
    End([End: Question presented to user])

    Start --> Observe
    Observe --> HasGaps
    HasGaps -->|No| NoGaps
    HasGaps -->|Yes| Orient
    Orient --> Score
    Score --> Decide
    Decide -->|Yes| TieBreak
    Decide -->|No| SelectNode
    TieBreak --> SelectNode
    SelectNode --> MapDomain
    MapDomain --> SelectAttack
    SelectAttack --> Act
    Act --> End
```

#### Process Steps

| Step | Description | Actor/System | Inputs | Outputs | Business Rules |
|------|-------------|-------------|--------|---------|----------------|
| 1 | Observe tree state | System | PRIMITIVE_TREE.jsonld | Node catalogue by status | — |
| 2 | Score candidates | System | Node properties, dependency graph | Scored candidate list | BR-08 |
| 3 | Select target node | System | Scored list | Single target node | BR-06 |
| 4 | Map to exploration domain | System | Node type | Domain assignment | — |
| 5 | Select attack pattern | System | Node type's attack_patterns | Question angle | — |
| 6 | Formulate question | System | Attack pattern, node context | Facilitation question | BR-07 |

#### Decision Points

| Decision | Criteria | Yes Path | No Path |
|----------|----------|----------|---------|
| Any gaps remain? | At least one node with health_status untested or with active invalidation signals | Continue to scoring | Signal artifact generation readiness |
| Multiple nodes tied? | Two or more nodes with identical composite score | Tie-break procedure | Select the single highest scorer |

---

## PF-03: Tree Update from User Input

**Related Use Case:** UC-04
**Trigger:** User responds to a facilitation question
**End State:** Tree updated and persisted with new information

```mermaid
flowchart TD
    Start([Start: User provides answer])
    Parse[Parse answer against target node properties and attack patterns]
    UpdateProps[Update node properties with new information]
    EvalSource{"Node source was inferred?"}
    PromoteSource[Update source to user, evidence grade WEAK to FAIR]

    EvalHealth{"Answer reveals node is unnecessary?"}
    MarkFailed[Transition health_status to failed]
    EvalComplete{"All attack patterns addressed, no invalidations?"}
    MarkValidated[Transition health_status to validated]
    KeepTesting[Keep health_status at testing, note remaining gaps]

    NewConcepts{"Answer introduces new concepts?"}
    CreateNodes[Create new nodes, assign types, wire dependencies]
    ReApplyScale{"Scale constraints violated?"}
    ApplyConstraints[Re-apply scale constraints]
    Persist[Persist updated PRIMITIVE_TREE.jsonld]
    End([End: Tree updated])

    Start --> Parse
    Parse --> UpdateProps
    UpdateProps --> EvalSource
    EvalSource -->|Yes| PromoteSource
    EvalSource -->|No| EvalHealth
    PromoteSource --> EvalHealth
    EvalHealth -->|Yes| MarkFailed
    EvalHealth -->|No| EvalComplete
    MarkFailed --> NewConcepts
    EvalComplete -->|Yes| MarkValidated
    EvalComplete -->|No| KeepTesting
    MarkValidated --> NewConcepts
    KeepTesting --> NewConcepts
    NewConcepts -->|Yes| CreateNodes
    NewConcepts -->|No| Persist
    CreateNodes --> ReApplyScale
    ReApplyScale -->|Yes| ApplyConstraints
    ReApplyScale -->|No| Persist
    ApplyConstraints --> Persist
    Persist --> End
```

#### Decision Points

| Decision | Criteria | Yes Path | No Path |
|----------|----------|----------|---------|
| Node source was inferred? | source property is "inferred" and user has now confirmed or provided detail | Promote to "user" | Proceed to health evaluation |
| Answer reveals node unnecessary? | User explicitly says not needed, or invalidation signal matched | Mark failed | Evaluate completeness |
| All attack patterns addressed? | Every attack pattern for this node type has been addressed in the conversation; no active invalidation signals | Mark validated | Keep testing |
| New concepts introduced? | User's answer describes building blocks not in the current tree | Create new nodes and wire | Persist directly |
| Scale constraints violated? | New nodes push fan-out > 7 or depth > 5 | Re-apply constraints | Persist directly |

---

## PF-04: Completeness Verification

**Related Use Case:** UC-06
**Trigger:** Facilitation reaches Phase 5 (verify) or circuit breaker triggers
**End State:** Tree verified, gaps documented, ready for artifact generation

```mermaid
flowchart TD
    Start([Start: Verification triggered])
    PassCounter["Set pass = 1"]
    EvalAttacks[For each node: evaluate attack patterns against SRD content]
    EvalInvalidations[For each node: check for active invalidation signals]
    HasGaps{"Any gaps found?"}
    AllClear([Verdict: PASS — ready for artifact generation])

    ClassifyGaps{"Gap fixable from context?"}
    FixInline[Fix gap inline, record fix]
    SurfaceToUser[Present gap to user]
    UserInput[User provides information or accepts risk]
    UpdateTree[Update tree with fix or risk acceptance]

    IncrementPass["pass = pass + 1"]
    MaxPasses{"pass > 3?"}
    DocumentGaps[Document remaining gaps in COMPLETENESS_REPORT.md]
    Verdict([Verdict: GAPS_FOUND — proceed with documented gaps])

    Start --> PassCounter
    PassCounter --> EvalAttacks
    EvalAttacks --> EvalInvalidations
    EvalInvalidations --> HasGaps
    HasGaps -->|No| AllClear
    HasGaps -->|Yes| ClassifyGaps
    ClassifyGaps -->|Yes| FixInline
    ClassifyGaps -->|No| SurfaceToUser
    FixInline --> UpdateTree
    SurfaceToUser --> UserInput
    UserInput --> UpdateTree
    UpdateTree --> IncrementPass
    IncrementPass --> MaxPasses
    MaxPasses -->|Yes| DocumentGaps
    MaxPasses -->|No| EvalAttacks
    DocumentGaps --> Verdict
```

#### Decision Points

| Decision | Criteria | Yes Path | No Path |
|----------|----------|----------|---------|
| Any gaps found? | At least one node with unaddressed attack patterns or active invalidation signals | Classify and fix | Verdict PASS |
| Gap fixable from context? | Enough information exists in the conversation or codebase to fill the gap without user input | Fix inline | Surface to user |
| Max passes exceeded? | Pass counter > 3 | Document remaining gaps | Re-evaluate |
