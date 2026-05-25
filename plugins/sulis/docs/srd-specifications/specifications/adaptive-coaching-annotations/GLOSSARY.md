# Glossary: Adaptive Coaching Annotations

## Summary

Domain terms used throughout the Adaptive Coaching Annotations specification. All other
specification artifacts use these definitions. When a term appears in the SRD, NFR, or
diagrams, its meaning is exactly as defined here.

---

## Terms

| Term | Definition | Context | First Appeared |
|------|-----------|---------|----------------|
| Coaching Annotation | A visually distinct blockquote note (`> *Concept -- explanation.*`) that appears in the agent's response when a gap is detected in the user's analytical thinking. References the previous answer, not the next question. | Delivery format for gap-based coaching | Phase 2, Turn 5 |
| SA&D Primitive | A fundamental building block of systems analysis and design that the agent uses as a reference framework to evaluate user answers. Divided into structural and analytical primitives. | Core reference framework | Phase 2, Turn 10 |
| Structural Primitive | An SA&D primitive that represents a type of system building block: Actor (S1), Use Case (S2), Business Rule (S3), Data Entity (S4), State Lifecycle (S5), Integration Boundary (S6), Process Flow (S7). | Gap detection -- "what kind of thing is missing" | Phase 2, Turn 11 |
| Analytical Primitive | An SA&D primitive that represents a dimension of completeness: Precondition (A1), Postcondition (A2), Exception Path (A3), Alternate Path (A4), Trigger (A5), Constraint (A6), Acceptance Criterion (A7). | Gap detection -- "what dimension is incomplete" | Phase 2, Turn 11 |
| Primitive Matrix | The conceptual grid formed by crossing structural primitives (rows) with analytical primitives (columns). Any structural primitive can be tested against any analytical primitive. E.g., "Use Case without Exception Paths" is cell (S2, A3). | Gap identification logic | Phase 2, Turn 11 |
| OODA Loop | Observe-Orient-Decide-Act decision cycle that the agent executes on every user answer. Observe reads the answer; Orient maps against primitives; Decide evaluates coaching opportunity; Act produces annotation or skips. Each cycle updates the user model. | Decision engine for coaching | Phase 2, Turn 9 |
| User Model | The agent's evolving understanding of the user's experience level and demonstrated competencies. Starts at a calibrated baseline (Phase 1) and refines with each OODA cycle. Tracks which primitives the user has demonstrated and which they have not. | Adaptive behaviour | Phase 2, Turn 7 |
| Mindset Skill | A meta-cognitive thinking pattern that sits above SA&D primitives: Boundary Thinking, Failure-First Thinking, Actor Empathy, Precision Reflex, Dependency Awareness. Coached when the agent detects a repeated pattern of missing the same type of primitive. | Meta-cognitive coaching layer | Phase 2, Turn 4 |
| Pattern Naming | The existing teaching mechanism where the agent names a formal concept after the user demonstrates it. Celebrates presence. Distinct from coaching annotations, which address absence. | Existing mechanism -- coexists with annotations | Phase 2, Turn 12 |
| Dual-Layer Facilitation | The architecture of running two parallel information channels: the primary facilitation conversation (questions, reflections, summaries) and the secondary coaching channel (annotations in blockquote format). The user can engage with one or both. | Information architecture | Phase 2, Turn 5 |
| Educated Assumption | The pattern where the agent asks a facilitation question and then offers an inference grounded in conversation context for the user to confirm, correct, or refine. Replaces open-ended interrogation with collaborative hypothesis-testing. | Interaction style | Phase 2, Turn 13 |
| Cold-Start Problem | The challenge of calibrating coaching frequency before the agent has enough signal about the user's experience level. Mitigated by Phase 1 orientation inference. | Calibration design | Phase 3, Gap Analysis |
| Absence Signal | An observable pattern in a user's answer that indicates a specific SA&D primitive was not considered. Each primitive has characteristic absence signals defined in the primitive tables. | Gap detection | Phase 2, Turn 10 |
| Cycling | The frequency governance rule that prevents overexposure by rotating through different primitives rather than coaching the same concept repeatedly. | Annotation frequency | Phase 2, Turn 7 |

## Synonyms and Disambiguation

| Preferred Term | Also Known As | NOT the Same As |
|---------------|---------------|-----------------|
| Coaching Annotation | Coaching note, annotation, coaching moment | Pattern naming (which celebrates presence, not absence) |
| SA&D Primitive | Primitive, building block | Design pattern (which is an implementation concept, not an analysis concept) |
| OODA Loop | OODA spiral, decision loop | The six-phase facilitation model (which governs the session, not individual turns) |
| User Model | Learner model, experience profile | User persona (which is a requirements artefact about the system being specified) |
| Mindset Skill | Thinking pattern, analytical habit | SA&D primitive (which is a specific building block, not a thinking pattern) |
| Educated Assumption | Hypothesis, inference | Leading question (which pushes toward a predetermined answer) |
