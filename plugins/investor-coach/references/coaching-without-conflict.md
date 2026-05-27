# Coaching Without Conflict Standard

<!-- summary -->
A validation framework for delivering feedback, corrections, and guidance without
triggering defensive reactions. Seven core tenets with comparison tables, a validation
checklist, application examples, and guidance on when conflict may be necessary.
<!-- /summary -->

> **Version:** 1.0.0
> **Status:** Active

---

## Principle Definition

**Coaching Without Conflict** is the discipline of delivering corrections, improvements,
and challenging feedback in a way that maintains the recipient's autonomy and dignity
while achieving the same behavioural outcome as direct criticism.

The goal is not to avoid hard truths. The goal is to deliver hard truths in a way that
the recipient can hear, process, and act on — rather than defend against.

This is not about being "nice." It is about being *effective*.

---

## Core Tenets

### 1. Show, Don't Tell

Present evidence and let the recipient draw the conclusion, rather than stating the
conclusion and expecting acceptance.

| Instead of | Try |
|------------|-----|
| "Your error handling is wrong." | "Here's what happens when this function receives null input — [show the stack trace]. What would you want to happen instead?" |
| "This design won't scale." | "Let's walk through what happens at 10x current load with this approach." |
| "You missed the requirement." | "Here's the requirement. Here's what we built. Let's compare them." |

**Why it works:** People accept conclusions they reach themselves more readily than
conclusions imposed on them. Showing evidence activates their own analytical process
rather than their defensive process.

---

### 2. Separate Observation from Judgement

State what you observe factually before offering any interpretation or evaluation.

| Instead of | Try |
|------------|-----|
| "This code is messy." | "I see four levels of nesting and three responsibilities in this function. That makes it hard for me to follow the logic." |
| "This plan is unrealistic." | "The plan estimates 2 weeks for integration. The last two integrations of similar scope took 5 and 6 weeks. What's different this time?" |
| "You're not paying attention to detail." | "I've found three instances where the output doesn't match the spec. Here they are." |

**Why it works:** Observations are verifiable and non-threatening. Judgements trigger
identity-defence. Leading with observation creates shared ground before interpretation.

---

### 3. Frame as Collaborative Problem-Solving

Position the issue as a shared problem to solve together, not as a mistake to correct.

| Instead of | Try |
|------------|-----|
| "You need to fix this." | "We've got a problem here — let's figure out the best approach." |
| "This approach is wrong." | "I'm not sure this approach handles [edge case]. What do you think?" |
| "You should have tested this." | "How can we make sure this gets caught before it reaches production?" |

**Why it works:** Collaborative framing maintains the recipient's status and agency.
It transforms the dynamic from judge-and-defendant into partners-facing-a-problem.

---

### 4. Acknowledge Complexity

Recognise that the situation may be genuinely difficult, that trade-offs exist, and that
the recipient may have information or constraints you don't.

| Instead of | Try |
|------------|-----|
| "This should be simple." | "I know there are constraints I might not be seeing. Walk me through what led to this approach." |
| "Why didn't you just use X?" | "Was there a reason X didn't work here? I might be missing context." |
| "This is obviously wrong." | "This looks off to me, but I want to make sure I'm not missing something. Can you walk me through the reasoning?" |

**Why it works:** Acknowledging complexity signals respect for the recipient's context
and intelligence. It also protects you from being wrong in public — sometimes the
"obvious" solution has been tried and failed.

---

### 5. Offer Alternatives, Not Just Criticism

When identifying a problem, provide at least one concrete alternative approach.

| Instead of | Try |
|------------|-----|
| "This won't work." | "I don't think this handles [edge case]. One option might be [alternative]. Another might be [alternative]. What do you think?" |
| "This is too complex." | "Could we achieve the same result with [simpler approach]? Here's what I'm thinking..." |
| "Don't do it that way." | "I've seen [this approach] work well for similar problems. Would it fit here?" |

**Why it works:** Criticism without alternatives is a dead end. Alternatives give the
recipient something to evaluate and build on, transforming a stop into a redirect.

---

### 6. Respect the Iteration

Recognise that the current state is a point in a journey, not a final destination.
Treat work-in-progress as work-in-progress.

| Instead of | Try |
|------------|-----|
| "This isn't good enough." | "This is a solid start. Here's what I think needs to happen to get it to production-ready." |
| "This has too many problems." | "Let's prioritise — which of these issues should we tackle first?" |
| "Start over." | "The [specific part] is strong. I think the [other part] needs rethinking. Here's why." |

**Why it works:** Acknowledging progress maintains motivation. Identifying the path from
current state to desired state is more useful than simply declaring the current state
inadequate.

---

### 7. Match the Medium to the Message

Deliver sensitive or complex feedback through a channel with enough bandwidth for nuance
and dialogue. Avoid delivering difficult feedback in low-bandwidth channels (short text
messages, PR comments without context, public channels).

| Instead of | Try |
|------------|-----|
| A terse PR comment: "This is wrong." | A PR comment with context: "I think there's an issue with [specific thing] — [explanation]. Happy to discuss synchronously if that would help." |
| Public criticism in a team channel. | Direct message or private conversation first, then share the technical learnings (not the criticism) with the team if appropriate. |
| A long written critique with no opportunity for dialogue. | A conversation (synchronous or asynchronous with clear invitation to respond) that allows the recipient to ask questions and provide context. |

**Why it works:** Complex feedback requires dialogue. Low-bandwidth channels strip
nuance and prevent the recipient from asking clarifying questions, increasing the
likelihood of misinterpretation and defensive response.

---

## Validation Checklist

### Pass/Fail Questions

Before delivering feedback, verify:

- [ ] **Evidence first?** Am I leading with observable evidence rather than a conclusion?
- [ ] **Observation separated from judgement?** Have I stated what I observe before
  offering interpretation?
- [ ] **Collaborative frame?** Am I framing this as a shared problem, not a personal
  failing?
- [ ] **Complexity acknowledged?** Have I considered that I might be missing context?
- [ ] **Alternative offered?** Am I providing at least one concrete alternative path?
- [ ] **Progress recognised?** Am I acknowledging what's working before identifying
  what needs to change?
- [ ] **Medium appropriate?** Is this channel appropriate for the sensitivity and
  complexity of this feedback?

### Red Flag Words

If you find yourself using these words, pause and reframe:

- "Obviously" — implies the recipient should have known, which is condescending
- "Just" — minimises complexity ("why didn't you just...")
- "Simply" — same as "just"
- "Wrong" — judgement without evidence
- "Should have" — retrospective judgement that cannot be acted on
- "Always" / "Never" — absolute generalisations that invite counter-examples
- "But" after praise — negates the praise ("this is good, but...")

### Green Light Words

Words and phrases that support coaching without conflict:

- "I notice..." — observation without judgement
- "I'm curious about..." — invites explanation without accusation
- "What if we..." — collaborative framing
- "Help me understand..." — positions the recipient as the expert
- "One option might be..." — offers alternatives without mandating
- "What do you think?" — invites dialogue and respects autonomy
- "And" instead of "but" — connects rather than negates

---

## Application Examples

### Example 1: Code Review

**Before (conflict-prone):**
> "This function is way too long and does too many things. You should know better than
> to write a 200-line function."

**After (coaching without conflict):**
> "I'm noticing this function handles validation, transformation, and persistence —
> three distinct responsibilities. What if we extracted each into its own function?
> That would make each one independently testable. The validation logic in particular
> looks like it could be reused elsewhere. What do you think?"

---

### Example 2: Design Review

**Before (conflict-prone):**
> "This design doesn't account for concurrent access. It's going to break under load."

**After (coaching without conflict):**
> "I want to walk through a scenario: what happens if two users update the same record
> simultaneously with this design? I think we might need a concurrency strategy here.
> One option is optimistic locking, another is a queue-based approach. Which do you
> think fits better given our latency requirements?"

---

### Example 3: Missed Requirement

**Before (conflict-prone):**
> "You missed the accessibility requirement. This needs to be keyboard-navigable."

**After (coaching without conflict):**
> "Looking at the requirements, there's an accessibility criterion for keyboard
> navigation. I don't see it in the implementation yet — is it planned for a later
> iteration, or did it get missed? If we need to add it, I can help scope the work."

---

### Example 4: Strategic Disagreement

**Before (conflict-prone):**
> "This strategy is too risky. We should go with the proven approach."

**After (coaching without conflict):**
> "I see the potential upside of this approach. I'm concerned about [specific risk].
> The last time we tried something similar, [specific outcome]. Could we mitigate that
> risk by [specific mitigation]? Or would a hybrid approach — [description] — give us
> the upside with less exposure?"

---

## When Conflict May Be Necessary

This standard acknowledges that coaching without conflict is not always sufficient.
Some situations require direct, unambiguous communication that may cause discomfort:

1. **Safety or security issues** — When users or data are at immediate risk, clarity
   and speed take priority over comfort. Say "This has a security vulnerability that
   must be fixed before merge" directly.

2. **Repeated pattern after coaching** — When the same issue has been raised through
   coaching approaches multiple times and the pattern continues, escalate to direct
   feedback: "We've discussed this pattern three times. It needs to change."

3. **Ethical violations** — Plagiarism, data manipulation, dishonest reporting.
   These require direct statements, not collaborative framing.

4. **Time-critical situations** — Production incidents, approaching deadlines with
   blocking issues. In these moments, direct communication serves everyone better.

In these situations, be direct, be factual, and be respectful — but do not sacrifice
clarity for comfort.

---

## Quick Reference Card

| Tenet | One-Liner |
|-------|-----------|
| Show, Don't Tell | Present evidence; let them conclude. |
| Observation vs Judgement | State what you see before what you think. |
| Collaborative Framing | "We have a problem" not "you made a mistake." |
| Acknowledge Complexity | "What am I missing?" not "this should be simple." |
| Offer Alternatives | Criticism without a path forward is a dead end. |
| Respect the Iteration | Current state is a waypoint, not a verdict. |
| Match the Medium | Complex feedback needs high-bandwidth channels. |

---

## Integration

This standard complements other standards in this repository:

- **Critical Thinking Standard (EH, HU):** Epistemic Humility (EH) directly supports
  Tenet 4 (Acknowledge Complexity) — both require intellectual honesty about what you
  might be wrong about. Hierarchy of Evidence (HU) informs how to present evidence
  effectively when coaching (Tenet 1).

- **Cognitive Load Standard (CL-04):** Choice Reduction applies to feedback delivery.
  When coaching, limit feedback to the most important actionable items rather than
  presenting every observation. Overwhelming the recipient with 15 improvement suggestions
  violates both CL-04 and Tenet 6 (Respect the Iteration).

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-13 | Adapted from coaching validation framework for general use. Seven core tenets, validation checklist, four application examples. |
