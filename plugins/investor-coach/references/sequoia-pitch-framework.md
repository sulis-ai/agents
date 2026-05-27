# Sequoia Pitch Framework Standard

<!-- summary -->

The Sequoia Pitch Framework codifies the slide structure, timing model, and
conversation discipline that Sequoia Capital recommends for early-stage
pitches, extended with stage-specific variants for angel, pre-seed, seed,
Series A, and Series B rounds.

The framework rests on three commitments:

1. **A ten-slide spine.** The deck answers ten investor questions in order —
   from "what's changed in the world?" through to "how will the capital be
   spent?" Each slide has one purpose. No slide is decorative.
2. **A 5/15/30 timing arc.** The opening five minutes earn the next fifteen;
   those fifteen earn the final thirty. The discipline is to front-load the
   most arresting content, not to bury it.
3. **A conversation, not a recital.** The agenda slide pauses to surface
   investor concerns before the substance starts. The deck is a scaffolding
   for dialogue, not a teleprompter.

The standard defines fourteen rules (SQ-01 through SQ-14), stage-specific
slide-emphasis variants, and anti-patterns. A deck that satisfies the spine
(SQ-01 through SQ-10) and the timing model (SQ-11) is **stage-conformant**.

<!-- detail -->

> **Version:** 1.0.0
> **Status:** Active

---

## Provenance

This standard synthesises:

- Sequoia Capital, "How to Present to Investors" (Sequoia Articles, public)
- Y Combinator pitch deck guidance (Carolynn Levy, Aaron Harris)
- Andreessen Horowitz, "16 metrics that matter" series
- First Round Review, "The Pitch Deck We Used to Raise $750k"
- Reid Hoffman's "If, Why, How" pitch framework (Greylock blog)
- NfX, "The 13 Questions VCs Ask About Your Pitch"
- Practitioner knowledge from founders who have closed at each stage

This is practitioner knowledge consolidated from VC-published guidance and
founder-published post-mortems. It is not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|---|---|
| **MUST** | Non-negotiable. A deck that violates this is not stage-conformant. |
| **SHOULD** | Default. Deviation requires explicit justification in `NARRATIVE.md`. |
| **MAY** | Permitted option. Use judgement. |

---

## Section 1: The Ten-Slide Spine

A stage-conformant deck contains slides SQ-01 through SQ-10 in order. Stage
variants (Section 3) adjust the emphasis and detail level of each slide; the
order is fixed.

### SQ-01: What's Changed?

**Severity:** MUST

**Investor question answered:** Why now? What's the discontinuous shift that
opens this window?

| Attribute | Detail |
|---|---|
| **Content** | The technology, regulation, behaviour, primitive, or distribution change that makes this company possible *now* and not five years ago. One claim, one piece of evidence, one slide. |
| **In Practice** | Lead with the shift, not the company. "The cost of training a 70B-parameter model fell 87% in 18 months" beats "We use AI to…" |
| **Anti-Pattern** | A history of the founder. A generic market trend ("AI is growing"). A claim with no evidence. Starting with the company name. |
| **How to verify** | The slide names a specific change (technology / regulation / behaviour / primitive / distribution) with a sourced data point. A reader who has never heard of the company can name the change after reading the slide. |

---

### SQ-02: What You Do

**Severity:** MUST

**Investor question answered:** In one sentence, what does this company do?

| Attribute | Detail |
|---|---|
| **Content** | One sentence. Verb-first. Specific. No jargon. Names the customer, the job, and the mechanism. Format: "[Company] helps [customer] [accomplish job] by [mechanism]." |
| **In Practice** | "Stripe helps internet businesses accept payments by replacing card-network integration with an API." Not: "Stripe is the leading payment infrastructure platform." |
| **Anti-Pattern** | A mission statement. A platform-of-platforms claim. Three sentences where one would do. Use of "leading", "innovative", "best-in-class". |
| **How to verify** | The sentence passes the competitor-substitution test (BR-02): replacing the company name with a named competitor produces an obviously different claim. A reader can repeat the sentence after one reading. |

---

### SQ-03: Fast Facts

**Severity:** MUST

**Investor question answered:** What context do I need to frame everything that follows?

| Attribute | Detail |
|---|---|
| **Content** | Founded date, headcount, stage of development (pre-product / private beta / GA / scaling), traction headline (one metric), fundraising target. Six facts maximum. |
| **In Practice** | Use a single horizontal strip or a 2×3 grid. Numbers, not adjectives. "12 employees" not "small team". "$2M ARR" not "early revenue". |
| **Anti-Pattern** | Vanity metrics (Twitter followers, press mentions). Adjective-only facts ("experienced team"). More than six facts (violates CL-01). |
| **How to verify** | A reader can recite the six facts after a five-second glance. No fact uses an adjective where a number would work. |

---

### SQ-04: Agenda

**Severity:** MUST

**Investor question answered:** What are we going to cover, and when can I interrupt?

| Attribute | Detail |
|---|---|
| **Content** | List of topics in the order they will be covered (typically: Pain, Solution, Market, Competition, Team, Financials). Verbal cue from the presenter: "Before I dive in — anything you want to make sure I cover, or any questions you have already?" |
| **In Practice** | Pause after this slide. Let the investor surface concerns. Adjust order or depth based on what they say. Mark interrupted topics in `EXPLORATION_JOURNAL.md` for the post-meeting debrief. |
| **Anti-Pattern** | No pause. Pre-announcing time per section ("I'll spend 3 minutes on each"). Putting the ask on the agenda (the ask is the close, not a topic). |
| **How to verify** | The slide names 4–7 topics in the order they appear. The speaker notes contain the explicit pause prompt. |

---

### SQ-05: Pain

**Severity:** MUST

**Investor question answered:** What problem are you solving, and how badly does the customer feel it?

| Attribute | Detail |
|---|---|
| **Content** | The specific job the customer is trying to do, the specific way they currently struggle, and a concrete artefact of that struggle (a quote, a workaround, a metric, a process diagram). |
| **In Practice** | Lead with a customer quote or a workflow snapshot, not a generic statement. "Customers spend 14 hours per month reconciling invoices manually" beats "Reconciliation is painful." |
| **Anti-Pattern** | Pain stated in the company's voice rather than the customer's. Pain that any product in the category solves equally well (fails competitor-substitution). Pain measured only by the founder's intuition. |
| **How to verify** | The pain is named with a customer's words or a quantified metric. A competitor in the same category cannot claim to solve the same pain in the same way. |

---

### SQ-06: Solution

**Severity:** MUST

**Investor question answered:** What did you build, and what does it actually do?

| Attribute | Detail |
|---|---|
| **Content** | The product, shown — a screenshot, a workflow diagram, a demo frame, or a before/after. The mechanism by which it solves the SQ-05 pain. |
| **In Practice** | Show, don't describe. A single annotated screenshot beats six bullet points. If the product is API-only, show the API call and the response. |
| **Anti-Pattern** | A wall of feature bullets. A logo-and-tagline slide. A "vision" rendering that doesn't match what's shipped. |
| **How to verify** | The slide contains a visual representation of the product. The mechanism (the how) is named in one sentence. A reader can describe what the product does after seeing the slide. |

---

### SQ-07: Market Size

**Severity:** MUST

**Investor question answered:** How big can this become?

| Attribute | Detail |
|---|---|
| **Content** | TAM / SAM / SOM — with **both top-down and bottom-up** triangulation per FN-04. Per-customer value. Growth trajectory with a sourced growth rate. |
| **In Practice** | One number per scope (TAM, SAM, SOM). Show the bottom-up math (units × price). Source every figure. Cite the proof-point ID. |
| **Anti-Pattern** | Top-down TAM only ("This is a $1T market"). Unsourced statistics. TAM equal to the size of a Gartner report rather than the realistic addressable market. Per-customer value omitted. |
| **How to verify** | Each of TAM, SAM, SOM has a top-down and a bottom-up figure. Each figure links to a proof-point. The bottom-up math is shown or available in the speaker notes. |

---

### SQ-08: Competition

**Severity:** MUST

**Investor question answered:** Who else is doing this, and why will you win?

| Attribute | Detail |
|---|---|
| **Content** | Named competitors (not "various incumbents"). A specific axis of differentiation (not "we're better"). For Series A+, a 2×2 positioning matrix with axes the investor would actually use. |
| **In Practice** | Name three to seven competitors. Include the obvious incumbents and the obvious adjacent threats. State the differentiation in falsifiable form ("We charge 60% less because…" not "We have superior unit economics."). |
| **Anti-Pattern** | Hiding obvious competitors. Claiming "no competition" (means either no market or no homework). Differentiation axes that all benefit the founder (the matrix where you're always in the top-right). |
| **How to verify** | At least three named competitors. Each named competitor appears in `GLOSSARY.md`. Differentiation axes are falsifiable. The matrix is plausible — if a competitor were presenting the same matrix, they would not put themselves where you put them, but they would not say the matrix is dishonest. |

---

### SQ-09: Team

**Severity:** MUST

**Investor question answered:** Why is this the right team to build this?

| Attribute | Detail |
|---|---|
| **Content** | Founders and key hires. For each: the specific reason this person is right for this specific problem. Not generic credentials. |
| **In Practice** | "Built and sold a payments processor to Visa" beats "20 years of fintech experience." Show the proprietary insight the team has that competitors lack. |
| **Anti-Pattern** | Logo-soup of past employers. Generic role descriptions ("CTO with deep technical expertise"). Team slides that read like LinkedIn profiles. |
| **How to verify** | For each named person, the slide states a specific reason they are right for this problem. The reason is falsifiable (a competitor founder reading it would not say "we have that too"). |

---

### SQ-10: Financials

**Severity:** MUST

**Investor question answered:** How will the capital be spent, and what will it produce?

| Attribute | Detail |
|---|---|
| **Content** | Use of funds tied to specific milestones, not generic categories. A burn schedule. A runway figure. The ask. For Series A+, projected revenue with stage-appropriate horizon (FN-01). |
| **In Practice** | "Reach $5M ARR with 130% NDR by Q3 2027" beats "Scale go-to-market." Connect each spend category to a milestone. Show the math. |
| **Anti-Pattern** | "Use of funds: 40% engineering, 30% sales, 20% marketing, 10% G&A" with no milestones. Hockey-stick projections with no stated assumptions. Hiding the ask. |
| **How to verify** | Each spend category links to a milestone. Milestones are falsifiable. The ask is stated explicitly. Projections reference `financial-model.yaml`. |

---

## Section 2: Timing and Conversation Discipline

### SQ-11: The 5/15/30 Arc

**Severity:** MUST

A pitch unfolds in three arcs:

| Minutes | Goal | Slides |
|---|---|---|
| **0–5** | Earn the next 15 minutes | SQ-01 through SQ-04 |
| **5–20** | Earn the final 30 minutes | SQ-05 through SQ-08 |
| **20–50** | Convert interest into a follow-up meeting | SQ-09, SQ-10, Q&A |

| Attribute | Detail |
|---|---|
| **In Practice** | Front-load the most arresting content. The shift, the one-sentence, the fast facts, and the agenda must hit in five minutes. If the investor isn't leaning in by minute five, the pitch is dead — better to know early. |
| **Anti-Pattern** | Saving the "best" content for the end. Burying the ask. Reading the deck. Spending 10 minutes on team intros before the substance starts. |
| **How to verify** | Walk the deck with a timer in rehearsal (`/investor-coach:rehearsal`). The arc holds within ±20%. |

---

### SQ-12: Pause After Agenda

**Severity:** SHOULD

After SQ-04 (Agenda), the presenter pauses and asks the investor what they
most want to ensure gets covered.

| Attribute | Detail |
|---|---|
| **In Practice** | "Before I dive in — anything you want to make sure I cover, or questions you already have?" Adjust depth or order based on the response. |
| **Anti-Pattern** | Powering through without the pause. The pause is what converts the deck from a recital into a conversation. |
| **How to verify** | The speaker notes for SQ-04 contain the pause prompt verbatim. |

---

### SQ-13: Conversation Over Recital

**Severity:** SHOULD

The deck is scaffolding for a conversation, not a script. The presenter
should be ready to abandon the deck at any point and engage the investor's
concern directly.

| Attribute | Detail |
|---|---|
| **In Practice** | Speaker notes are talking points, not paragraphs. The presenter can summarise any slide in 30 seconds without looking at it. The presenter listens more than they talk in the first 10 minutes. |
| **Anti-Pattern** | Reading the deck. Refusing to take questions mid-deck. Talking past the time. |
| **How to verify** | Rehearsal (`/investor-coach:rehearsal`) tests the presenter's ability to summarise each slide without reading. |

---

### SQ-14: Slide Count Discipline

**Severity:** SHOULD

The Sequoia spine is ten slides. The full deck SHOULD be ten to fifteen
slides. More than fifteen indicates either an appendix that should be
broken out, or insufficient editing.

| Attribute | Detail |
|---|---|
| **In Practice** | If a slide cannot be cut without losing an investor question, keep it. If it can, cut it. Move detailed data, demo footage, and reference material to an appendix referenced from speaker notes — not in the main deck. |
| **Anti-Pattern** | A 40-slide deck where every slide is "essential". A 7-slide deck that elides the financials. Decks padded to look thorough. |
| **How to verify** | Slide count is between 10 and 15. Each slide answers a named investor question. An appendix exists for detailed material. |

---

## Section 3: Stage-Specific Slide Emphasis

The ten-slide spine applies at every stage. The **emphasis** — which slides
get the most content, which get the lightest treatment, which get optional
sub-slides — varies by stage.

### SQ-V1: Angel / Pre-seed Variant

| Slide | Emphasis | Notes |
|---|---|---|
| SQ-01 What's Changed? | **HEAVY** | The why-now is doing most of the work. Most arresting evidence here. |
| SQ-02 What You Do | HEAVY | The pitch lives or dies on the clarity of this sentence. |
| SQ-03 Fast Facts | LIGHT | Numbers are small; lean on stage marker, headcount, and ask. |
| SQ-04 Agenda | STANDARD | |
| SQ-05 Pain | HEAVY | Lean on customer-discovery quotes; founders should have conducted 20+ interviews. |
| SQ-06 Solution | MEDIUM | Wireframes / prototypes acceptable; product may be pre-launch. |
| SQ-07 Market Size | MEDIUM | Top-down acceptable with bottom-up framework; precise SOM not required. |
| SQ-08 Competition | MEDIUM | Direct + adjacent competitors; differentiation thesis-level. |
| SQ-09 Team | **HEAVY** | At pre-seed, the team **is** the bet. Two slides if the team is multi-founder. |
| SQ-10 Financials | LIGHT | Use of funds + runway + 12-month milestones. No revenue projection required. |

### SQ-V2: Seed Variant

| Slide | Emphasis | Notes |
|---|---|---|
| SQ-01 What's Changed? | HEAVY | |
| SQ-02 What You Do | HEAVY | |
| SQ-03 Fast Facts | STANDARD | First pilot metrics if any. |
| SQ-04 Agenda | STANDARD | |
| SQ-05 Pain | HEAVY | Customer-discovery evidence + pilot signal. |
| SQ-06 Solution | HEAVY | Live product or working prototype demo required. |
| SQ-07 Market Size | STANDARD | TAM/SAM/SOM with bottom-up math. |
| SQ-08 Competition | STANDARD | |
| SQ-09 Team | HEAVY | |
| SQ-10 Financials | MEDIUM | 12-month bottom-up forecast, milestone-tied. |

### SQ-V3: Series A Variant

| Slide | Emphasis | Notes |
|---|---|---|
| SQ-01 What's Changed? | MEDIUM | Less novel-framing, more "the shift is now visible in our data". |
| SQ-02 What You Do | STANDARD | |
| SQ-03 Fast Facts | HEAVY | Revenue, growth rate, NRR, headcount, ARR multiple. |
| SQ-04 Agenda | STANDARD | |
| SQ-05 Pain | MEDIUM | Customer evidence shifts from interviews to retention data. |
| SQ-06 Solution | MEDIUM | Demo focuses on differentiated capability, not feature tour. |
| SQ-07 Market Size | HEAVY | Bottom-up grounded in actual ACV and segment data. |
| SQ-08 Competition | HEAVY | 2×2 matrix expected. Named comparable rounds and outcomes. |
| SQ-09 Team | STANDARD | |
| SQ-10 Financials | **HEAVY** | 24-month forecast, cohort retention, CAC by channel, payback. |

### SQ-V4: Series B Variant

| Slide | Emphasis | Notes |
|---|---|---|
| SQ-01 What's Changed? | LIGHT | The shift is established. Often folded into SQ-03. |
| SQ-02 What You Do | STANDARD | |
| SQ-03 Fast Facts | **HEAVY** | Quarterly ARR trajectory, NRR, sales efficiency, magic number, headcount growth. |
| SQ-04 Agenda | STANDARD | |
| SQ-05 Pain | LIGHT | Customer evidence shifts to retention cohorts and expansion. |
| SQ-06 Solution | LIGHT | Differentiation slide, not a demo. |
| SQ-07 Market Size | STANDARD | Bottom-up grounded in won-account data and segment penetration. |
| SQ-08 Competition | HEAVY | Won-vs-lost analysis; positioning maturity. |
| SQ-09 Team | STANDARD | Key hires beyond founders, plus org-design plan. |
| SQ-10 Financials | **HEAVY** | 36-month forecast + sensitivity table, scaled unit economics, sales efficiency, capital efficiency. |

---

## Section 4: Anti-Patterns

| ID | Anti-Pattern | Violated Standard |
|---|---|---|
| AP-SQ-01 | Lead with the company, not the shift | SQ-01 |
| AP-SQ-02 | A mission statement instead of a one-sentence offering | SQ-02 |
| AP-SQ-03 | Vanity metrics on the Fast Facts slide | SQ-03 |
| AP-SQ-04 | No pause after the agenda | SQ-12 |
| AP-SQ-05 | Pain stated in the company's voice, not the customer's | SQ-05 |
| AP-SQ-06 | Feature bullets instead of a product visual | SQ-06 |
| AP-SQ-07 | Top-down TAM only, no bottom-up | SQ-07 |
| AP-SQ-08 | "No competition" claim | SQ-08 |
| AP-SQ-09 | Generic credentials on the team slide | SQ-09 |
| AP-SQ-10 | Use of funds without milestone-tying | SQ-10 |
| AP-SQ-11 | Burying the ask | SQ-10 |
| AP-SQ-12 | More than 15 slides in the main deck | SQ-14 |
| AP-SQ-13 | Stage-mismatched rigor (pre-seed deck with Series A model, or Series B deck with seed-level financials) | Section 3 variants |
| AP-SQ-14 | Hockey-stick projections with no stated assumptions | SQ-10, FN-NN |

---

## Section 5: Verification Checklist

Before declaring a deck stage-conformant, verify:

- [ ] All ten spine slides (SQ-01 through SQ-10) are present in order
- [ ] Each slide answers a named investor question
- [ ] Stage variant (SQ-V1 through SQ-V4) has been applied per `PITCH.yaml`
- [ ] Total slide count is between 10 and 15
- [ ] Every numerical claim links to a proof-point
- [ ] No prohibited words from PL ("revolutionary", "disruptive", "best-in-class", etc.)
- [ ] No anti-patterns AP-SQ-01 through AP-SQ-14
- [ ] Speaker notes for SQ-04 contain the pause prompt
- [ ] Rehearsal (`/investor-coach:rehearsal`) confirms the 5/15/30 arc holds within ±20%
- [ ] Appendix exists for detailed reference material; main deck is not padded

---

## Relationship to Other Standards

| Standard | Relationship |
|---|---|
| `deck-narrative-standard.md` (ND-) | ND- governs *how* each slide is composed (Pyramid + SCQA); SQ- governs *which* slides and *what they cover* |
| `financial-rigor-standard.md` (FN-) | FN- enforces evidence rigor for SQ-07 and SQ-10 content |
| `investor-objection-catalogue.md` (IO-) | IO- catalogues objections that target weaknesses in each SQ- slide; used in `/investor-coach:adversarial-review` |
| `visual-design-standard.md` (VD-) | VD- governs slide layout, density, and visual hierarchy; applies to every SQ- slide |
| `cognitive-load.md` (CL-) | CL-01 (chunk limit) caps content per slide; CL-06 (mental model) drives consistent vocabulary across the spine |
| `critical-thinking-standard.md` | PP (Pyramid Principle) and PL (Precision of Language) apply to every slide title and bullet |

---

## Version History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-05-13 | Initial release. Ten-slide spine, 5/15/30 timing model, four stage variants, fourteen anti-patterns. |
