# Sequence Diagrams: Primitive Tree Architecture

**Version:** 1.0.0
**Date:** 2026-03-16

---

## Summary

Two sequence diagrams capture the key interaction patterns: the end-to-end facilitation
session (from codebase mapping through tree synthesis, facilitation, and artifact generation)
and the single-turn facilitation exchange (the detailed interaction within one OODA spiral
pass).

---

## SD-01: End-to-End Facilitation Session

**Related Use Case:** UC-01 through UC-08
**Participants:** User, SRD Agent, Codebase Mapper, Tree Synthesiser, OODA Engine, Artifact Generator
**Trigger:** User initiates a requirements facilitation session

```mermaid
sequenceDiagram
    participant U as User
    participant Agent as SRD Agent
    participant Mapper as Codebase Mapper
    participant Synth as Tree Synthesiser
    participant OODA as OODA Engine
    participant ArtGen as Artifact Generator

    U->>Agent: Start facilitation session
    activate Agent

    Note over Agent,Mapper: Phase 1: Orientation
    Agent->>Mapper: Trigger codebase mapping (background)
    activate Mapper
    Agent->>U: Orientation questions (scope, audience, goals)
    U->>Agent: System description and context
    Mapper-->>Agent: CODEBASE_INDEX.json
    deactivate Mapper

    Note over Agent,Synth: Tree Synthesis
    Agent->>Synth: Synthesise tree from index + description + LLM knowledge
    activate Synth
    Synth-->>Agent: PRIMITIVE_TREE.jsonld (initial)
    deactivate Synth

    Note over Agent,OODA: Phases 2-3: Divergent + Convergent Exploration
    loop For each facilitation turn
        Agent->>OODA: Select next question from tree gaps
        activate OODA
        OODA-->>Agent: Target node + attack pattern + question
        deactivate OODA
        Agent->>U: Facilitation question
        U->>Agent: Answer
        Agent->>Agent: Update tree (properties, health status, new nodes)
        Agent->>Agent: Persist PRIMITIVE_TREE.jsonld

        opt Reflection checkpoint (every 3-4 turns)
            Agent->>U: Exec summary (progress by status, next target)
            U->>Agent: Confirmation or correction
        end
    end

    Note over Agent,OODA: Phase 5: Verify
    Agent->>OODA: Run completeness verification
    activate OODA
    OODA-->>Agent: Gaps found (if any)
    deactivate OODA

    opt Gaps require user input
        Agent->>U: Gap questions (one at a time)
        U->>Agent: Answers or risk acceptances
        Agent->>Agent: Update tree
    end

    Note over Agent,ArtGen: Phase 4: Artifact Generation
    Agent->>ArtGen: Generate artifacts (tree as checklist, conversation as content)
    activate ArtGen
    loop For each artifact
        ArtGen-->>Agent: Draft artifact
        Agent->>U: Present artifact for review
        U->>Agent: Approval or corrections
    end
    ArtGen-->>Agent: All artifacts complete
    deactivate ArtGen

    Note over Agent: Phase 6: Handover
    Agent->>Agent: Generate HANDOVER.md, COMPLETENESS_REPORT.md
    Agent->>U: Final summary: what's solid, what's thin, next steps
    deactivate Agent
```

#### Interaction Notes

| Step | From | To | Data | Notes |
|------|------|----|------|-------|
| 1 | User | Agent | Session start | User describes what they want to specify |
| 2 | Agent | Mapper | Trigger | Background task — does not block facilitation |
| 3 | Mapper | Agent | CODEBASE_INDEX.json | Overlaid at next reflection checkpoint, not announced |
| 4 | Agent | Synth | Index + description + LLM knowledge | Brownfield or greenfield path selected automatically |
| 5 | Synth | Agent | PRIMITIVE_TREE.jsonld | Initial tree with all nodes untested |
| 6 | OODA | Agent | Question selection | Composite scoring: fan-out, invalidations, phase, confidence |
| 7 | Agent | User | Question | Framed by attack pattern; includes educated assumption |
| 8 | User | Agent | Answer | Parsed against target node properties |
| 9 | Agent | ArtGen | Tree + conversation | Tree provides structure; conversation provides content |
| 10 | ArtGen | User | Artifacts | One at a time for review |

---

## SD-02: Single Facilitation Turn (OODA Detail)

**Related Use Case:** UC-03, UC-04
**Participants:** SRD Agent, OODA Engine, Primitive Tree, User
**Trigger:** Previous facilitation exchange completed

```mermaid
sequenceDiagram
    participant Agent as SRD Agent
    participant OODA as OODA Engine
    participant Tree as PRIMITIVE_TREE.jsonld
    participant U as User

    Agent->>Tree: Read current state
    activate Tree
    Tree-->>Agent: All nodes with statuses, dependencies, properties
    deactivate Tree

    Agent->>OODA: Observe: catalogue by health_status
    activate OODA
    OODA->>OODA: Orient: score candidates (fan_out*3 + invalidations*2 + phase*1 + confidence*1)
    OODA->>OODA: Decide: select highest scorer, break ties by topology then recency
    OODA-->>Agent: Target node ID, attack pattern, exploration domain
    deactivate OODA

    Agent->>Tree: Set target node health_status = testing
    activate Tree
    Tree-->>Agent: Confirmed
    deactivate Tree

    Agent->>U: Question framed by attack pattern + educated assumption
    activate U
    U-->>Agent: Answer
    deactivate U

    Agent->>Agent: Parse answer against node properties

    alt Answer fully specifies node
        Agent->>Tree: Update properties, set health_status = validated, source = user
    else Answer partially specifies
        Agent->>Tree: Update properties, keep health_status = testing, note gaps
    else Answer reveals node unnecessary
        Agent->>Tree: Set health_status = failed
        Agent->>Tree: Propagate: flag dependants for re-evaluation
    else Answer introduces new concepts
        Agent->>Tree: Create new nodes, wire dependencies, assign phases
        Agent->>Tree: Re-apply scale constraints if needed
    end

    Agent->>Tree: Persist updated tree
