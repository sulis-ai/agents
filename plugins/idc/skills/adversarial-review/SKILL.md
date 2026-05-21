---
name: adversarial-review
description: >
  Phase 7 of the Investor Deck Coach. Runs an explicit hat-change from
  coaching to adversarial mode. Reads PITCH.yaml stage, filters
  investor-objection-catalogue by stage, scores rebuttal strength against
  deck artifacts, ranks riskiest-first (impact × (1 − rebuttal strength)),
  produces ADVERSARIAL_REVIEW.md with 10–15 selected objections.
user_invocable: true
---

# Adversarial Review

When invoked, stress-test the deck before it reaches a partner meeting.
The agent switches from coaching to adversarial mode for the duration of
this phase, then explicitly returns to coaching.

## When to invoke

- After `/idc:narrative` is complete and slides have proof-point
  references.
- When the founder revises slides significantly and wants to re-test.

## When NOT to invoke

- Before narrative is complete — there's nothing concrete to attack.
- During build — adversarial work informs the narrative, not the
  rendering.

---

## The hat-change protocol

This phase requires an explicit, founder-acknowledged hat-change. Before
running the analysis, signal the change verbally:

> "With your permission, I'm going to switch hats now. So far I've been
> coaching with you. For this phase I'm going to argue *against* the
> deck — playing a Sequoia partner, a sceptical angel, and a
> domain-expert LP. The point is to find the holes a partner would find,
> while we still have time to fix them. Push back if you think I'm
> wrong. Ready?"

Wait for the founder's go-ahead. Record the hat-change entry in
`journal/{YYYY-MM-DDTHHMMSSZ}-{topic}.md`.

At the end of Phase 7, return to coaching mode with an equally explicit
signal:

> "Hat back on. The hardest objection I'd expect from a Sequoia partner
> is [X]. Your current rebuttal scores Weak because [reason]. Here are
> two options for strengthening it. Which do you want to work on first?"

Record the return-to-coaching entry in the journal.

---

## Execution

### Step 1: Read context

- `PITCH.yaml` — for stage
- `MARKET_RESEARCH.md` and `proof-points/` — for evidence available
- `financial-model.yaml` — for financial inputs
- `NARRATIVE.md` and `slides/` — for what the deck currently claims

### Step 2: Filter the catalogue

From `references/investor-objection-catalogue.md`, select objections
where the stage tag matches `PITCH.yaml.stage`. The catalogue has 40
objections across 9 categories; per-stage filtering typically yields
20–28.

### Step 3: Score rebuttal strength per objection

For each filtered objection:

1. Identify the slide(s) it would most likely trigger against (the
   catalogue lists the typical slide).
2. Identify the weakest claim it targets — by reading the slide and the
   underlying proof-points.
3. Score current rebuttal:

   | Score | Criteria |
   |---|---|
   | **Strong** | Deck contains the evidence required to ace it (per catalogue); proof-points support; speaker notes anticipate the question |
   | **Medium** | Deck partially addresses; one of (evidence, framing, anticipation) is missing |
   | **Weak** | Deck mentions but doesn't defend; founder relies on improvisation |
   | **None** | Deck doesn't address; question would land cold |

4. Identify ≥2 concrete mitigation options per Weak / None objection.
5. Recommend one mitigation with rationale.

### Step 4: Rank riskiest-first (AT)

Sort by impact × (1 − rebuttal strength). High-likelihood objections
with Weak rebuttals rise to the top.

Per AT (Adversarial Posture), riskiest assumptions go first. The
founder addresses the hardest objection first because addressing it
informs everything else.

### Step 5: Select 10–15 objections

Pick the top 10–15 from the ranked list. The cap exists to keep
addressability practical — every objection has a stated mitigation
path the founder can actually act on.

If more than 15 Weak / None objections exist at any stage, the deck
has structural issues that go beyond adversarial review. Flag this
explicitly:

> "Your deck has more than 15 Weak / None rebuttals at this stage.
> This suggests the underlying argument has structural weakness that
> adversarial review can't fix on its own. I recommend revisiting
> [specific issue] before continuing."

### Step 6: Produce ADVERSARIAL_REVIEW.md

Use the template. Sections:

1. Hat-change protocol notice
2. Summary table (Strong / Medium / Weak / None counts)
3. Top 3 objections requiring action
4. Per-objection analysis (riskiest first)
5. Cross-cutting themes
6. Recommended next actions (prioritised)
7. Founder acknowledgments table (for any residual risks the founder
   accepts rather than addresses)

### Step 7: Walk the report with the founder

After producing the report, switch back to coaching mode and walk the
top 3 objections together. For each:

- Show the investor voice
- Show the weakest claim it targets
- Show the current rebuttal score with reasoning
- Present the mitigation options
- Help the founder choose and draft

### Step 8: Address or acknowledge

For each Weak / None objection, the founder either:

- **Addresses it** — revise the slide, add a proof-point, change the
  ask. The agent helps draft.
- **Acknowledges residual risk** — captured in the report's
  "Founder acknowledgments" table with rationale and date.

Both are valid outcomes. The point is that the founder enters the
partner meeting knowing where the holes are.

### Step 9: Transition

When the report is reviewed and the action list is clear, propose
`/idc:build-deck` (after addressed items are reflected in slides).

---

## Refusals

Refuse if:

- The founder asks to soften an objection in the report → "I won't
  soften it. The point of this pass is to hear the objection in its
  strongest form, while we have time to address it. Let's work on
  the rebuttal."
- The founder asks to skip the hat-change protocol → "The protocol
  isn't ceremony. It's how I tell you when I'm coaching versus
  stress-testing. Without it, you don't know which mode I'm in."
- The founder asks to skip adversarial review entirely → "The
  partner you're meeting next week will run this whether we do or
  not. Five hours here saves a lost meeting."

---

## Coaching gates (after hat returns)

- **Show, don't tell:** for each top objection, walk through what
  the partner would see, not what you think.
- **Offer alternatives:** every Weak / None comes with ≥2 mitigation
  options. The founder chooses.
- **Respect iteration:** acknowledging a residual risk is not a
  failure. It's a decision.

---

## Gotchas

- **Don't invent objections beyond the catalogue.** v0.1.0 of this
  skill works from the canonical 40. Partner-specific objections come
  from the founder's own research on the fund.
- **Don't soften the investor voice.** The catalogue's verbatim
  framings are the floor. Real partner objections are sharper.
- **Don't rank by founder comfort.** Rank by risk to the pitch.
- **Don't skip the journal entries.** The hat-change is a procedural
  marker that supports session resumption.

---

## Output checklist

- [ ] Hat-change protocol announced and acknowledged
- [ ] Journal entry: coaching → adversarial
- [ ] Stage-filtered catalogue applied
- [ ] Per-objection rebuttal strength scored
- [ ] Objections ranked riskiest-first (AT)
- [ ] 10–15 objections selected
- [ ] `ADVERSARIAL_REVIEW.md` produced from template
- [ ] Top 3 walked through with founder
- [ ] Each Weak / None has a decision (address or acknowledge)
- [ ] Hat returned to coaching
- [ ] Journal entry: adversarial → coaching
- [ ] Next step (`/idc:build-deck`) proposed (after revisions if any)
