# Process Flow Diagrams: Adaptive Coaching Annotations

## Summary

Two process flows govern the coaching system's behaviour: the OODA decision loop
(executed on every user answer) and the turn structure (the ordering of elements
in each agent response).

---

### PF-01: OODA Coaching Decision Loop

**Related Use Case:** UC-01
**Trigger:** User provides an answer to a facilitation question
**End State:** Agent has either produced a coaching annotation or decided to skip, and has updated the user model

```mermaid
flowchart TD
    Start([User provides answer])

    subgraph Observe["1. OBSERVE"]
        O1[Read user answer]
        O2[Identify domain-relevant primitives]
        O3[Catalogue: which are present, which absent]
    end

    subgraph Orient["2. ORIENT"]
        OR1{Any primitives absent?}
        OR2[Assess significance of each gap]
        OR3[Check for repeated absence pattern]
        OR4{Mindset skill threshold reached?}
    end

    subgraph Decide["3. DECIDE"]
        D1{Significance: relevant to current domain?}
        D2{Freshness: not coached in last 3 turns?}
        D3{User Level: genuine gap, not contextual?}
        D4{Cycling: different category from last 2 turns?}
        D5[Apply priority hierarchy to select ONE gap]
    end

    subgraph Act["4. ACT"]
        A1[Produce coaching annotation]
        A2[Record in journal: fired]
        A3[Skip annotation]
        A4[Record in journal: suppressed + reason]
    end

    UpdateModel[Update user model with demonstrated/absent primitives]
    End([Proceed to turn rendering])

    Start --> O1
    O1 --> O2
    O2 --> O3
    O3 --> OR1

    OR1 -->|No gaps| A3
    OR1 -->|Gaps found| OR2
    OR2 --> OR3
    OR3 --> OR4
    OR4 -->|Yes: escalate| D5
    OR4 -->|No: evaluate primitive| D1

    D1 -->|Not relevant| A3
    D1 -->|Relevant| D2
    D2 -->|Recently coached| A3
    D2 -->|Fresh| D3
    D3 -->|Contextual omission| A3
    D3 -->|Genuine gap| D4
    D4 -->|Same category recently| A3
    D4 -->|Different category| D5
    D5 --> A1

    A1 --> A2
    A3 --> A4
    A2 --> UpdateModel
    A4 --> UpdateModel
    UpdateModel --> End
```

#### Process Steps

| Step | Description | Actor/System | Inputs | Outputs | Business Rules |
|------|-------------|-------------|--------|---------|----------------|
| O1 | Read user's answer | Agent | Raw user text | Parsed content | -- |
| O2 | Identify which primitives apply to current domain | Agent | Current exploration domain, FR-04 mapping | Relevant primitive set (subset of S1-S7, A1-A7) | BR-04 |
| O3 | Check each relevant primitive against the answer | Agent | Answer content, relevant primitives | Present/absent classification per primitive | -- |
| OR1 | Determine if any relevant primitives are absent | Agent | Present/absent classifications | Binary: gaps exist or not | -- |
| OR2 | Assess significance of each absent primitive | Agent | Absent primitives, conversation history | Significance score per gap | -- |
| OR3 | Check if this primitive has been absent before | Agent | Journal history, current absent primitives | Repeated absence flag | -- |
| OR4 | Check mindset skill thresholds | Agent | Repeated absence counts, mindset trigger map | Mindset escalation flag | BR-08 |
| D1-D4 | Apply four Decide criteria | Agent | Gap data, journal history, user model | Coach or skip verdict | BR-05, BR-13 |
| D5 | Select highest-priority gap | Agent | All qualifying gaps | Single gap selection | BR-01, BR-03 |
| A1 | Render annotation | Agent | Selected gap, user's answer context | Blockquote annotation text | BR-02, BR-14 |
| A2/A4 | Record in journal | Agent | Decision outcome | Journal entry | BR-11, BR-12 |

#### Decision Points

| Decision | Criteria | Yes Path | No Path |
|----------|----------|----------|---------|
| Any primitives absent? | At least one domain-relevant primitive not demonstrated in answer | Proceed to significance assessment | Skip annotation |
| Mindset skill threshold? | 3+ absences of primitives associated with a mindset skill | Escalate to mindset skill coaching | Evaluate individual primitive |
| Significance? | Gap is relevant to the current exploration domain | Continue evaluation | Skip annotation |
| Freshness? | This primitive has not been coached in the last 3 turns | Continue evaluation | Skip annotation |
| User Level? | User model indicates this is a genuine gap, not contextual | Continue evaluation | Skip annotation |
| Cycling? | The annotation category (structural/analytical/mindset) differs from last 2 turns | Select gap and coach | Skip annotation |

---

### PF-02: Agent Turn Structure

**Related Use Case:** UC-01
**Trigger:** OODA loop completes; agent is ready to render response
**End State:** Agent has produced a well-ordered response with facilitation content and optional coaching

```mermaid
flowchart TD
    Start([OODA loop complete])

    P1[Position 1: Acknowledge and process user answer]
    P2{Primitive demonstrated well?}
    P2Y[Position 2: Pattern naming - name the concept inline, one sentence]
    P3{OODA verdict: coach?}
    P3Y["Position 3: Coaching annotation (blockquote)"]
    P4[Position 4: Next question + educated assumption]
    End([Response complete])

    Start --> P1
    P1 --> P2
    P2 -->|Yes| P2Y
    P2 -->|No| P3
    P2Y --> P3
    P3 -->|Yes| P3Y
    P3 -->|No| P4
    P3Y --> P4
    P4 --> End
```

#### Process Steps

| Step | Description | Actor/System | Inputs | Outputs | Business Rules |
|------|-------------|-------------|--------|---------|----------------|
| P1 | Acknowledge user's answer, process content | Agent | User answer, conversation history | Response text (acknowledgement) | -- |
| P2 | Check if user demonstrated a primitive worth naming | Agent | OODA Observe results | Pattern naming decision | BR-15 |
| P2Y | Produce pattern naming phrase | Agent | Demonstrated primitive | Inline text naming the concept | One sentence max |
| P3 | Check OODA verdict | Agent | OODA Act output | Coach or skip | BR-01, BR-13 |
| P3Y | Insert coaching annotation | Agent | Selected gap, annotation text | Blockquote annotation | BR-02, BR-14 |
| P4 | Produce next facilitation question with educated assumption | Agent | Exploration plan, conversation context | Question + inference | -- |

#### Ordering Constraints

| Constraint | Rule | Rationale |
|-----------|------|-----------|
| Annotation before question | Position 3 always precedes position 4 | Annotation references previous answer; question targets next topic |
| Pattern naming before annotation | Position 2 always precedes position 3 | Celebrate what was right before addressing what was missing |
| Reflection suppression | At reflection checkpoints, positions 2 and 3 are replaced by the reflection summary | Reflection and coaching serve conflicting cognitive functions |
