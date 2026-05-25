# Handover Brief: Adaptive Coaching Annotations

## Summary

This document provides everything needed to implement the Adaptive Coaching Annotations
enhancement in the requirements-analyst agent prompt. The enhancement adds gap-triggered
coaching annotations to the agent's facilitation behaviour, developing users' SA&D skills
through doing. Implementation means modifying the agent prompt file
(`srd/agents/requirements-analyst.md`), not writing software code.

---

## Key Decisions

These decisions were made during facilitation. They are final and should not be
re-litigated during implementation.

| # | Decision | Why | Alternatives Considered |
|---|----------|-----|------------------------|
| 1 | Coaching annotations are gap-triggered (reactive to absence), not schedule-triggered (attached to questions) | Real coaching responds to observed performance, not a fixed curriculum. The user's answer reveals what they need to learn. | Schedule-based (annotation on every question), first-encounter (annotation first time a concept appears), shift-based (tapering frequency) |
| 2 | Visual format is blockquote with italic (`> *text*`), not inline explanation | Dual-layer architecture: facilitation is primary channel, coaching is secondary. The user can absorb or skip without disruption to flow. | Inline explanation before question (too heavy), parenthetical aside (breaks sentence flow), post-hoc naming only (misses absence) |
| 3 | SA&D primitives are the reference framework, not a list of "topics to cover" | Primitives make gap detection concrete and implementable. "Check which primitives are relevant and absent" is a precise instruction. "Detect analytical gaps" is vague. | Generic "analytical thinking" assessment, checklist of topics, free-form judgement |
| 4 | Structural primitives (S-level) take priority over analytical (A-level) | Structural gaps are more fundamental. You cannot specify exception paths for a use case that hasn't been identified. Fix the foundation before the details. | Equal priority with random selection, analytical first (catches more subtle gaps), most-frequent-absence first |
| 5 | User model has three levels, not a continuous scale | Three levels produce distinct, implementable coaching behaviours. A continuous scale requires threshold decisions at every point and is harder to express in a prompt. | Binary (novice/expert), continuous (0-100 score), five-level (too many distinct behaviours to specify) |
| 6 | All four teaching mechanisms coexist with independent limits | Pattern naming (celebrates presence) and coaching annotations (addresses absence) serve complementary functions. Combining them under one limit would force a choice between rewarding and coaching on every turn. | Single "one teaching moment per turn" rule covering all mechanisms, coaching annotations replace pattern naming |
| 7 | Question + educated assumption is the interaction style | Inference over interrogation. Offering an assumption for the user to confirm/correct is faster and more collaborative than open-ended questions. | Open-ended questions only, multiple-choice prompting, statement-then-question |

---

## Assumptions

| # | Assumption | Impact if False | Validation Method |
|---|-----------|----------------|-------------------|
| 1 | The agent can reliably detect primitive absence from natural language | False positives (coaching when no gap exists) or false negatives (missing real gaps) degrade trust in the coaching system | Run scenario tests with deliberate omissions and verify detection accuracy |
| 2 | One sentence (30 words) is enough to convey a coaching concept | If too brief, annotations are cryptic and unhelpful. If insufficient, the 30-word limit needs to increase. | Pilot with users and assess whether they understand the annotation without additional context |
| 3 | The blockquote format achieves visual separation in practice | If users do not perceive annotations as distinct from the main response, the dual-layer architecture fails | Test in Claude Code CLI, VS Code, and GitHub rendering |
| 4 | Three coaching levels are sufficient to cover the novice-to-expert spectrum | If three levels are too coarse, intermediate users get coaching that is either too basic or too sparse | Monitor user feedback across sessions with different experience levels |
| 5 | The exploration journal provides sufficient session continuity for the user model | If journal entries are too compressed, the agent cannot reconstruct the user model in a new session | Test session resumption: start a session, end it, resume from journal, verify coaching behaviour is consistent |

---

## Known Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | False positive coaching: agent fires annotations on experienced users who deliberately omitted a primitive because it is irrelevant | Medium | Patronises user, damages trust, user mentally dismisses all future annotations | Cold-start calibration (FR-12) sets Level 3 for experienced users. OODA Decide step checks user model before coaching. User-level criterion requires genuine gap, not contextual omission. |
| 2 | Annotation fatigue: even at correct frequency, annotations become background noise after 20+ turns | Medium | User stops reading annotations entirely | Freshness rule (BR-05) prevents repeating within 3 turns. Cycling rule ensures variety. Mindset skill escalation (FR-19) provides novelty. Level transitions reduce frequency as user demonstrates competency. |
| 3 | Prompt length increase makes the agent slower or less reliable | Low | Slower response times, potential for the agent to drop coaching rules under context pressure | Coaching rules are concise (primitive tables, OODA steps, business rules). Total addition to prompt estimated at 800-1200 words. Monitor response quality after implementation. |
| 4 | Coaching and facilitation compete for cognitive attention | Medium | User is thinking about the coaching annotation when they should be thinking about the facilitation question | Turn ordering (FR-16) separates annotation from question. Reflection checkpoint suppression (FR-17) prevents dual cognitive load at consolidation points. |
| 5 | Journal coaching entries accumulate faster than expected, consuming context | Low | Reduced context available for facilitation content in long sessions | Compressed storage (FR-23) limits to 2 lines per turn. At 60 turns, this is 120 lines -- manageable within journal structure. |

---

## Recommended Implementation Sequence

Implementation means modifying `srd/agents/requirements-analyst.md`. The following
sequence minimises risk by building foundational capabilities first.

### Phase 1: Foundation (encode first)

1. **SA&D Primitive Tables (FR-01, FR-02)** -- Add the structural and analytical
   primitive tables to the agent prompt. These are pure reference data with no
   behavioural change. The agent needs these before it can detect gaps.

2. **Domain-Primitive Mapping (FR-04)** -- Add the mapping of exploration domains
   to relevant primitives. This scopes gap detection to the current domain.

3. **Turn Ordering Rules (FR-16)** -- Define the four-position turn structure. This
   changes response formatting but not content. Test that responses follow the ordering
   even before coaching annotations are active.

### Phase 2: Core Behaviour (encode second)

4. **OODA Loop (FR-05 through FR-08)** -- Add the four-step decision loop. This is
   the core behaviour change. The agent now evaluates every answer against the
   primitive framework and decides whether to coach.

5. **Priority Rules (FR-14, FR-15)** -- Add the priority hierarchy for selecting
   among multiple gaps. Without this, the OODA loop has no selection mechanism.

6. **Coaching Annotation Format (FR-09, FR-10, FR-11)** -- Add the annotation
   rendering rules. The agent can now produce coaching output.

7. **Cold-Start Calibration (FR-12)** -- Add Phase 1 orientation calibration. Without
   this, the agent has no initial user model and defaults may be wrong.

### Phase 3: Refinement (encode third)

8. **User Model Refinement (FR-13)** -- Add ongoing level transitions. The user
   model now adapts across the session.

9. **Mindset Skill Coaching (FR-18, FR-19, FR-20)** -- Add the meta-cognitive layer.
   This depends on the OODA loop being stable.

10. **Journal Integration (FR-21, FR-22, FR-23)** -- Add coaching entries to the
    exploration journal. This enables session continuity.

### Phase 4: Coexistence (encode last)

11. **Coexistence Rules (BR-15)** -- Add the rules governing interaction between
    pattern naming and coaching annotations. Test that both mechanisms work
    independently and together.

12. **Reflection Checkpoint Suppression (FR-17, BR-13)** -- Add the suppression
    rule for reflection turns.

---

## Artifact Reading Order

For the implementer modifying the agent prompt:

1. **[GLOSSARY.md](GLOSSARY.md)** -- Understand the terms first. "Coaching annotation,"
   "SA&D primitive," "OODA loop," "user model," and "mindset skill" have precise
   definitions.

2. **[SRD.md](SRD.md)** -- The complete specification. Read Section 4 (System Features)
   for all functional requirements. Read Section 9 (Business Rules Summary) for the
   complete rule set.

3. **[diagrams/process-flows.md](diagrams/process-flows.md)** -- The OODA loop
   visualised. Shows the decision tree the agent follows on every turn.

4. **[diagrams/state-diagrams.md](diagrams/state-diagrams.md)** -- The user model
   lifecycle. Shows how coaching level changes across a session.

5. **[NFR.md](NFR.md)** -- Constraints on the coaching system's behaviour. Especially
   the cognitive load limits and consistency requirements.

6. **This file (HANDOVER.md)** -- Decisions, assumptions, risks, and implementation
   sequence.

---

## Verification Approach

Because this enhancement is a prompt behavioural change (not software), traditional
unit testing does not apply. Verification uses scenario testing.

### Scenario Test Categories

1. **Gap Detection Accuracy** -- Provide the agent with user answers that deliberately
   omit specific primitives. Verify the correct primitive is identified as absent.
   Cover all 14 primitives.

2. **False Positive Suppression** -- Provide answers from experienced users who
   deliberately omit irrelevant primitives. Verify the agent does NOT coach.

3. **Priority Selection** -- Provide answers missing multiple primitives simultaneously.
   Verify the agent selects the correct one per the priority hierarchy (structural
   before analytical, domain-relevant first).

4. **Frequency Governance** -- Run a 20-turn simulated conversation. Verify that no
   primitive is coached more than once in any 3-turn window, and that coaching
   categories cycle.

5. **Calibration Accuracy** -- Provide three opening statements (novice, intermediate,
   experienced). Verify the agent sets the correct initial level and communicates
   calibration appropriately.

6. **Turn Ordering** -- Across 10+ turns, verify that acknowledgement, pattern naming,
   coaching annotation, and next question always appear in the correct order.

7. **Format Compliance** -- Verify every annotation matches `> *Label -- explanation.*`
   with 30 words or fewer.
