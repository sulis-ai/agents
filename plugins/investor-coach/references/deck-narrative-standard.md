# Deck Narrative Standard

<!-- summary -->

This standard governs *how* each slide is composed and *how* the slides
connect to form a coherent pitch narrative. Eleven rules (ND-01 through
ND-11) apply the Pyramid Principle and SCQA framing to pitch decks, enforce
slide-to-slide narrative continuity, and prohibit the patterns that bury
the lead.

ND- works alongside `sequoia-pitch-framework.md` (SQ-): SQ- specifies
*which* slides exist and *what* they cover; ND- specifies *how* each one
is written.

The standard rests on three commitments:

1. **One investor question per slide.** Every slide answers exactly one
   named question. The slide title states the answer, not the topic.
2. **Lead with the conclusion.** The headline is the takeaway. Supporting
   evidence follows. Investors should be able to read only the headlines
   and still get the pitch.
3. **The deck is one story.** Slide N sets up slide N+1. Transitions are
   intentional. The narrative arc is articulated in `NARRATIVE.md` before
   slides are written.

A narrative satisfies the standard when all eleven rules pass and the
arc in `NARRATIVE.md` reads coherently when slide headlines are read in
sequence.

<!-- detail -->

> **Version:** 1.0.0
> **Status:** Active

---

## Provenance

This standard synthesises:

- Barbara Minto, "The Pyramid Principle" (1987) — Pyramid structure, MECE
  decomposition, SCQA framing
- Critical Thinking Standard — PP (Pyramid Principle), PL (Precision of
  Language)
- Cognitive Load Standard — CL-01 (working memory), CL-06 (coherent mental
  model)
- Sequoia Capital pitch guidance — conclusion-first slide titles
- Practitioner knowledge from pitch coaches and partner debriefs

This is practitioner knowledge consolidated from analytical writing
methodology and pitch coaching. It is not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|---|---|
| **MUST** | Non-negotiable. A narrative that violates this is not stage-conformant. |
| **SHOULD** | Default. Deviation requires explicit justification in `NARRATIVE.md`. |
| **MAY** | Permitted option. Use judgement. |

---

## Section 1: Per-Slide Composition

### ND-01: One Investor Question Per Slide

**Severity:** MUST

Every slide answers exactly one named investor question. The question is
captured in the slide file's front matter and reviewed before composition.

| Attribute | Detail |
|---|---|
| **In Practice** | Each `slides/NN-*.md` file opens with `investor-question:` in front matter. If the slide tries to answer two questions, split it. If it answers no clear question, cut it. |
| **Anti-Pattern** | "About us" slides that answer no investor question. Slides combining "what we do + market size + team" into one. |
| **How to verify** | Front matter exists. The question is specific (per BI). The slide content directly addresses that one question. |

---

### ND-02: Lead With the Conclusion (Pyramid Principle)

**Severity:** MUST

The slide title states the answer to the investor question, not the topic.
The supporting bullets, visual, or chart provide the evidence.

| Title style | Example |
|---|---|
| **Conclusion-first (do)** | "We grew 14% MoM for six consecutive months" |
| **Topic-only (avoid)** | "Growth" |
| **Conclusion-first (do)** | "B2B trucking software has consolidated to three incumbents — and they share a $2B blind spot" |
| **Topic-only (avoid)** | "Market opportunity" |

| Attribute | Detail |
|---|---|
| **In Practice** | Write the slide title last, after the supporting content is finalised. Title = the one-sentence takeaway you'd want the investor to remember from this slide. |
| **Anti-Pattern** | Topic titles. Verbless titles. Titles longer than 12 words. |
| **How to verify** | Read all slide titles in sequence. A reader who sees only the titles can summarise the pitch. |

---

### ND-03: SCQA Framing for Argument Slides

**Severity:** SHOULD

For slides that argue a position (typically SQ-01 What's Changed, SQ-05
Pain, SQ-08 Competition), structure the slide content as SCQA:

| Element | Content |
|---|---|
| **Situation** | The relevant context, briefly |
| **Complication** | What changed, what's broken, what's been missed |
| **Question** | The question the complication raises |
| **Answer** | The slide's claim — typically the slide title |

| Attribute | Detail |
|---|---|
| **In Practice** | The speaker notes follow SCQA verbatim, even if the slide visual is condensed. Speaker notes are where the founder constructs the argument the slide visually summarises. |
| **Anti-Pattern** | Stating the answer without the complication (loses the *why*). Stating the situation without the answer (loses the takeaway). |
| **How to verify** | Argument slides have SCQA-structured speaker notes. The progression is explicit. |

---

### ND-04: Headlines as Conclusions, Not Labels

**Severity:** MUST

The slide title is a complete sentence (or a complete claim phrased as a
fragment) that states the conclusion. It is not a category label.

| Type | Example |
|---|---|
| **Conclusion (do)** | "Net retention has held above 120% for four consecutive quarters" |
| **Conclusion (do)** | "We are the only player serving the underbanked SMB segment" |
| **Label (avoid)** | "Retention" |
| **Label (avoid)** | "Market positioning" |

A conclusion title contains a verb or makes a specific claim. A label is
a noun phrase. If the title is a noun phrase, rewrite it.

| Attribute | Detail |
|---|---|
| **In Practice** | After writing each slide title, ask: "Does this state what I want the investor to take away, or does it just name the topic?" If it names the topic, rewrite. |
| **Anti-Pattern** | Generic labels: "Solution", "Team", "Vision", "Mission", "Roadmap". |
| **How to verify** | Every title contains a verb or a specific factual claim. No title is a bare noun phrase. |

---

### ND-05: Claim-to-Proof Traceability

**Severity:** MUST

Every numerical claim, every market-size figure, every competitive
positioning statement on a slide MUST reference a proof-point ID from
`proof-points/pp-NNN-*.md`.

| Attribute | Detail |
|---|---|
| **In Practice** | The slide file's front matter contains a `proof-points:` list referencing each `pp-NNN-*` used. The visual displays the figure; the speaker notes cite the source. |
| **Anti-Pattern** | Numbers on slides that don't exist in any proof-point. Proof-points referenced but contradicted by the slide. |
| **How to verify** | `/investor-coach:validate` walks each slide's claims, confirms each links to a proof-point, and confirms the proof-point's source supports the claim. |

---

### ND-06: Chunk Limit (CL-01)

**Severity:** MUST

No slide presents more than 4±1 independent information chunks. A "chunk"
is one self-contained claim, bullet, data point, or visual element that
requires independent attention.

| Attribute | Detail |
|---|---|
| **In Practice** | A 7-bullet slide is too dense. Cut to 4. If all 7 are essential, split into two slides. A slide with a chart counts the chart as 1 chunk plus any annotations as additional chunks. |
| **Anti-Pattern** | Bullet stacks of 6+. Charts with 8 series. Logo soup with 12 customer logos and 4 awards. |
| **How to verify** | Count independent chunks per slide. None exceed 5. |

---

## Section 2: Across-Deck Narrative

### ND-07: Articulated Arc in NARRATIVE.md

**Severity:** MUST

Before slides are composed, `NARRATIVE.md` states the deck's story arc in
a single page: opening hook → core argument → evidence build → ask. The
arc is reviewed with the founder before any slide is written.

| Attribute | Detail |
|---|---|
| **In Practice** | NARRATIVE.md contains: (1) the one-sentence pitch, (2) the opening hook (Slides 1-4), (3) the core argument (Slides 5-7), (4) the evidence build (Slides 8-10), (5) the ask and close, (6) the planned Q&A redirects. |
| **Anti-Pattern** | Writing slides before the arc. Slides whose existence the arc doesn't account for. An arc that reads like a category list rather than a story. |
| **How to verify** | NARRATIVE.md exists, was reviewed before slide composition, and every slide is referenced by the arc. |

---

### ND-08: Slide-to-Slide Continuity

**Severity:** SHOULD

Each slide sets up the next. The transition is intentional and stated in
the speaker notes — "which is why we built [next slide]" or "which means
[next slide]".

| Attribute | Detail |
|---|---|
| **In Practice** | Speaker notes for slide N include the verbal transition to slide N+1. The arc reads as cause-and-effect, not as a list. |
| **Anti-Pattern** | Disconnected slides. Speaker notes that end each slide with "and so on" or no transition at all. |
| **How to verify** | Read speaker notes in sequence. Each slide's closing line connects to the next slide's opening. |

---

### ND-09: Term Consistency (CL-06)

**Severity:** MUST

Every term used across the deck appears in `GLOSSARY.md` with a single
definition. Same term, same meaning, every slide.

| Attribute | Detail |
|---|---|
| **In Practice** | When the deck names a competitor ("Stripe"), it always means the same Stripe product. When it names a metric ("CAC"), it always means the same kind of CAC (blended or paid). When it names a segment ("SMB"), it always means the same revenue band. |
| **Anti-Pattern** | "Stripe" on slide 8 meaning Stripe Payments; on slide 9 meaning Stripe Connect. "CAC" on slide 10 meaning paid CAC; in speaker notes meaning blended CAC. |
| **How to verify** | Every term in `GLOSSARY.md` is used consistently across all slides. `/investor-coach:validate` checks this. |

---

## Section 3: Voice

### ND-10: Precision of Language (PL)

**Severity:** MUST

Slides MUST NOT contain prohibited weasel words. Quantitative terms
require metrics. Hedges are not stacked.

**Prohibited terms** (from critical-thinking PL):
"revolutionary", "disruptive", "unprecedented", "game-changing",
"best-in-class", "cutting-edge", "world-class", "amazing", "incredible",
"leading", "innovative" (when used as adjectives without specification).

**Terms requiring metrics:** "significant", "many", "most", "growing",
"large", "fast" — replace with a specific quantity.

| Attribute | Detail |
|---|---|
| **In Practice** | When a slide uses "leading", replace with "the largest" + a specific number (and prove it). When a slide uses "fast-growing", replace with "growing 14% MoM" (and prove it). |
| **Anti-Pattern** | "Our revolutionary platform" — drop the adjective, name the specific advance. "We're a leader in our market" — drop the claim, show the market-share table. |
| **How to verify** | `/investor-coach:validate` greps for prohibited terms. None present. Every quantitative term has a number. |

---

### ND-11: Speaker Notes as Talking Points

**Severity:** SHOULD

Speaker notes are talking points, not paragraphs. They contain the key
facts, the verbal transitions, the planned anecdote, and the proof-point
citations — but not full prose.

| Attribute | Detail |
|---|---|
| **In Practice** | Bullet-form notes. Maximum 80 words per slide. The founder can read the notes and immediately know the talking points without parsing prose. |
| **Anti-Pattern** | Speaker notes as a transcript. Speaker notes the founder would have to memorise verbatim. |
| **How to verify** | Speaker notes per slide ≤ 80 words. Notes are in bullet form. |

---

## Section 4: Anti-Patterns

| ID | Anti-Pattern | Violated Standard |
|---|---|---|
| AP-ND-01 | Topic-only slide titles | ND-02, ND-04 |
| AP-ND-02 | Slides answering multiple investor questions | ND-01 |
| AP-ND-03 | No SCQA structure on argument slides | ND-03 |
| AP-ND-04 | Numbers on slides not linked to proof-points | ND-05 |
| AP-ND-05 | More than 5 chunks per slide | ND-06 |
| AP-ND-06 | Slides composed before NARRATIVE.md arc exists | ND-07 |
| AP-ND-07 | Disconnected slides with no verbal transitions | ND-08 |
| AP-ND-08 | Inconsistent use of terms across slides | ND-09 |
| AP-ND-09 | Prohibited PL words present | ND-10 |
| AP-ND-10 | Speaker notes as full-prose paragraphs | ND-11 |
| AP-ND-11 | Slide title is a noun phrase with no verb | ND-04 |

---

## Section 5: Verification Checklist

Before declaring a narrative stage-conformant, verify:

- [ ] `NARRATIVE.md` exists and was reviewed before slides composed (ND-07)
- [ ] Every slide has `investor-question:` in front matter (ND-01)
- [ ] Every slide title is a conclusion, not a label (ND-02, ND-04)
- [ ] Argument slides have SCQA-structured speaker notes (ND-03)
- [ ] Every numerical claim links to a proof-point (ND-05)
- [ ] No slide exceeds 5 chunks (ND-06)
- [ ] Speaker notes contain verbal transitions to the next slide (ND-08)
- [ ] Every term used consistently per `GLOSSARY.md` (ND-09)
- [ ] No prohibited PL words present (ND-10)
- [ ] Speaker notes ≤ 80 words per slide, bullet-form (ND-11)
- [ ] Headline-only reading of the deck conveys the pitch (ND-02)
- [ ] None of AP-ND-01 through AP-ND-11 present

---

## Relationship to Other Standards

| Standard | Relationship |
|---|---|
| `sequoia-pitch-framework.md` (SQ-) | SQ- specifies *which* slides exist; ND- specifies *how* each is composed |
| `visual-design-standard.md` (VD-) | VD- governs visual layout once narrative is locked |
| `cognitive-load.md` (CL-) | CL-01 → ND-06 (chunk limit); CL-06 → ND-09 (term consistency) |
| `critical-thinking-standard.md` | PP → ND-02; PL → ND-10; BI → ND-01 |
| `financial-rigor-standard.md` (FN-) | FN-06 (per-claim evidence) → ND-05 (claim-to-proof traceability) |

---

## Version History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-05-13 | Initial release. Eleven rules across per-slide composition, across-deck narrative, and voice. Eleven anti-patterns. |
