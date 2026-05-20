# Identity Instance Schema (v1alpha1)

> **Used by:** `Identity.yaml` generate stage as `spec.generate.spec_ref`.
> **Replaces:** the IDENTITY_TEMPLATE.md from the legacy `identity-articulation` outcome.
> **Output target:** `product/organization/IDENTITY.md`.

This schema defines the structural shape of a generated `IDENTITY.md`. The generate stage must produce a Markdown file conforming to this section order and content rules. The evaluate stage's rubric then assesses the resulting document.

---

## Section order (REQUIRED)

The generated document MUST contain these sections in this order:

1. **Tagline + one-liner**
2. **Why We Exist** — Tension, Belief, Cause
3. **Our Approach (HOW)** — 3-5 core principles, each with trade-off
4. **Who We Serve** — Primary persona, We Are NOT Building For
5. **Value Proposition** — concise positioning statement
6. **Success Looks Like** — outcome statements grounded in specifics
7. **Time Horizon** — review cadence, what would change this identity
8. **Authenticity Validation** — table of criteria with status + evidence
9. **Tone Validation** — T-01, T-02, vocabulary checks
10. **Version** — history table

---

## 1. Tagline + one-liner

One short tagline (3-7 words) followed by one summary line (≤ 20 words). The tagline embodies the WHY in compressed form.

**Anti-pattern:** generic taglines ("Building the future of X").
**Test:** the tagline plus the one-liner is enough for a stranger to know what we believe and what we do.

---

## 2. Why We Exist

Three sub-sections, in this order:

### The Tension

A specific, named tension this organisation exists to address. NOT a generic industry observation. The tension is the *gap* between what's currently true and what should be true.

- **Cite the gap with evidence** drawn from BRIEF_PACK.
- **Quantify where possible** (e.g., percentages, dollar amounts, headcount).
- **Avoid:** "the world needs X" framing. Be specific to this organisation's lens.

### The Belief

The fundamental belief that resolves the tension. One paragraph. Strong claim — someone could reasonably disagree.

- **Quality test:** can a counter-position be stated? If not, the belief is a platitude.
- **Avoid:** "we believe in great X" or "we're passionate about Y."

### The Cause

The directional outcome the organisation pursues. Three to five bullet points naming WHO benefits HOW.

- **Format:** "So that {audience} can {specific outcome}."
- **Earned-right framing** if the organisation is pre-PMF or pre-revenue — name the staging.

---

## 3. Our Approach (HOW)

Three to five principles. Each principle MUST include:

- **Statement** — what the principle is, in one sentence.
- **Rationale** — why this principle (one paragraph).
- **Trade-off / What this rules out** — the falsifiability clause. Names what adopting this principle excludes.
- **Evidence** (optional) — example of the principle in action, drawn from BRIEF_PACK.

**Anti-pattern:** principles that are universal goods ("we value quality"). Principles must have a trade-off.

---

## 4. Who We Serve

Two sub-sections:

### Primary Persona(s)

For each primary persona:

- **Name** (role or archetype)
- **Context** — the situation they're in
- **Goal** — what they're trying to do
- **Pain** — what they're up against
- **Quote** — a specific phrase from BRIEF_PACK persona signals, if available

If multiple personas exist, note the sequencing (which is the wedge, which comes later) and the trade-off.

### We Are NOT Building For

A specific exclusion list with rationale. Names actual segments the organisation explicitly turns away.

- **Format:** "{Segment} — {one-line reason for exclusion}"
- **Anti-pattern:** an empty exclusion list. Every focused organisation has explicit exclusions.

---

## 5. Value Proposition

A structured positioning statement. The template:

```
For {target audience}
who {context / problem},
our {category}
provides {core benefit}
unlike {competitor / alternative},
we {specific differentiator}.
```

**Quality tests:**
- The differentiator is specific (verified against BRIEF_PACK competitor_signals).
- The category is named (don't be a category without a name).
- The competitor substitution test: replacing "our" with a named competitor's brand should NOT yield a plausible statement.

---

## 6. Success Looks Like

Three to seven outcome statements describing what success looks like for each persona served (and optionally for the world). Specific, observable, plausible.

**Format options:**

- "For {audience}: {specific outcome with measurable signal}"
- "When we have succeeded: {observable state}"

**Anti-pattern:** abstract goods ("more people will be empowered"). Be concrete.

---

## 7. Time Horizon

Two sub-fields:

- **This identity guides decisions for:** {duration with reasoning}
- **Review cadence:** {annual / quarterly / event-triggered}
- **What might change this identity:** specific events that would force re-articulation.

---

## 8. Authenticity Validation

A table running the rubric's authenticity criteria against this document:

| Criterion | Status | Evidence |
|---|---|---|
| WHY grounded in evidence | PASS / FAIL | {brief evidence summary} |
| Competitor substitution test | PASS / FAIL | {named competitors that don't fit} |
| MECE WHY/HOW/WHAT | PASS / FAIL | {one-line check} |
| Anti-goal coherence | PASS / FAIL | {anti-goals checked} |
| Honest staging | PASS / FAIL | {what's claimed as built vs. building} |

This section is the document's self-attestation. The Verdict from the evaluate stage validates it; mismatches are written into the Verdict's specific_feedback.

---

## 9. Tone Validation

A short checklist:

- **T-01 Pragmatic Authority:** confirmed (or noted where the document deviated).
- **T-02 Radical Clarity:** confirmed (no forbidden vocabulary used).
- **Zero hyperbole:** no superlatives without quantification.

---

## 10. Version

A short history table:

| Version | Date | Changes |
|---|---|---|
| {semver} | {date} | {one-line change summary} |

---

## Section-level rules

- **No emojis** unless the user has explicitly invited them in BRIEF_PACK voice signals.
- **Markdown headings** at consistent levels (H1 = document title, H2 = section, H3 = sub-section).
- **No internal codes** (no FE-NN, T-NN, BC-NN, etc.) in body text — these are evaluation references only.
- **Generated artifact length:** between 600 and 1500 words. Below 600 is thin; above 1500 has likely lost MECE.

---

## What this schema does NOT cover

- **BRAND.md** — produced separately. May be a future sibling Kind (`Brand` apiVersion business-strategy/v1alpha1).
- **TONE_OF_VOICE.md** — produced separately. May be a future sibling Kind (`ToneOfVoice`).
- **PRINCIPLES.md** — produced separately, by a future `Principles` Kind (referenced by both Identity and Strategy Kinds).

For the v0.1 test, the Identity Kind produces only IDENTITY.md. The brand and tone work happens in subsequent invocations of sibling Kinds once they exist.
