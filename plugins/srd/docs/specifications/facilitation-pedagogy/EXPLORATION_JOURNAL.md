# Exploration Journal: Facilitation Pedagogy Enhancement

**Date:** 2026-03-13
**Goal:** Enhance the requirements-analyst agent's dialog flow to subtly explain the reasoning behind each question, developing users' product management and systems analysis skills through doing.
**Scope:** Behavioural change to an existing AI agent's facilitation approach — not a new software system.
**Audience:** The user is the author/maintainer of the requirements-analyst agent. They understand the agent's current design intimately and want to improve its pedagogical effectiveness.

---

## Session Log

### Turn 1 — Phase 1 (Orientation)

**Initial assessment:**
The user wants to change how the requirements-analyst agent facilitates conversations. Currently, the agent asks questions following the six-phase model with pattern naming as the primary teaching mechanism (one teaching moment per turn, tied to what the user just described). The enhancement request is to go further — not just naming patterns after the fact, but explaining *why* each question is being asked, so users learn the analytical thinking behind requirements gathering, not just the vocabulary.

**Key tension to explore:**
- "Subtly" is the operative word. The user does not want the agent to become a lecturer. The explanation needs to feel like a natural part of the conversation, not a parenthetical aside that breaks flow.
- The current agent prompt already has teaching mechanisms (pattern naming, artifact explanation, process narration). This enhancement would add a fourth: question rationale.
- There is a design tension between cognitive load (adding explanation increases load per turn) and learning value (understanding *why* a question matters builds transferable skill).

**Coverage:** No domains explored yet. This is orientation.

### Turn 2 — Phase 2 (Divergent Exploration)

**Question asked:** What does a good learning moment look like from the user's side? (Domain 2: Capabilities — understanding the desired outcome)

**Key points from answer:**
- The goal is to encourage a *mindset*, not teach vocabulary or process steps
- The mindset includes: critical thinking, discerning what is important vs. not, recognising analytical patterns
- The user framed this as "mindset skills and patterns you'd expect them to have" — implying there is a defined set of thinking competencies a requirements analyst uses
- This is distinct from the existing pattern-naming mechanism, which labels things after the fact. The enhancement is about developing the *thinking* that leads to good analysis.

**Patterns detected:**
- This is a competency model question — what are the specific thinking skills that constitute "thinking like a requirements analyst"? We need to enumerate these before we can design how to teach them.
- The word "subtly" from the original request combined with "through doing" suggests the teaching mechanism should be embedded in the question itself, not added as a separate explanation.

**New glossary terms:**
- "Mindset skills" — the analytical thinking patterns a requirements analyst uses (as distinct from vocabulary or process knowledge)

**Coverage assessment:**
- Domain 1 (Actors): Partially covered — we know the learner persona exists but need more on their experience level range
- Domain 2 (Capabilities): Starting to form — the core capability is "develop mindset skills through facilitation"
- Domains 3-6: Untouched

### Turn 3 — Phase 2 (Divergent Exploration)

**Question asked:** What are the thinking habits that set a skilled requirements analyst apart? (Domain 2: Capabilities — enumerating the mindset skills to be taught)

**Key points from answer:**
- User turned the question back: "What do you think?" — signalling they want the agent's perspective as a starting point to refine.
- This is a collaborative framing moment. The user trusts the agent's domain knowledge here and wants a hypothesis to react to rather than building from scratch.

**Response approach:**
- Per Tenet 5 (hypotheses over conclusions), present a candidate list of mindset skills framed as a hypothesis
- Per Tenet 7 (room to step up), leave explicit room for the user to reshape
- Draw from the standards already embedded in the agent (Critical Thinking, Cognitive Load, Coaching Without Conflict) and from what skilled analysts actually do
- Ask the user to refine: what is missing, what does not belong, what is the priority order

### Turn 4 — Phase 2 (Divergent Exploration)

**Agent response:** Presented hypothesis of 5 mindset skills: boundary thinking, failure-first thinking, actor empathy, precision reflex, dependency awareness. Asked user to reshape.

**Key points from answer:**
- User accepted all five as a good starting point to test
- No additions or removals — the list landed well
- The five mindset skills are now our working model

**Agreed mindset skills:**
1. Boundary thinking — "what is this, and what is this not?"
2. Failure-first thinking — "what could go wrong here?"
3. Actor empathy — mentally inhabiting different perspectives
4. Precision reflex — pushing vague language toward specificity
5. Dependency awareness — "what does this depend on, and what depends on this?"

**Next thread to follow:** HOW these get surfaced. The "what" is defined; the "how" is the core design challenge. Need to understand what "subtle" means in practice — the delivery mechanism.

**Coverage assessment:**
- Domain 1 (Actors): Partially covered — learner persona identified, experience range not yet explored
- Domain 2 (Capabilities): Well-covered — five mindset skills defined, core goal clear
- Domain 3 (Business Rules): Untouched — when/how to surface each skill, frequency rules, phase-dependent behaviour
- Domain 4 (Integrations): Untouched — how this interacts with existing teaching mechanisms
- Domain 5 (Process/Workflow): Untouched — timing within the facilitation flow
- Domain 6 (Constraints): Untouched — cognitive load limits, subtlety constraints

### Turn 5 — Phase 2 (Divergent Exploration)

**Agent response:** Presented two approaches (A: explain before question, B: name skill after answer) and asked which felt closer to "subtle."

**Key points from answer:**
- User proposed a third approach: **visual separation**
- The facilitation question stands alone as primary content
- Below it, in visually distinct formatting (different colour/style), a coaching annotation explains the thinking pattern
- The annotation is opt-in by nature — it is present but does not interrupt the flow
- This is a "margin note" or "annotation" pattern — the coaching layer sits alongside the facilitation layer, not interleaved with it

**Patterns detected:**
- This is a dual-layer information architecture: the facilitation conversation is the primary channel, the coaching annotations are a secondary channel. The user can engage with one or both.
- In a CLI/markdown context, "different colour" translates to formatting conventions: blockquotes (`>`), italic text, dimmed/grey text (if terminal supports it), or a consistent visual marker.
- This approach elegantly solves the cognitive load tension: the question itself carries no extra load, and the annotation is available but ignorable.

**New glossary terms:**
- "Coaching annotation" — a visually distinct note beneath a facilitation question that names the mindset skill being exercised and explains the reasoning behind the question
- "Dual-layer facilitation" — the pattern of running two parallel information channels (facilitation + coaching) with visual separation

**Questions opened by this answer:**
- Frequency: does every question get an annotation, or only some?
- Content: does the annotation name the skill, explain the reasoning, pose a meta-question, or some combination?
- Format: what specific markdown/terminal formatting achieves the visual separation?
- Interaction with existing teaching: how does this relate to pattern naming, which currently happens inline?

**Coverage assessment:**
- Domain 2 (Capabilities): Strong — mindset skills defined, delivery mechanism concept emerging
- Domain 3 (Business Rules): Opening — need frequency rules, content rules for annotations
- Domain 4 (Integrations): Opening — interaction with existing teaching mechanisms
- Domain 5 (Process/Workflow): Still thin — timing across phases
- Domain 6 (Constraints): Opening — cognitive load implications becoming clearer

### Turn 6 — Phase 2 (Divergent Exploration)

**Agent response:** Showed a concrete example of the blockquote+italic formatting pattern. Asked about frequency spectrum.

**Key points from answer:**
- User confirmed the visual format with "yes, exactly" — the blockquote+italic pattern is the right approach
- User did not explicitly answer the frequency question — the confirmation was about the format, not about how often annotations appear
- Need to re-ask frequency more concretely

**Confirmed design decisions:**
- Format: blockquote with italic text beneath the facilitation question
- Structure: skill name in bold/label position, followed by one-sentence reasoning
- The example that landed: `> *Failure-first thinking — Most production incidents live at the points where things can go wrong...*`

### Turn 7 — Phase 2 (Divergent Exploration)

**Agent response:** Presented three frequency options (A: every question, B: first encounter only, C: shift-based tapering). Asked which felt right.

**Key points from answer:**
- Cycle through mindset skills — rotate, don't hammer one repeatedly
- Risk of overexposure if too frequent
- **Critical design pivot:** annotations should be triggered by the QUALITY of the user's answer, not pre-attached to questions
- "If the answers aren't right enough or not on point, then it might be a coaching opportunity"
- This means the coaching annotation is RESPONSIVE, not SCHEDULED

**Design pivot — Adaptive coaching annotations:**
- The agent asks a facilitation question (no annotation at this point)
- The user answers
- The agent evaluates the answer: did it demonstrate the relevant mindset skill, or miss it?
- If the answer is thin or missing a dimension, the agent's FOLLOW-UP includes a coaching annotation explaining the mindset skill the user could have applied
- If the answer already demonstrates the skill, no annotation needed — the user is already thinking that way
- This is fundamentally different from the earlier model where annotations were attached to questions. Now they are attached to GAPS IN ANSWERS.

**Implications:**
- The agent needs gap-detection logic: what signals in a user's answer indicate missing mindset skills?
- Each mindset skill has characteristic "absence signals" — patterns in answers that suggest the thinking was not applied
- The annotation appears on the follow-up question, not on the original question
- This maps naturally to how real coaching works: you observe the student's work, then coach based on what you see

**New glossary term update:**
- "Coaching annotation" — redefined: a visually distinct note that appears when the agent detects a gap in the user's analytical thinking, naming the mindset skill that would have caught the gap

**Coverage assessment:**
- Domain 3 (Business Rules): Major progress — the trigger mechanism is defined (adaptive, gap-based)
- Need to explore: what are the specific gap signals for each of the five mindset skills?
- Domain 4 (Integrations): Still need to explore interaction with existing teaching mechanisms
- Domain 5 (Process/Workflow): Need to explore how this plays across phases

### Turn 8 — Phase 2 (Divergent Exploration) — Reflection Checkpoint

**Agent response:** Summarised the adaptive coaching model (5-step flow: ask, answer, evaluate, annotate if gap, skip if demonstrated). Asked for confirmation.

**Key points from answer:**
- User confirmed the adaptive model
- **Scope expansion:** coaching annotations should NOT be limited to the five mindset skills
- Also cover: technical concepts, frameworks, conventions
- "If there is an opportunity to clarify a technical concept or a framework or convention, I don't want to miss that opportunity"
- User referenced design standards document at `/Users/iain/Documents/repos/platform/methodology/delivery/design/STANDARDS.md`

**Analysis of scope expansion:**
The coaching annotation system now has THREE categories of teachable content:
1. **Mindset skills** (5 defined) — the analytical thinking patterns
2. **Technical concepts** — things like state machines, MECE, falsifiability, idempotency, eventual consistency
3. **Frameworks and conventions** — things like the EAST framework (DS-08), anti-pattern structures, substitution tests, specificity gradients

This is broader than originally scoped but still bounded. The agent does not need to teach ALL technical concepts — only those that are relevant to the conversation at hand. The trigger mechanism (gap-based, adaptive) naturally limits the scope: the annotation only fires when the user's answer reveals a gap that a specific concept would address.

**Reference: Design Standards patterns relevant to coaching:**
- Anti-pattern structure (What / Why it's wrong / What to do instead) — could inform annotation structure
- Substitution test — a thinking tool worth teaching
- Specificity gradient — knowing how specific vs generic something is
- EAST framework — evidence-based behavioural design
- Coherence checking — do things work together, not just individually

**Key design question emerging:** The agent cannot carry an encyclopedia of concepts. It needs a way to draw from its existing knowledge (standards, domain concepts, technical patterns) and produce annotations that are contextually relevant. This is more about the STRUCTURE of annotations than about pre-defining every possible annotation.

**Coverage assessment:**
- Domain 2 (Capabilities): Expanded — three categories of teachable content
- Domain 3 (Business Rules): Need to define the annotation structure that works across all three categories
- Domain 4 (Integrations): Opening — how does this interact with existing pattern naming?
- Domain 5 (Process/Workflow): Still thin

### Turn 9 — Phase 2 (Divergent Exploration)

**Agent response:** Reflected back the three-category model. Proposed annotation structure question (name/relevance/application vs fluid).

**Key points from answer:**
- The challenge is FRAMING — precise instructions so the agent reliably produces good annotations
- **Primitives as anchor points:** break capabilities into composable building blocks
- **OODA spiral:** Observe-Orient-Decide-Act for breakpoints and re-evaluation as certainty grows

**OODA mapping to coaching annotation flow:**
1. **Observe:** Read the user's answer. What dimensions are present? What is absent?
2. **Orient:** Map gaps to coaching categories (mindset skill / technical concept / convention)
3. **Decide:** Is this a coaching opportunity? Consider: cycling, significance, user model
4. **Act:** Produce annotation or skip
5. **Spiral:** Each pass builds certainty about the user's level. Coaching adapts.

**Primitives hypothesis:**
- Observe primitive: gap-detection
- Orient primitive: concept-matching
- Decide primitive: frequency-control
- Act primitive: annotation-rendering
- Learn primitive: user-model-updating

**New glossary terms:**
- "OODA spiral" — iterative Observe-Orient-Decide-Act loop with increasing certainty
- "Coaching primitive" — fundamental building block of the coaching annotation system

**Coverage assessment:**
- Domain 3 (Business Rules): Strong — OODA provides the decision framework
- Domain 5 (Process/Workflow): Opening — OODA spiral maps to facilitation phases
- Need to explore: what are the primitives exactly? What does each one need?

### Turn 10 — Phase 2 (Divergent Exploration) — Reflection Checkpoint

**Significant reframe:** User clarified that "primitives" means the primitives of SYSTEMS ANALYSIS AND DESIGN, not primitives of the coaching mechanism.

**Key insight:**
- SA&D has fundamental building blocks: actors, use cases, state transitions, business rules, integration contracts, data flows, preconditions, postconditions, exception flows, etc.
- These primitives form the REFERENCE FRAMEWORK that the agent tests user answers against
- When a user's answer is missing a primitive that should be present, THAT is the coaching opportunity
- The primitive names become the vocabulary for coaching annotations
- Example: user describes a workflow but doesn't mention state transitions → "state lifecycle" primitive is missing → coaching annotation fires

**Why this matters:**
This makes gap detection concrete and implementable. Instead of "detect analytical gaps" (vague), the instruction becomes "check which SA&D primitives are relevant to this answer and which are absent" (specific). The agent already knows these primitives — the six MECE exploration domains are organized around them. This enhancement makes them EXPLICIT as a coaching reference framework.

**Connection to existing agent structure:**
The six MECE domains already implicitly contain the primitives:
- Domain 1 (Actors/Stakeholders): actors, roles, goals, indirect stakeholders
- Domain 2 (Capabilities/Use Cases): use cases, flows, alternate paths, scope boundaries
- Domain 3 (Business Rules): validations, calculations, conditions, constraints
- Domain 4 (Integrations/Data): integration contracts, data sources, data transformations
- Domain 5 (Process/Workflow): state transitions, sequences, handoffs, timeouts
- Domain 6 (Constraints/NFRs): performance targets, security, scalability, availability

The primitives are a FINER GRAIN than the domains — they are the individual building blocks within each domain.

**Coverage assessment:**
- Domain 2 (Capabilities): Strong — the SA&D primitives ARE the core capability
- Domain 3 (Business Rules): Strong — primitives provide the gap-detection framework, OODA provides the decision loop
- Domain 4 (Integrations): Need to explore — how does this interact with existing pattern naming?
- Domain 5 (Process/Workflow): Progressing — OODA spiral governs timing
- All six exploration domains for the ENHANCEMENT are now at least partially covered. Approaching Phase 3 readiness.

### Turn 11 — Phase 2 (Divergent Exploration) — Convergence Point

**Agent response:** Proposed two-level primitive split (structural + analytical). Asked if this matches user's thinking.

**Key points from answer:**
- User confirmed the two-level split
- Described the full system: "primitives get encoded, then we use the OODA loop to work through them, assisting the user where possible to suggest and validate assumptions, to work towards the end outcome of having a solution design and providing coaching moments"
- Key phrase: "assisting the user where possible to suggest and validate assumptions" — the agent is ACTIVE, not passive. It suggests, proposes, validates — not just asks.
- The end outcome remains the SRD and artifacts
- Coaching moments are a natural byproduct of the OODA loop running against the primitives

**Full system model now clear:**
1. SA&D primitives encoded as explicit reference framework (structural + analytical)
2. OODA loop drives through them on each exchange (observe answer → orient against primitives → decide to coach or not → act)
3. Agent actively suggests and validates (not just passive questioning)
4. Coaching annotations appear in blockquote format when gaps detected
5. Frequency governed by cycling + overexposure avoidance
6. Five mindset skills provide the meta-cognitive layer above the primitives
7. End outcome: solution design (SRD + artifacts) with coaching along the way

**Remaining areas to explore before Phase 3:**
- How does this interact with the EXISTING teaching mechanisms (pattern naming, artifact explanation, process narration)?
- Does the existing "one teaching moment per turn" rule change?
- How does the agent adapt for experienced users who already know the primitives?
- Are there any constraints we haven't discussed (cognitive load limits, session length impacts)?

**Saturation signal check:**
- Last 3 turns have been convergent — confirming and refining, not introducing major new concepts
- All exploration domains have substantive coverage
- Core use cases are defined with enough flow to specify
- Ready for reflection checkpoint, then transition to Phase 3

### Turn 12 — Phase 2 (Divergent Exploration) — Reflection + Coexistence

**Agent response:** Full system consolidation (4 layers). Asked about coexistence of all four teaching mechanisms.

**Key points from answer:**
- All four teaching mechanisms coexist, each serving a different purpose:
  - Pattern naming: celebrates what user got RIGHT (reactive to presence)
  - Coaching annotations: addresses what user MISSED (reactive to absence)
  - Artifact explanation: teaches diagram types during generation
  - Process narration: orients user during phase transitions
- Pattern naming and coaching annotations are complementary: one rewards presence, one addresses absence
- The existing "one teaching moment per turn" rule needs reconsideration — a turn could have pattern naming AND a coaching annotation since they serve different purposes

**Open questions (minor, can be resolved in Phase 3):**
- Whether coaching annotations should be logged in the exploration journal
- Whether completeness verification is affected (probably not — it checks artifacts, not the coaching)
- How the agent adapts for experienced users (probably via the OODA "decide" step — if user consistently demonstrates a primitive, stop coaching on it)

**Phase transition assessment:**
ALL criteria met:
1. All 6 exploration domains have substantive coverage ✓
2. Core use cases have basic flow + alternate flows ✓
3. Last 3 turns have not introduced major new concepts ✓ (last 3 were: confirming primitives, confirming OODA+primitives integration, confirming coexistence)

READY FOR PHASE 3.

### Turn 13 — Phase 2 (Divergent Exploration) — Final Divergent Turn

**Agent response:** Asked about the interaction style — how questions and coaching annotations should feel together.

**Key points from answer:**
- "It depends on context" — no single fixed style
- Good to ask questions — questions remain primary
- Even better: question followed by an EDUCATED ASSUMPTION
- The agent should infer from context and offer that inference for the user to confirm, correct, or refine
- This is "inference over interrogation" — instead of asking from scratch, the agent proposes and the user reacts
- This aligns with the existing "context-grounded questions" rule but extends it: the agent does not just ground in the codebase index, it also grounds in the conversation so far and in domain knowledge

**Design implication:**
- The "question + educated assumption" pattern applies to FACILITATION questions, not coaching annotations
- It changes the interaction from "What happens when X?" to "What happens when X? Based on what you've described, I'd guess [assumption] — is that right?"
- This is faster, more collaborative, and gives the user something concrete to react to
- The coaching annotation (if triggered) then appears below both the question and the assumption

**Coverage assessment:**
- All domains substantively covered
- Saturation confirmed — 4 consecutive convergent turns
- Transitioning to Phase 3

---

## Phase 3: Convergent Specification

Starting convergent specification. Switching from open exploration to specific, falsifiable questions about exact behaviour.

### Turn 14 — Phase 3 (Convergent Specification)

**Agent response:** Proposed the full SA&D primitive checklist: 7 structural primitives (S1-S7) with absence signals, 7 analytical primitives (A1-A7) with absence signals. Explained the matrix relationship.

**Key outcome:** User confirmed the primitive tables and asked two meta-questions: "Is there anything I haven't asked you that I should have?" and "Is there anything we should have considered that we haven't?"

### Turn 15 — Phase 3 (Convergent Specification) — Gap Analysis

**Agent response:** Applied failure-first thinking to the specification itself. Identified 10 genuine gaps:
1. Journal tracking of coaching moments
2. Opt-out / experienced user calibration (cold-start)
3. Multiple simultaneous gaps — priority rule
4. "One teaching moment per turn" constraint update
5. Rendering context compatibility
6. Feedback loop / measurement
7. Token budget / response length
8. Turn ordering (annotation placement)
9. Testing / verification approach
10. Scope boundary

### Turn 16 — Phase 3 (Convergent Specification) — Prioritisation

**User asked:** "If you had to pick 3, what would the top 3 we must include?"

**Agent response:** Selected top 3 based on failure-first thinking:
1. Gap 3 (Priority rule for multiple simultaneous gaps) — most likely runtime failure
2. Gap 2 (Experienced user calibration / cold-start) — first-impression damage
3. Gap 8 (Turn ordering) — affects every single turn

**User confirmed:** "Yes please" — proceed with specification and artifact generation.

---

## Phase 4: Artifact Generation

Specification artifacts generated in `.specifications/adaptive-coaching-annotations/`:
- GLOSSARY.md — 15 domain terms defined
- SRD.md — Full specification with 23 functional requirements, 16 business rules, 4 use cases
- diagrams/process-flows.md — OODA decision loop (PF-01), turn structure (PF-02)
- diagrams/state-diagrams.md — User model lifecycle (ST-01)
- NFR.md — 14 non-functional requirements across 5 categories
- HANDOVER.md — 7 key decisions, 5 assumptions, 5 risks, 4-phase implementation sequence
