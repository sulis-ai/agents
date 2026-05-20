---
name: rehearsal
description: >
  Phase 9 of the Investor Deck Coach. Times the founder against the Sequoia
  5/15/30 arc, runs 8–10 in-character mock investor questions drawn from
  ADVERSARIAL_REVIEW.md, scores answer strength (Strong/Medium/Weak/Evaded),
  and produces REHEARSAL_NOTES.md with timing breakdown, transcript, and
  weak-answer drill list. Agent-proposed at the end of /idc:build-deck.
user_invocable: true
---

# Rehearsal

When invoked, run a timed walkthrough of the deck followed by mock Q&A.
The agent plays the investor in-character (Sequoia partner, sceptical
angel, domain-expert LP) and scores answer strength.

The agent proposes this skill at the end of `/idc:build-deck`. The
founder may decline; rehearsal is optional but strongly recommended.

## When to invoke

- Right after `/idc:build-deck` is complete and the founder accepts the
  rehearsal proposal.
- Before a known partner meeting (re-run as needed).

## When NOT to invoke

- Before the deck is built — there's nothing to walk through.
- Without the founder's explicit acceptance — rehearsal is collaborative,
  not unilateral.

---

## Execution

### Step 1: Set the mode

Confirm the rehearsal scenario:

- **Mock partner meeting** — 50-minute slot, 25 min present + 25 min Q&A
- **Demo day** — short slot (often 3–10 min), no Q&A
- **Angel coffee** — informal, no fixed slot, conversational

Default is mock partner meeting. Adjust timing targets accordingly.

Record the mode in `journal/{YYYY-MM-DD}-{topic}.md`.

### Step 2: Time the walkthrough

The founder presents the deck slide-by-slide. The agent times each
section and records:

| Section | Slides | Target |
|---|---|---|
| Opening hook | 1–4 | 5 min |
| Core argument | 5–7 | 10 min |
| Evidence build | 8–10 | 10 min |

Target ±20% per section. Significant deviation → flag for revision
(usually trimming).

The agent does NOT interrupt during the timed walkthrough. Notes go
into the running transcript silently. Interruptions break flow.

### Step 3: Mock Q&A (in-character)

After the walkthrough, the agent switches into investor character for
8–10 questions. The character rotates:

- Sequoia partner (sharp, data-driven, market-focused)
- Sceptical angel (founder-focused, defensibility-focused)
- Domain-expert LP (regulatory, technical, scale-of-outcome focused)

Questions come from `ADVERSARIAL_REVIEW.md`'s top-10 list, asked in
the appropriate character's voice. The founder answers; the agent
scores:

| Score | Criteria |
|---|---|
| **Strong** | Clear, specific, evidence-backed, lands in < 30s |
| **Medium** | Reasonable but could be sharper / shorter |
| **Weak** | Vague, evasive, or missed the question |
| **Evaded** | Founder pivoted away from the question entirely |

Scoring happens silently during the Q&A. Feedback follows after the
final question.

### Step 4: Hat back to coaching

After the final question, switch back to coaching mode explicitly:

> "Okay, hat back on. That was the mock Q&A. Want me to walk through
> what worked and what we'd want to drill next?"

Wait for confirmation, then deliver feedback.

### Step 5: Deliver feedback

For each question:

- Replay the investor voice
- Replay the founder's answer (paraphrased)
- State the score
- For Weak / Evaded: draft a strengthened version of the answer

Use coaching-without-conflict throughout:

- **Show, don't tell:** for Weak answers, replay what the partner
  would have heard, not the verdict.
- **Offer alternatives:** every Weak answer gets a coached version
  ready for the next rehearsal.
- **Respect the iteration:** the founder is rehearsing precisely
  because they don't have the answers down yet. Treat each weak
  answer as a drill point, not a failure.

### Step 6: Walk slide-level observations

The agent's notes from the timed walkthrough surface here:

- Which slides ran long (candidates for trimming)
- Which slides the founder hesitated on (candidates for rephrasing
  or replacing with a stronger visual)
- Which bullets the founder skipped (candidates for cutting)

### Step 7: Founder self-assessment

Ask the founder to rate themselves on:

- Confidence in delivery
- Knowledge of own financial model
- Knowledge of competitor positioning
- Comfort handling difficult Qs

This is for the journal — not for judgement.

### Step 8: Produce REHEARSAL_NOTES.md

Use the template. Sections:

1. Timing breakdown table
2. Mock Q&A transcript with per-question scoring
3. Weak-answer drill list (questions to re-run next rehearsal)
4. Slide cuts and strengthens
5. Founder self-assessment
6. Coaching notes (top 2 wins, top 1 strengthen)
7. Next-rehearsal date (if applicable)

### Step 9: Transition

If significant revisions are needed, return to `/idc:narrative`.
If only drill is needed, schedule the next rehearsal date in the
journal.

If the founder is ready for the actual meeting, propose
`/idc:validate` as the final pre-flight check.

---

## Refusals

Refuse if:

- The founder asks to skip the timed walkthrough → "The timing IS the
  pitch. If we don't time it, we don't know whether the 5/15/30 arc
  holds."
- The founder asks for "softer" investor characters → "The point is
  to feel the real thing. I won't soften the partner voice — but I'll
  coach the answer afterwards."
- The founder asks to grade their own answers → "I'll grade. If you
  disagree I'll show you what the partner would have heard. We can
  recalibrate together."

---

## Coaching gates (after hat returns)

- **Show, don't tell:** replay the moment, not the verdict.
- **Offer alternatives:** every Weak answer gets a coached version.
- **Respect iteration:** the first rehearsal is a baseline, not a
  performance review.
- **Match the medium:** difficult feedback is delivered in
  conversation, not in a written list to be read alone.

---

## Gotchas

- **Don't interrupt the timed walkthrough.** Save observations for
  later. Mid-flow interruption damages calibration.
- **Don't break character mid-question.** If you start a question as
  a Sequoia partner, finish as one. Inconsistent character
  undermines the drill.
- **Don't rate softly.** A Weak answer in rehearsal is what the
  partner will hear in the meeting. Calibrate honestly.
- **Don't skip the self-assessment.** It's a useful baseline against
  the agent's external scoring.

---

## Output checklist

- [ ] Mode set (mock-partner / demo-day / angel coffee)
- [ ] Timed walkthrough completed without interruption
- [ ] Mock Q&A: 8–10 questions delivered in-character
- [ ] Each question scored Strong / Medium / Weak / Evaded
- [ ] Hat returned to coaching explicitly
- [ ] Feedback delivered with coached-answer drafts for Weak / Evaded
- [ ] Slide-level observations captured
- [ ] Founder self-assessment recorded
- [ ] `REHEARSAL_NOTES.md` produced from template
- [ ] Weak-answer drill list captured
- [ ] Next step proposed (`/idc:narrative` if revisions needed, else
      `/idc:validate`)
