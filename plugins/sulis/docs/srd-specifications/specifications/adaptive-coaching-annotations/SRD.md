# Software Requirements Document: Adaptive Coaching Annotations

**Version:** 1.0
**Date:** 2026-03-13
**Status:** Draft
**Author:** Iain (facilitated by Requirements Analyst)

---

## Summary

This document specifies a behavioural enhancement to the requirements-analyst agent. The
enhancement adds adaptive coaching annotations -- visually distinct notes that appear when
the agent detects gaps in a user's analytical thinking during requirements facilitation.
The goal is to develop users' systems analysis and design skills through doing, not lecturing.

The enhancement operates across four layers: SA&D primitives provide the reference
framework, an OODA loop drives per-turn decision-making, coaching annotations deliver
the teaching, and mindset skills provide the meta-cognitive layer above individual
primitives.

This is not a new software system. It is a set of behavioural rules to be encoded in
the requirements-analyst agent prompt (`srd/agents/requirements-analyst.md`).

---

### 1. Introduction

#### 1.1 Purpose

This SRD specifies how the requirements-analyst agent should adaptively coach users in
systems analysis and design thinking during facilitation conversations. It defines the
exact primitives the agent tests against, the decision logic for when to coach, the
format of coaching output, and the rules governing frequency, priority, and calibration.

#### 1.2 Scope

**In scope:**
- SA&D primitive reference framework (structural and analytical)
- OODA loop decision engine for per-turn coaching evaluation
- Coaching annotation format and placement rules
- Priority rules for multiple simultaneous gaps
- User experience calibration (cold-start and ongoing)
- Coexistence rules with existing teaching mechanisms
- Turn ordering specification
- Exploration journal integration
- Five mindset skills as meta-cognitive coaching layer

**Out of scope:**
- Changes to the six-phase facilitation model itself
- Changes to artifact generation (Phase 4) behaviour
- Changes to completeness verification (Phase 5) behaviour
- General-purpose tutoring beyond SA&D primitives and mindset skills
- Assessment, scoring, or grading of user competency
- Persistent user profiles across separate projects

#### 1.3 Intended Audience

1. The agent prompt author -- to encode these rules in `srd/agents/requirements-analyst.md`
2. Anyone reviewing or maintaining the agent's facilitation behaviour

#### 1.4 Definitions and Acronyms

See [GLOSSARY.md](GLOSSARY.md) for the full domain glossary.

#### 1.5 References

| Document | Purpose |
|----------|---------|
| `srd/agents/requirements-analyst.md` | The agent prompt this enhancement modifies |
| `standards/COGNITIVE_LOAD.md` | Cognitive load principles governing annotation frequency |
| `standards/COACHING_WITHOUT_CONFLICT.md` | Coaching tenets governing annotation tone |
| `standards/CRITICAL_THINKING_STANDARD.md` | Critical thinking principles governing gap detection |

---

### 2. Overall Description

#### 2.1 Product Perspective

The requirements-analyst agent already has three teaching mechanisms: pattern naming
(celebrates demonstrated concepts), artifact explanation (explains diagram types during
Phase 4), and process narration (explains phase transitions). This enhancement adds a
fourth: coaching annotations that address gaps in analytical thinking.

The four mechanisms coexist. Pattern naming and coaching annotations are complementary
-- one rewards presence, the other addresses absence. They operate on independent limits
and can both appear in the same turn.

#### 2.2 Product Functions (Summary)

| Function | Description |
|----------|-------------|
| F-01 | SA&D Primitive Gap Detection -- identify which primitives are relevant to a user's answer and which are absent |
| F-02 | OODA Decision Loop -- evaluate each answer and decide whether to produce a coaching annotation |
| F-03 | Coaching Annotation Rendering -- produce a visually distinct blockquote annotation with correct placement |
| F-04 | User Model Calibration -- build and maintain a model of the user's experience level across the session |
| F-05 | Priority Selection -- when multiple gaps exist, select the single most valuable coaching opportunity |
| F-06 | Mindset Skill Coaching -- detect repeated primitive-gap patterns and coach the underlying thinking habit |
| F-07 | Journal Integration -- record coaching activity in the exploration journal for session continuity |

#### 2.3 User Classes and Characteristics

| Actor | Description | Frequency of Use | Technical Proficiency |
|-------|-------------|-------------------|----------------------|
| Novice User | Someone learning product management or systems analysis. May not know what a use case or state diagram is. | Every facilitation session | Low -- learning through doing |
| Experienced User | A PM, engineer, or domain expert who knows SA&D concepts and needs structured specifications, not teaching. | Every facilitation session | High -- needs organisation, not education |
| Agent Prompt Author | The person encoding these rules into the agent prompt. Reads this SRD to understand exact behaviour. | Once, during implementation | High |

#### 2.4 Operating Environment

The agent operates within Claude Code, producing markdown-formatted responses. Output
renders in CLI terminals with markdown support, VS Code, and GitHub. The coaching
annotation format (`> *text*`) depends on markdown rendering for visual distinction.
In environments without markdown rendering, the blockquote character (`>`) still
provides structural separation.

#### 2.5 Design and Implementation Constraints

- The enhancement is implemented as prompt instructions, not as code
- All behaviour must be expressible as natural language rules in the agent prompt
- The agent has no persistent storage between sessions beyond the exploration journal and agent memory files
- Cognitive load limits from `standards/COGNITIVE_LOAD.md` apply: max 5 choices, 4+/-1 chunks in working memory
- Coaching tenets from `standards/COACHING_WITHOUT_CONFLICT.md` apply: structural over personal, diagnostic over prescriptive, hypotheses over conclusions

#### 2.6 Assumptions and Dependencies

| Assumption | Impact if False | Validation Method |
|------------|----------------|-------------------|
| The agent can reliably detect primitive absence from natural language answers | Gap detection produces false positives/negatives, coaching fires incorrectly | Scenario testing with deliberate omissions |
| Users will notice and read blockquote annotations | Coaching has no effect; format needs to change | User feedback during pilot sessions |
| The existing six-phase facilitation model remains stable | Phase references in calibration rules become invalid | Review when facilitation model changes |
| One sentence is sufficient to convey a coaching concept | Annotations are too brief to teach; need expansion | User comprehension feedback |

---

### 3. External Interface Requirements

#### 3.1 User Interfaces

The coaching annotation is rendered as markdown within the agent's conversational response.

**Format specification:**

```
> *{Primitive or Skill Name} -- {One sentence explaining why this matters in the current context.}*
```

**Constraints:**
- Maximum 30 words in the annotation body
- The primitive or skill name appears first as the label
- The explanation ties the concept to the user's specific answer, not a generic definition
- The entire annotation is italic within a blockquote

**Example -- structural primitive gap:**
```
> *Exception paths -- When a user submits a form and the payment gateway is down, what does the system do? Most production incidents live at these failure points.*
```

**Example -- mindset skill gap:**
```
> *Failure-first thinking -- You've described what happens when things go right. Skilled analysts start with what goes wrong, because that's where the hard requirements hide.*
```

#### 3.2 Hardware Interfaces

Not applicable.

#### 3.3 Software Interfaces

Not applicable. The enhancement modifies agent prompt behaviour, not software integrations.

#### 3.4 Communications Interfaces

Not applicable.

---

### 4. System Features

#### 4.1 SA&D Primitive Gap Detection [F-01]

**Priority:** High

##### 4.1.1 Description

The agent maintains a reference framework of 14 SA&D primitives organised into two
levels. On each user answer, the agent identifies which primitives are relevant to the
topic being discussed and which are present or absent in the user's response.

##### 4.1.2 Functional Requirements

**FR-01: Structural Primitive Reference Table**

The agent MUST use the following structural primitives as its reference framework for
gap detection.

| ID | Primitive | What It Captures | Absence Signal |
|----|-----------|-----------------|----------------|
| S1 | Actor | A person, role, or system that interacts with the system | User describes features without saying who uses them |
| S2 | Use Case | An actor achieving a specific goal through the system | Capabilities described as feature lists, not goal-directed scenarios |
| S3 | Business Rule | A condition, validation, or calculation that governs behaviour | Behaviour described without specifying what constraints apply |
| S4 | Data Entity | A thing the system stores, transforms, or manages | Processes described without identifying what data is involved |
| S5 | State Lifecycle | An entity that moves through defined stages over time | Entities treated as static when they change status |
| S6 | Integration Boundary | A point where this system meets an external system | System described as self-contained when it depends on or feeds others |
| S7 | Process Flow | A sequence of steps with decisions and branches | Multi-step behaviour described as a single action |

**Acceptance criteria:** When a user's answer describes system behaviour, the agent can
identify which structural primitives from S1-S7 are relevant to the answer and which
are present or absent. Verified by scenario testing with answers that deliberately omit
each primitive.

**FR-02: Analytical Primitive Reference Table**

The agent MUST use the following analytical primitives to evaluate the completeness of
each structural primitive discussed.

| ID | Primitive | What It Tests For | Absence Signal |
|----|-----------|-------------------|----------------|
| A1 | Precondition | What must be true before something can happen | Flows described without entry criteria |
| A2 | Postcondition | What is true after something succeeds | Outcomes assumed but not stated explicitly |
| A3 | Exception Path | What happens when things go wrong | Only the happy path described |
| A4 | Alternate Path | Valid variations of the main flow | One path treated as the only path |
| A5 | Trigger | What initiates an action or transition | Things "just happen" without a clear cause |
| A6 | Constraint | A limit or boundary on behaviour | Requirements stated without bounds |
| A7 | Acceptance Criterion | How you know this requirement is satisfied | Requirements that cannot be tested or measured |

**Acceptance criteria:** When a user describes a structural primitive (e.g., a use case),
the agent can identify which analytical dimensions (A1-A7) are present and which are
absent. Verified by scenario testing with use case descriptions that deliberately omit
each analytical dimension.

**FR-03: Primitive Matrix Application**

The agent SHOULD apply the primitive matrix (structural x analytical) to identify
specific gaps. A gap is expressed as a cell in the matrix: "Use Case (S2) without
Exception Paths (A3)."

**Acceptance criteria:** The agent can express detected gaps as matrix coordinates
(e.g., S2xA3) in its internal reasoning, even though the coaching annotation uses
plain language.

**FR-04: Domain-Relevant Filtering**

The agent MUST only evaluate primitives that are relevant to the current exploration
domain. Not all 14 primitives apply to every answer.

| Exploration Domain | Primary Structural Primitives | Primary Analytical Primitives |
|-------------------|------------------------------|-------------------------------|
| Domain 1: Actors & Stakeholders | S1 Actor | A1 Precondition, A6 Constraint |
| Domain 2: Capabilities & Use Cases | S2 Use Case, S7 Process Flow | A1-A5 (all flow-related) |
| Domain 3: Business Rules & Logic | S3 Business Rule | A1 Precondition, A3 Exception, A6 Constraint, A7 Acceptance |
| Domain 4: Integrations & Data | S4 Data Entity, S6 Integration | A1 Precondition, A3 Exception, A5 Trigger |
| Domain 5: Process & Workflow | S5 State Lifecycle, S7 Process Flow | A1-A5 (all flow-related), A5 Trigger |
| Domain 6: Constraints & NFRs | S3 Business Rule | A6 Constraint, A7 Acceptance |

**Acceptance criteria:** When exploring Domain 1 (Actors), the agent does not flag
missing State Lifecycles (S5) as a gap. Primitives outside the current domain's
primary set are not evaluated for coaching purposes.

---

#### 4.2 OODA Decision Loop [F-02]

**Priority:** High

##### 4.2.1 Description

On every user answer, the agent executes a four-step decision loop to determine whether
to produce a coaching annotation. The loop also updates the agent's model of the user's
competency. See [diagrams/process-flows.md](diagrams/process-flows.md#pf-01).

##### 4.2.2 Functional Requirements

**FR-05: Observe Step**

The agent MUST read the user's answer and catalogue which domain-relevant primitives
are demonstrated (present in the answer) and which are absent.

- "Demonstrated" means the user's answer shows evidence of considering this primitive,
  even if not by its formal name. A user who says "but what if the API is down?" has
  demonstrated Exception Path (A3) without naming it.
- "Absent" means the primitive is relevant to the topic but the user's answer shows
  no evidence of considering it.

**Acceptance criteria:** Given a user answer about an order creation process that mentions
the happy path but not error cases, the agent identifies A3 (Exception Path) as absent
and S7 (Process Flow) as demonstrated.

**FR-06: Orient Step**

The agent MUST map each absent primitive to the current exploration domain and assess
its significance.

Significance factors:
1. How central is this primitive to the current topic? (An actor describing features
   without mentioning who uses them is highly significant; a missing acceptance
   criterion during early exploration is less significant.)
2. Has this primitive been absent in previous answers? (Repeated absence suggests a
   gap in the user's analytical approach, not a one-off omission.)
3. Is this primitive one the user has previously demonstrated? (If yes, the absence
   may be contextual, not a competency gap.)

**Acceptance criteria:** The agent can distinguish between a significant gap (user
repeatedly omits exception paths across multiple answers) and a contextual omission
(user mentioned exception paths last turn but did not repeat them this turn).

**FR-07: Decide Step**

The agent MUST evaluate whether to produce a coaching annotation based on four criteria,
all of which must be satisfied:

| Criterion | Rule | Rationale |
|-----------|------|-----------|
| Significance | The gap is relevant to the current domain and topic | Prevents coaching on tangential primitives |
| Freshness | This specific primitive has not been coached in the last 3 turns | Prevents overexposure and hammering |
| User Level | The user model indicates this is a genuine competency gap, not a contextual omission | Prevents coaching experienced users on concepts they know |
| Cycling | The agent has not already produced a coaching annotation on the same primitive category (structural or analytical) in the last 2 turns | Ensures variety in coaching topics |

If all four criteria are satisfied, the agent produces a coaching annotation. If any
criterion fails, the agent skips the annotation for this turn.

**Acceptance criteria:** Given that the agent coached on Exception Paths (A3) two turns
ago, the Freshness criterion fails and the agent does not coach on A3 again, even if it
is absent in the current answer.

**FR-08: Act Step**

When the Decide step produces a "coach" verdict:
- The agent selects the single highest-priority gap (see F-05, FR-14)
- The agent produces a coaching annotation in the specified format (see Section 3.1)
- The annotation is placed according to the turn ordering rules (see FR-16)

When the Decide step produces a "skip" verdict:
- No annotation appears
- The agent proceeds directly to the next facilitation question

In both cases, the OODA cycle updates the user model (see F-04).

**Acceptance criteria:** A "coach" verdict results in exactly one annotation in blockquote
format. A "skip" verdict results in no annotation. No turn ever contains more than one
coaching annotation.

---

#### 4.3 Coaching Annotation Rendering [F-03]

**Priority:** High

##### 4.3.1 Description

The coaching annotation is the visible output of the OODA loop. It appears as a visually
distinct blockquote in the agent's markdown response.

##### 4.3.2 Functional Requirements

**FR-09: Annotation Format**

Every coaching annotation MUST follow this exact format:

```
> *{Label} -- {Contextual explanation, maximum 30 words.}*
```

Where:
- `{Label}` is the primitive name or mindset skill name
- `{Contextual explanation}` ties the concept to the user's specific answer, not a
  generic definition
- The entire content is wrapped in italic markers within a blockquote

**Acceptance criteria:** Every annotation produced by the agent matches the format
`> *Label -- explanation.*` with the explanation under 30 words.

**FR-10: Contextual Grounding**

The annotation MUST reference the user's specific answer, not provide a textbook
definition.

- Good: `> *Exception paths -- You described what happens when the order is created successfully. What happens if the inventory check fails mid-order?*`
- Bad: `> *Exception paths -- Exception paths describe what happens when things go wrong in a system process.*`

**Acceptance criteria:** Every annotation contains a reference to the user's specific
answer or the specific topic being discussed, not a generic definition.

**FR-11: Tone Compliance**

Coaching annotations MUST comply with the seven coaching tenets from
`standards/COACHING_WITHOUT_CONFLICT.md`:

- Structural over personal: "There's a dimension we haven't explored" not "You missed..."
- Hypotheses over conclusions: "It might be worth considering..." not "You need to add..."
- Questions over statements: End with a question when possible

**Acceptance criteria:** No annotation uses the phrases "you need to," "you forgot,"
"you missed," "you should," or "that's wrong."

---

#### 4.4 User Model Calibration [F-04]

**Priority:** High

##### 4.4.1 Description

The agent builds and maintains a model of the user's SA&D experience level across the
facilitation session. The model starts at a calibrated baseline set during Phase 1
orientation and refines with each OODA cycle.
See [diagrams/state-diagrams.md](diagrams/state-diagrams.md#st-01).

##### 4.4.2 Functional Requirements

**FR-12: Cold-Start Calibration**

During Phase 1 (Orientation), the agent MUST infer the user's experience level from
how they frame their initial request. The agent uses three signals:

| Signal | Novice Indicator | Experienced Indicator |
|--------|-----------------|----------------------|
| Vocabulary | Uses informal language ("I want to build a thing that...") | Uses SA&D terminology ("I need to specify the use cases for...") |
| Framing | Describes features or ideas | Describes actors, flows, constraints, or integration points |
| Scope awareness | Describes everything as equally important | Distinguishes core from secondary, in-scope from out-of-scope |

Based on these signals, the agent sets an initial coaching level:

| Level | Label | Coaching Behaviour |
|-------|-------|-------------------|
| 1 | Novice | Annotations active from turn 1 at normal frequency. Pattern naming includes brief explanations. |
| 2 | Intermediate | Annotations active but frequency reduced. Pattern naming without explanation unless concept is new. |
| 3 | Experienced | Annotations suppressed by default. Only fire for genuinely surprising gaps -- primitives the user has not demonstrated across 5+ relevant opportunities. Pattern naming only for unusual concepts. |

The agent MUST communicate the calibration naturally during orientation. For experienced
users: "Based on how you've framed this, it sounds like you have experience with
requirements analysis. I'll focus on the specification rather than the methodology,
unless something comes up that's worth flagging." For novice users, no explicit
calibration statement -- the coaching simply begins.

**Acceptance criteria:** An experienced user who opens with "I need to specify the
integration contracts and state lifecycles for our payment service" receives Level 3
calibration. A novice who opens with "I have an idea for an app" receives Level 1.

**FR-13: Ongoing Refinement**

After each OODA cycle, the agent MUST update the user model:

- When a user demonstrates a primitive unprompted, increment that primitive's
  "demonstrated" counter
- When a user demonstrates a primitive after coaching, record it as "prompted
  demonstration" (weaker signal than unprompted)
- When a coaching annotation fires, record the primitive ID and turn number

The user model adjusts the coaching level over time:
- Level 1 to Level 2: User has demonstrated 5+ distinct primitives unprompted
- Level 2 to Level 3: User has demonstrated 10+ distinct primitives unprompted,
  including at least 3 analytical primitives (A1-A7)
- Level 3 to Level 2 (demotion): User consistently misses primitives they were
  expected to know (3+ misses on domain-relevant primitives in 5 consecutive turns)

**Acceptance criteria:** A user who starts at Level 1 and progressively demonstrates
more primitives sees coaching frequency decrease over the session. A user who starts at
Level 3 but reveals unexpected gaps sees coaching appear.

---

#### 4.5 Priority Selection [F-05]

**Priority:** High

##### 4.5.1 Description

When a user's answer reveals multiple absent primitives, the agent must select exactly
one for coaching. This feature defines the priority rules for that selection.

##### 4.5.2 Functional Requirements

**FR-14: Priority Hierarchy**

When multiple gaps are detected in a single answer, the agent MUST select one using
the following priority rules, applied in order:

1. **Level priority:** Structural primitives (S1-S7) take priority over analytical
   primitives (A1-A7). Rationale: structural gaps are more fundamental -- you cannot
   have exception paths for a use case that hasn't been identified.

2. **Domain relevance:** Within each level, the primitive most relevant to the current
   exploration domain wins. Use the domain-primitive mapping from FR-04 to determine
   relevance.

3. **Recency:** If two primitives have equal domain relevance, prefer the one that
   has not been coached recently. The primitive with the longest gap since last coaching
   (or never coached) wins.

4. **Repeat-gap signal:** If a primitive has been absent in 2+ previous answers without
   being coached yet, it takes priority over a first-time absence. Repeated absence
   is a stronger signal of a genuine gap.

**Acceptance criteria:** Given an answer missing Actor (S1), Exception Path (A3), and
Constraint (A6) while exploring Domain 2 (Capabilities), the agent selects S1 (Actor)
because it is structural, missing, and is not a first-time absence if previously
unaddressed. If S1 was coached last turn, the agent selects A3 (Exception Path) because
it is the most domain-relevant analytical primitive for capabilities.

**FR-15: Single Annotation Limit**

The agent MUST produce at most one coaching annotation per turn. This limit is
independent of pattern naming -- a turn may contain one pattern naming AND one coaching
annotation, but never two of either.

**Acceptance criteria:** No agent response ever contains two blockquote coaching
annotations. An agent response may contain one inline pattern naming phrase and one
blockquote coaching annotation.

---

#### 4.6 Turn Structure [F-03 continued]

**Priority:** High

##### 4.6.1 Description

The exact ordering of elements within each agent turn. This ensures coaching annotations
are clearly associated with the previous answer, not the next question.

##### 4.6.2 Functional Requirements

**FR-16: Turn Ordering**

Every agent response during Phases 2 and 3 MUST follow this ordering:

| Position | Element | Condition |
|----------|---------|-----------|
| 1 | Acknowledgement | Always. Process and respond to the user's previous answer. |
| 2 | Pattern naming | Optional. If the user demonstrated a primitive well, name it inline. One sentence maximum. |
| 3 | Coaching annotation | Optional. If a gap was detected and OODA decided to coach. Blockquote format, below the main response text. |
| 4 | Next question + educated assumption | Always. The facilitation question targeting the next topic, followed by an inference for the user to confirm or correct. |

**Constraints:**
- The coaching annotation (position 3) MUST appear AFTER the acknowledgement (position 1)
  and pattern naming (position 2), and BEFORE the next question (position 4)
- The annotation references the PREVIOUS answer. The question targets the NEXT topic.
  The visual separation (blockquote) and positional ordering make this unambiguous.
- Positions 2 and 3 are independent. A turn may have both, either, or neither.

**Acceptance criteria:** In every agent response, any coaching annotation appears after
the response to the previous answer and before the next question. No annotation appears
after the next question.

**FR-17: Reflection Checkpoint Integration**

At reflection checkpoints (every 3-4 exchanges), coaching annotations are suppressed.
The reflection itself consolidates understanding and serves a different cognitive
function. Coaching during a reflection creates conflicting cognitive demands.

**Acceptance criteria:** Agent responses that contain a reflection summary ("Let me make
sure I've got this right...") do not also contain a coaching annotation.

---

#### 4.7 Mindset Skill Coaching [F-06]

**Priority:** Medium

##### 4.7.1 Description

The five mindset skills represent meta-cognitive patterns above individual primitives.
They are coached when the agent detects a repeated pattern of missing the same TYPE of
primitive, suggesting a thinking habit gap rather than a single knowledge gap.

##### 4.7.2 Functional Requirements

**FR-18: Mindset Skill Definitions**

| ID | Skill | Description | Triggered By |
|----|-------|-------------|-------------|
| M1 | Boundary Thinking | The habit of asking "what is this, and what is this NOT?" | Repeated absence of S1 (Actor scope), S6 (Integration Boundary), A6 (Constraint) |
| M2 | Failure-First Thinking | The habit of starting with what can go wrong | Repeated absence of A3 (Exception Path) across 3+ answers |
| M3 | Actor Empathy | The habit of mentally inhabiting different perspectives | Repeated absence of S1 (Actor) or considering only one actor when multiple exist |
| M4 | Precision Reflex | The habit of pushing vague language toward specificity | Repeated absence of A7 (Acceptance Criterion), A6 (Constraint), or S3 (Business Rule) |
| M5 | Dependency Awareness | The habit of asking "what does this depend on?" | Repeated absence of A1 (Precondition), A5 (Trigger), S6 (Integration Boundary) |

**FR-19: Mindset Skill Trigger Threshold**

A mindset skill coaching annotation fires when:
- The associated primitives have been absent 3+ times across different answers
- The user has not demonstrated the mindset skill unprompted
- No mindset skill has been coached in the last 5 turns

Mindset skill annotations use the same blockquote format but reference the skill name
instead of a primitive name.

**Acceptance criteria:** After a user provides 3 answers describing happy paths without
mentioning failure cases, the agent coaches Failure-First Thinking (M2) rather than
Exception Path (A3) for the fourth instance.

**FR-20: Mindset Skill vs Primitive Priority**

When both a mindset skill and a primitive annotation are candidates for the same turn:
- Mindset skill annotations take priority over primitive annotations when the mindset
  trigger threshold has been reached
- A mindset skill annotation replaces (not supplements) the primitive annotation for
  that turn -- still one annotation maximum

**Acceptance criteria:** When the agent could coach either Exception Path (A3) or
Failure-First Thinking (M2), and the M2 threshold has been reached, M2 is coached.

---

#### 4.8 Journal Integration [F-07]

**Priority:** Medium

##### 4.8.1 Description

Coaching activity is recorded in the exploration journal for session continuity and
completeness verification.

##### 4.8.2 Functional Requirements

**FR-21: Coaching Log Entry**

After each OODA cycle, the agent MUST record in the exploration journal:

```
**Coaching:** {Primitive ID} {fired|suppressed} — {reason}
```

- If fired: record the primitive ID, the annotation text (compressed), and which
  absence signal triggered it
- If suppressed: record why (freshness, user level, cycling, or no gap detected)

**FR-22: Demonstration Tracking**

When a user demonstrates a primitive unprompted (not in response to coaching), the
agent MUST record:

```
**Demonstrated:** {Primitive ID} (unprompted, turn {N})
```

This feeds the user model refinement (FR-13) and enables session continuity.

**FR-23: Compressed Storage**

Journal entries for coaching MUST use compressed form to manage token budget:
- Primitive ID (e.g., S2, A3) not full name
- Fired/suppressed as single word
- Reason in 10 words or fewer

**Acceptance criteria:** Coaching journal entries add no more than 2 lines per turn
to the exploration journal.

---

### 5. Non-Functional Requirements

See [NFR.md](NFR.md) for full non-functional requirements specification.

| Category | Summary |
|----------|---------|
| Performance | Annotations add no more than 30 words per turn |
| Scalability | System handles sessions of 60+ turns without degradation in coaching quality |
| Consistency | Same gap pattern produces same coaching decision across sessions |
| Cognitive Load | Maximum one annotation per turn; suppressed during reflections |

---

### 6. Diagrams

| Diagram Type | File | Purpose |
|-------------|------|---------|
| Process Flow | [diagrams/process-flows.md](diagrams/process-flows.md) | OODA loop decision flow, turn structure flow |
| State | [diagrams/state-diagrams.md](diagrams/state-diagrams.md) | User model lifecycle |

---

### 7. Traceability Matrix

| Goal | Use Cases | Diagrams | NFRs | Features |
|------|-----------|----------|------|----------|
| G-01: Develop SA&D skills through facilitation | UC-01, UC-02, UC-03 | PF-01, PF-02 | NFR-P01, NFR-CL01 | F-01, F-02, F-03 |
| G-02: Adapt coaching to user experience level | UC-02 | ST-01 | NFR-CON01 | F-04 |
| G-03: Avoid cognitive overload from coaching | UC-01, UC-03 | PF-01 | NFR-CL01, NFR-CL02 | F-05, F-03 |
| G-04: Maintain session continuity for coaching | UC-04 | -- | NFR-S01 | F-07 |
| G-05: Coexist with existing teaching mechanisms | UC-01 | PF-02 | NFR-CL02 | F-03, F-05 |

---

### 8. Use Cases

#### UC-01: Adaptive Gap Coaching During Facilitation

**Actor:** Novice User
**Goal:** Receive coaching on missing SA&D primitives as a natural part of the facilitation conversation
**Priority:** High

**Preconditions:**
- Facilitation session is in Phase 2 (Divergent Exploration) or Phase 3 (Convergent Specification)
- User model has been initialised during Phase 1

**Postconditions (success):**
- User has received coaching on relevant SA&D primitives they were not considering
- Coaching appeared as visually distinct annotations that did not disrupt facilitation flow
- User model has been updated to reflect demonstrated and absent primitives

**Postconditions (failure):**
- Agent produced an annotation that was irrelevant to the topic (false positive)
- Agent missed a significant gap (false negative)
- Coaching disrupted the facilitation conversation flow

##### Basic Flow

| Step | Actor | System |
|------|-------|--------|
| 1 | User provides answer to facilitation question | |
| 2 | | Agent executes OODA Observe: catalogues primitives present/absent in answer |
| 3 | | Agent executes OODA Orient: maps gaps to current domain, assesses significance |
| 4 | | Agent executes OODA Decide: evaluates significance, freshness, user level, cycling |
| 5 | | Agent executes OODA Act: produces coaching annotation in blockquote format |
| 6 | | Agent renders response: acknowledgement, pattern naming (if applicable), annotation, next question + assumption |
| 7 | User reads response, absorbs or skips annotation, answers next question | |

##### Alternate Flows

**AF-01: No gap detected**
- Branches from: Step 4
- Condition: OODA Decide finds no absent primitives relevant to current domain

| Step | Actor | System |
|------|-------|--------|
| 4.1 | | Agent skips annotation, proceeds to next question |

- Rejoins: Step 6 (without annotation in position 3)

**AF-02: Gap detected but suppressed**
- Branches from: Step 4
- Condition: OODA Decide finds a gap but freshness, cycling, or user level criterion fails

| Step | Actor | System |
|------|-------|--------|
| 4.1 | | Agent records suppression reason in journal |
| 4.2 | | Agent skips annotation, proceeds to next question |

- Rejoins: Step 6 (without annotation in position 3)

**AF-03: Pattern naming coexists with annotation**
- Branches from: Step 2
- Condition: User's answer both demonstrates one primitive well AND omits another

| Step | Actor | System |
|------|-------|--------|
| 2.1 | | Agent identifies demonstrated primitive for pattern naming |
| 2.2 | | Agent identifies absent primitive for coaching annotation |

- Rejoins: Step 3 (both pattern naming and annotation will appear in response)

##### Exception Flows

**EF-01: Reflection checkpoint turn**
- Branches from: Step 2
- Condition: This turn is a reflection checkpoint (every 3-4 exchanges)

| Step | Actor | System |
|------|-------|--------|
| 2.1 | | Agent suppresses coaching annotation for this turn |
| 2.2 | | Agent produces reflection summary instead |

- Result: No annotation this turn. OODA cycle still runs to update user model.

##### Business Rules

| ID | Rule | Applies To |
|----|------|------------|
| BR-01 | Maximum one coaching annotation per turn | Step 5 |
| BR-02 | Annotations reference previous answer, not next question | Step 5 |
| BR-03 | Structural primitives (S-level) take priority over analytical (A-level) | Step 4 |
| BR-04 | Domain-relevant primitives only; non-relevant primitives are not evaluated | Step 3 |
| BR-05 | Same primitive not coached within 3 turns | Step 4 |

---

#### UC-02: Cold-Start Calibration

**Actor:** Any User
**Goal:** Begin the session with a coaching level appropriate to the user's experience
**Priority:** High

**Preconditions:**
- Session is in Phase 1 (Orientation)
- No user model exists yet for this session

**Postconditions (success):**
- User model initialised at Level 1, 2, or 3
- For experienced users, calibration communicated naturally
- Coaching frequency set appropriately from the first facilitation turn

##### Basic Flow

| Step | Actor | System |
|------|-------|--------|
| 1 | User provides initial request describing what they want to specify | |
| 2 | | Agent evaluates vocabulary, framing, and scope awareness signals |
| 3 | | Agent sets initial coaching level (1, 2, or 3) |
| 4 | | Agent communicates calibration naturally during orientation response |
| 5 | | User model initialised; coaching behaviour set for Phase 2 |

##### Alternate Flows

**AF-01: Ambiguous signals**
- Branches from: Step 2
- Condition: User's initial request contains mixed signals (e.g., informal language but mentions specific technical concepts)

| Step | Actor | System |
|------|-------|--------|
| 2.1 | | Agent defaults to Level 2 (intermediate) |
| 2.2 | | Agent monitors first 3 answers closely for rapid recalibration |

- Rejoins: Step 3

##### Business Rules

| ID | Rule | Applies To |
|----|------|------------|
| BR-06 | Default to Level 2 when signals are ambiguous | Step 2.1 |
| BR-07 | Communicate calibration for Level 3 users only; Level 1 begins coaching without announcement | Step 4 |

---

#### UC-03: Mindset Skill Escalation

**Actor:** Novice User
**Goal:** Receive coaching on a meta-cognitive thinking pattern when individual primitive gaps form a pattern
**Priority:** Medium

**Preconditions:**
- Session is in Phase 2 or Phase 3
- A mindset skill trigger threshold has been reached (3+ absences of associated primitives)

**Postconditions (success):**
- User has received coaching on the underlying thinking pattern, not just the individual primitive
- User model records mindset skill coaching

##### Basic Flow

| Step | Actor | System |
|------|-------|--------|
| 1 | User provides answer missing primitives associated with a mindset skill for the 3rd+ time | |
| 2 | | Agent detects repeated pattern in OODA Orient step |
| 3 | | Agent determines mindset skill threshold is met |
| 4 | | Agent produces mindset skill annotation instead of primitive annotation |
| 5 | | Agent records mindset skill coaching in journal |

##### Business Rules

| ID | Rule | Applies To |
|----|------|------------|
| BR-08 | Mindset skill threshold: 3+ absences of associated primitives | Step 3 |
| BR-09 | No mindset skill coaching within 5 turns of last mindset skill coaching | Step 3 |
| BR-10 | Mindset skill annotation replaces, not supplements, primitive annotation | Step 4 |

---

#### UC-04: Session Continuity Via Journal

**Actor:** Agent (automated)
**Goal:** Record coaching activity so the agent can resume with context in a new session
**Priority:** Medium

**Preconditions:**
- Exploration journal exists for this specification

**Postconditions (success):**
- Every OODA cycle is recorded (fired or suppressed)
- Demonstrated primitives are tracked with turn numbers
- A new session can reconstruct the user model from journal entries

##### Basic Flow

| Step | Actor | System |
|------|-------|--------|
| 1 | | Agent completes OODA cycle |
| 2 | | Agent writes compressed coaching log entry to journal |
| 3 | | If primitive demonstrated unprompted, agent writes demonstration entry |
| 4 | | Journal entries accumulate across the session |

##### Business Rules

| ID | Rule | Applies To |
|----|------|------------|
| BR-11 | Journal entries use compressed form (primitive ID, fired/suppressed, reason in <=10 words) | Step 2 |
| BR-12 | Maximum 2 lines per turn added to journal for coaching | Step 2-3 |

---

### 9. Business Rules Summary

| ID | Rule | Category | Applies To |
|----|------|----------|------------|
| BR-01 | Maximum one coaching annotation per turn | Frequency | F-03, F-05 |
| BR-02 | Annotations reference previous answer, not next question | Placement | F-03 |
| BR-03 | Structural primitives (S-level) take priority over analytical (A-level) when selecting which gap to coach | Priority | F-05 |
| BR-04 | Only domain-relevant primitives are evaluated for coaching | Scope | F-01 |
| BR-05 | Same primitive not coached within 3 turns (freshness rule) | Frequency | F-02 |
| BR-06 | Default to Level 2 (intermediate) when experience signals are ambiguous | Calibration | F-04 |
| BR-07 | Communicate calibration naturally for experienced users only; novice coaching begins without announcement | Calibration | F-04 |
| BR-08 | Mindset skill threshold: 3+ absences of associated primitives across different answers | Escalation | F-06 |
| BR-09 | No mindset skill coaching within 5 turns of last mindset skill coaching | Frequency | F-06 |
| BR-10 | Mindset skill annotation replaces, not supplements, primitive annotation for that turn | Priority | F-06 |
| BR-11 | Journal entries use compressed form: primitive ID, fired/suppressed, reason in 10 words or fewer | Storage | F-07 |
| BR-12 | Maximum 2 journal lines per turn for coaching activity | Storage | F-07 |
| BR-13 | Coaching annotations suppressed during reflection checkpoints | Frequency | F-02, F-03 |
| BR-14 | Annotation body maximum 30 words | Format | F-03 |
| BR-15 | One pattern naming AND one coaching annotation per turn maximum; never two of either | Coexistence | F-03, F-05 |
| BR-16 | Coaching scope limited to SA&D primitives (S1-S7, A1-A7) and five mindset skills (M1-M5). Technical concepts coached only when directly instantiating a primitive. | Scope | F-01, F-06 |

---

### 10. Appendices

#### 10.1 Exploration Journal
See [EXPLORATION_JOURNAL.md](../facilitation-pedagogy/EXPLORATION_JOURNAL.md) for the facilitation record.

#### 10.2 Handover Brief
See [HANDOVER.md](HANDOVER.md) for the execution agent handover.
