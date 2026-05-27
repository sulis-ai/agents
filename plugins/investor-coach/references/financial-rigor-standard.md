# Financial Rigor Standard

<!-- summary -->

This standard governs every financial claim that appears in a pitch deck or
the financial model that backs it. Sixteen rules (FN-01 through FN-16)
enforce evidence-based, stage-appropriate, confidence-calibrated financial
reasoning. The standard adapts the research-synthesis methodology used for
market research and applies it to the financial domain — every number is
sourced, every projection has a stop/pivot trigger, every assumption is
flagged.

The standard rests on three commitments:

1. **Triangulation over assertion.** TAM, SAM, SOM, and any market growth
   rate require both a top-down and a bottom-up calculation. A single-method
   figure is treated as provisional.
2. **Stage-appropriate rigor.** A pre-seed pitch needs a credible thesis and
   a unit-economic hypothesis. A Series B pitch needs cohort retention,
   sales efficiency, and a sensitivity table. The stage gate prevents both
   over-specification (pre-seed pretending to be Series A) and
   under-specification (Series B looking like seed).
3. **Every number traceable.** Every figure in the deck or model links to a
   `proof-points/pp-NNN-*.md` file, which links to a `sources/src-NNN-*.md`
   file with an explicit credibility tier.

A financial model satisfies the standard when all MUST rules pass and any
SHOULD deviations are documented in the model's `assumptions` section.

<!-- detail -->

> **Version:** 1.0.0
> **Status:** Active

---

## Provenance

This standard synthesises:

- David Skok, "SaaS Metrics 2.0" (matrix.vc)
- Andreessen Horowitz, "16 Startup Metrics" and "16 More Startup Metrics"
- Bessemer Venture Partners, "State of the Cloud" annual report — metric definitions
- Sequoia Capital, "Pitch Deck Template" — financial slide expectations
- ChartMogul, "SaaS Metrics Reference"
- Research-synthesis methodology — tiered sources, triangulation,
  contradiction surfacing (adapted from
  `tria/methodology/outcomes/utility/research-synthesis`)
- Critical Thinking Standard — FR (Falsifiability), CC (Confidence
  Calibration), EH (Epistemic Humility), AT (Adversarial Posture)

This is practitioner knowledge consolidated from VC-published metric
definitions and research methodology. It is not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|---|---|
| **MUST** | Non-negotiable. A model that violates this is not stage-conformant. |
| **SHOULD** | Default. Deviation requires explicit justification in the assumptions section. |
| **MAY** | Permitted option. Use judgement. |

---

## Section 1: Stage-Appropriate Rigor

### FN-01: Stage-Appropriate Projection Horizon

**Severity:** MUST

Projection horizon and the artifacts required to support it are determined
by funding stage. Over-specification (pre-seed pitching Series A-style
projections) is as much a credibility loss as under-specification (Series
B pitching seed-style).

| Stage | Horizon | Required artifacts |
|---|---|---|
| Angel / Pre-seed | Thesis-level | Market thesis, unit-economic hypothesis, use of funds tied to 12-month milestones. **No revenue projection required.** A pre-seed deck with a 36-month revenue curve is a credibility loss. |
| Seed | 12 months bottom-up | Revenue forecast (monthly), burn schedule, runway figure, milestone-tied use of funds. Cohort data not required if pre-PMF. |
| Series A | 24 months + cohort | Monthly revenue forecast, **cohort retention curve** (gross + net), CAC by channel, payback period, gross margin, headcount plan. |
| Series B | 36 months + sensitivity | Quarterly revenue forecast, scaled unit economics, **sensitivity table** (revenue ±20%, CAC ±30%), sales efficiency, magic number, capital efficiency ratio. |

| Attribute | Detail |
|---|---|
| **In Practice** | Read `PITCH.yaml` for `stage` before building the model. The model template is selected by stage. |
| **Anti-Pattern** | A pre-seed deck with detailed multi-year revenue forecasts (signals naïveté). A Series B deck with no sensitivity analysis (signals lack of rigor). A Series A deck with no cohort data (signals lack of measurement). |
| **How to verify** | The model's horizon and artifacts match the stage row of this table. Any deviation is documented in the model's `stage-justification` section. |

---

### FN-02: Unit-Economics Disclosure Depth by Stage

**Severity:** MUST

Different stages require different unit-economic disclosures. The
following are the minimum disclosures per stage; richer disclosure is
permitted only if the additional metrics are stable and grounded in data
covering the required period.

| Metric | Pre-seed | Seed | Series A | Series B |
|---|---|---|---|---|
| Pricing model & ACV | thesis | preliminary | confirmed | mature |
| Gross margin | hypothesis | preliminary | confirmed (≥6 months data) | confirmed (≥12 months data) |
| CAC (blended) | — | optional | required | required |
| CAC by channel | — | — | required | required |
| LTV / LTV:CAC | — | — | required (≥6 months retention data) | required (≥12 months) |
| Payback period (months) | — | — | required | required |
| Net Revenue Retention (NRR) | — | — | optional | required |
| Gross Revenue Retention (GRR) | — | — | optional | required |
| Logo retention | — | optional | required | required |
| Sales efficiency (magic number) | — | — | optional | required |
| Capital efficiency ratio | — | — | optional | required |

| Attribute | Detail |
|---|---|
| **In Practice** | A "required" metric absent from the model fails validation. An "optional" metric included MUST be supported by the data period in parentheses. |
| **Anti-Pattern** | Including LTV:CAC for a seed company with three months of data (insufficient observation window). Including NRR for a single-cohort Series A (no second cohort to compute net retention against). |
| **How to verify** | Each required metric for the stage has a value in the model. Each metric value links to a proof-point that confirms the data period. |

---

### FN-03: Cohort Definitions and Consistency

**Severity:** MUST

Cohort definitions MUST be stated explicitly and used consistently across
the deck, the model, and the speaker notes.

| Attribute | Detail |
|---|---|
| **In Practice** | A "cohort" is the set of customers acquired in a defined period (typically a calendar month). Retention is measured at fixed intervals (M+1, M+3, M+6, M+12). Whether retention is logo-based or revenue-based MUST be stated. |
| **Anti-Pattern** | "Our cohorts retain at 90%" with no period, no interval, no definition (logo vs revenue). Using a different cohort definition on slide 8 than the one used in the model. |
| **How to verify** | `GLOSSARY.md` contains the cohort definition. Every cohort claim in the deck matches the definition in `GLOSSARY.md`. The model's cohort table uses the same intervals. |

---

## Section 2: Market-Sizing Rigor

### FN-04: TAM/SAM/SOM Triangulation (MANDATORY)

**Severity:** MUST

Every market-sizing figure (TAM, SAM, SOM) MUST be supported by **both**
a top-down calculation and a bottom-up calculation. A single-method figure
is provisional and MUST be flagged in the model.

| Definition | Description |
|---|---|
| **TAM** (Total Addressable Market) | Total annual revenue opportunity if every potential customer used the product. |
| **SAM** (Serviceable Addressable Market) | The portion of TAM reachable with the company's current go-to-market motion and geography. |
| **SOM** (Serviceable Obtainable Market) | The portion of SAM realistically capturable within the projection horizon. |

| Method | Description |
|---|---|
| **Top-down** | Start from an industry analyst report (Gartner, Forrester, IDC, a16z, public company filings) and segment down to the addressable scope. Cite source. |
| **Bottom-up** | Start from estimated unit volume × average price. Show the math: `customers × price-per-customer-per-year = annual revenue`. Cite source for the customer count and the price. |

A pitch where top-down and bottom-up agree within 2× is **convergent**. A
pitch where they differ by more than 2× must explain the gap explicitly
(e.g., "Top-down includes adjacent segments we don't serve").

| Attribute | Detail |
|---|---|
| **In Practice** | Compute both. Show both. Cite both. Reconcile if they diverge. |
| **Anti-Pattern** | Top-down only ("This is a $1T market" — the McKinsey report number). Bottom-up only ("If we get 1% of the market…"). The 1% claim is the most common pitch-deck failure mode and is rejected on sight by most VCs. |
| **How to verify** | Both calculations are present in the model. Both are sourced. If they diverge >2×, a reconciliation note exists. |

---

### FN-05: Source Tiering for Financial Claims

**Severity:** MUST

Every financial claim is supported by a source assigned to one of four
tiers. Each source file under `sources/src-NNN-*.md` MUST declare its tier
with rationale.

| Tier | Description | Examples |
|---|---|---|
| **Tier 1** | Primary, audited, or directly observed | Company's own audited financials, primary research with named methodology, regulatory filings, the company's own customer billing system |
| **Tier 2** | Reputable secondary, peer-reviewed methodology | Gartner / Forrester / IDC reports, BVP State of the Cloud, public company 10-Ks |
| **Tier 3** | Practitioner / community | Industry blog posts with stated methodology, conference talks, podcast disclosures |
| **Tier 4** | Unattributed / promotional | Vendor marketing material, unsourced benchmarks, anonymous forum claims |

| Attribute | Detail |
|---|---|
| **In Practice** | Every source file declares its tier and the rationale for that tier. Tier 4 sources MAY inform exploration but MUST NOT support load-bearing claims in the deck or model. |
| **Anti-Pattern** | Citing a vendor's marketing landing page as a TAM source. Citing a tier 3 blog post as a substitute for a tier 2 analyst report when one exists. Failing to declare tier. |
| **How to verify** | Each `src-NNN-*.md` has a tier field with rationale. No deck claim is supported only by tier 4 sources. |

---

### FN-06: Per-Claim Evidence (Numbers Trace to Proof-Points)

**Severity:** MUST

Every numerical claim in the deck, the narrative, the financial model, or
the speaker notes MUST link to a `proof-points/pp-NNN-*.md` file. Each
proof-point contains **one claim, one source**.

| Attribute | Detail |
|---|---|
| **In Practice** | When a number first enters the model or the deck, create the proof-point. The proof-point states the claim, links the source, and notes any caveats (recency, scope, methodology limitations). |
| **Anti-Pattern** | Numbers in the deck that don't appear in the model. Numbers in the model with no proof-point reference. A proof-point that cites two sources (split into two proof-points). |
| **How to verify** | `/investor-coach:validate` traces every number in the deck → proof-point → source. Any unsourced number is a `GAPS_FOUND` finding. |

---

## Section 3: Reasoning Rigor

### FN-07: Confidence Calibration

**Severity:** MUST

Every projection and every estimated figure carries an explicit confidence
level: HIGH, MEDIUM, or LOW.

| Level | Criteria |
|---|---|
| **HIGH** | Directly observed primary data, or ≥3 tier-1/2 independent sources converging within 20% |
| **MEDIUM** | Tier 1 + tier 2 sources with some gaps, or strong analogous data |
| **LOW** | Single source, extrapolation from limited data, or judgement with minimal supporting evidence |

| Attribute | Detail |
|---|---|
| **In Practice** | Use ranges, not point estimates, when confidence is MEDIUM or LOW. "Year-2 revenue: $4.0M–$6.5M (MED)" beats "$5.3M (LOW)". The HTML dashboard renders ranges as bands; the Excel model includes a Low / Base / High column structure. |
| **Anti-Pattern** | Point estimates with no range when underlying confidence is LOW. The same confidence ascribed to a Year-1 forecast and a Year-5 forecast. |
| **How to verify** | Every projection in the model has a confidence field. Ranges are used when the field is MEDIUM or LOW. |

---

### FN-08: No False Precision

**Severity:** MUST

Output precision MUST NOT exceed input precision. A model built on
±30% input variance cannot produce three-significant-figure forecasts.

| Attribute | Detail |
|---|---|
| **In Practice** | Round outputs to match the precision of inputs. "$4M ARR in Year 2" not "$4,237,491 ARR in Year 2" when the inputs are estimates. The Excel model may display full precision for engine accuracy, but the deck and HTML summary MUST round to plausible precision. |
| **Anti-Pattern** | A revenue forecast displayed to the dollar based on a customer-count estimate that's a round number ("we'll have 1,000 customers paying $4,237.91 each"). False precision is a credibility signal — investors trust over-rounded forecasts more than over-precise ones. |
| **How to verify** | Deck and HTML output use rounded figures (e.g., $4M, $4.5M, not $4,237,491). Speaker notes contain the full-precision figure if needed for Q&A. |

---

### FN-09: Assumption Documentation

**Severity:** MUST

Every assumption underlying a projection MUST be documented in the
financial model's `assumptions` section. Assumptions are flagged for
validation; they are not facts.

| Attribute | Detail |
|---|---|
| **In Practice** | "We assume a 5% monthly conversion rate from trial to paid, based on the median for B2B SaaS reported by ChartMogul (Tier 2, pp-014)" — assumption + rationale + source. If no source exists, mark `[ASSERTED]` and flag for adversarial review. |
| **Anti-Pattern** | A projection with no assumptions section. A projection where the assumptions are obvious only by reverse-engineering the math. |
| **How to verify** | The `assumptions` section lists every assumption with rationale. Adversarial review (`/investor-coach:adversarial-review`) tests the riskiest assumptions first (AT). |

---

### FN-10: Pre-Mortem Requirement

**Severity:** MUST

Every financial model includes a pre-mortem: "If these projections miss
by 50%, the top three reasons are…". The pre-mortem is captured in the
model's `risks` section and is referenced in the adversarial report.

| Attribute | Detail |
|---|---|
| **In Practice** | Conducted with the founder during Phase 5. The most common causes (slower sales cycle, higher CAC, lower retention, regulatory delay, technical setback) are evaluated explicitly for this company. The top three are documented. |
| **Anti-Pattern** | No pre-mortem (the partner will run one in the meeting). A pre-mortem that names only external risks ("a recession") and no execution risks. |
| **How to verify** | The model's `risks` section contains a pre-mortem with at least three concrete risks, ordered by likelihood × impact. Each risk has a mitigation note. |

---

### FN-11: Stop / Pivot Triggers

**Severity:** SHOULD

For each strategic bet implied by the model (e.g., "we'll achieve $10
CAC via paid social"), define an explicit trigger: at what observed data
point would the bet be considered failed, requiring stop or pivot?

| Attribute | Detail |
|---|---|
| **In Practice** | "We will pivot the paid-social channel if Month-6 CAC exceeds $40 against a $10 target." Capture in the model's `triggers` section. |
| **Anti-Pattern** | Bets with no failure condition (unfalsifiable). Continuing investment in a channel past its trigger because of sunk cost. |
| **How to verify** | The `triggers` section names each strategic bet, its target, and the observation that would trigger reconsideration. |

---

## Section 4: Specific-Metric Discipline

### FN-12: No Vanity Metrics

**Severity:** MUST

Vanity metrics — figures that grow monotonically and don't predict
revenue, retention, or capital efficiency — MUST NOT appear in the
financial slide or the model summary. They MAY appear in the appendix if
they have an explicit explanatory role.

Examples of vanity metrics that fail this rule unless explained:

- Cumulative downloads, cumulative sign-ups, cumulative GMV (when not
  tied to net revenue)
- "Total users" without distinguishing active, paying, or retained
- Press mentions, social-media followers
- Pipeline value without conversion rate

| Attribute | Detail |
|---|---|
| **In Practice** | If a metric is included, it must answer: how does this predict the financial outcome on the next slide? If it doesn't, cut it. |
| **Anti-Pattern** | A SaaS deck showing "100,000 cumulative sign-ups" when only 2% are active. A marketplace deck showing GMV without take rate. |
| **How to verify** | Every metric on the financials slide has a stated link to revenue, retention, or capital efficiency. |

---

### FN-13: Burn and Runway Calculation

**Severity:** MUST

Burn and runway figures MUST use consistent definitions, stated in
`GLOSSARY.md`.

| Term | Definition |
|---|---|
| **Gross burn** | Total monthly cash outflow |
| **Net burn** | Gross burn minus monthly cash inflow (revenue + other) |
| **Runway** | Current cash ÷ trailing-3-month-average net burn |

| Attribute | Detail |
|---|---|
| **In Practice** | When stating runway, specify whether net or gross burn is the denominator. The deck convention is **net burn**, current month and trailing-3-month-average shown together. |
| **Anti-Pattern** | "We have 18 months of runway" without stating cash, burn, or whether the calculation includes the round being raised. |
| **How to verify** | `GLOSSARY.md` contains both definitions. Every runway figure in the deck states the burn type and the calculation date. |

---

### FN-14: Sensitivity Analysis (Series A+)

**Severity:** MUST for Series A and B; MAY for Seed; not required for Pre-seed

For Series A and B, the model MUST include a sensitivity analysis varying
two or three key drivers (typically: revenue growth rate, gross margin,
CAC). The analysis is presented as a 3×3 or 5×5 grid showing impact on
runway or ARR.

| Attribute | Detail |
|---|---|
| **In Practice** | Pick two drivers that the investor will most want to stress-test. Show the company outcome under a downside, base, and upside scenario for each. |
| **Anti-Pattern** | A "downside scenario" that's only 10% below the base case (insufficient stress). A sensitivity grid where every cell is profitable (insufficient stress). |
| **How to verify** | The model contains a sensitivity grid for Series A+ pitches. The downside scenario tests a realistic adverse condition (e.g., revenue growth 50% of base, CAC 150% of base). |

---

### FN-15: Use-of-Funds Milestone-Tying

**Severity:** MUST

Use of funds MUST be tied to specific, falsifiable milestones — not
generic spending categories.

| Attribute | Detail |
|---|---|
| **In Practice** | "Hire VP Sales + 2 AEs by Q1, reach $2M ARR by Q3" beats "30% on sales." Each milestone has a date and a measurable outcome. |
| **Anti-Pattern** | "40% engineering, 30% sales, 20% marketing, 10% G&A" with no milestones. This is a payroll allocation, not a use of funds. |
| **How to verify** | Each spend category links to a milestone. Each milestone has a date and an outcome measurable in `financial-model.yaml`. |

---

### FN-16: Round Sizing Justification

**Severity:** MUST

The ask amount MUST be justified by the runway it buys and the
milestones it funds.

| Attribute | Detail |
|---|---|
| **In Practice** | "$5M closes 18 months of runway to reach $5M ARR with NRR ≥ 120%, positioning for a Series B in Q4 2027." The ask, the runway, the milestones, and the next-round positioning are all in one sentence. |
| **Anti-Pattern** | "We're raising $5M" with no stated runway or milestone-positioning rationale. An ask sized to "round number expectations" rather than capital required. |
| **How to verify** | The financial model contains a `round-justification` section stating ask amount, expected runway, milestones funded, and next-round positioning. |

---

## Section 5: Anti-Patterns

| ID | Anti-Pattern | Violated Standard |
|---|---|---|
| AP-FN-01 | Top-down TAM only | FN-04 |
| AP-FN-02 | "1% of the market" bottom-up | FN-04 |
| AP-FN-03 | Hockey-stick projections with no stated assumptions | FN-09 |
| AP-FN-04 | Single-source financial figure | FN-05, FN-06 |
| AP-FN-05 | Cohort drift (definition changes between slides) | FN-03 |
| AP-FN-06 | Vanity metrics on the financials slide | FN-12 |
| AP-FN-07 | LTV without CAC payback | FN-02 |
| AP-FN-08 | "Conservative estimate" without methodology | FN-09 |
| AP-FN-09 | False precision (3 sig figs from ±30% inputs) | FN-08 |
| AP-FN-10 | Sensitivity analysis where every scenario is profitable | FN-14 |
| AP-FN-11 | Use of funds without milestones | FN-15 |
| AP-FN-12 | Stage-mismatched rigor | FN-01 |
| AP-FN-13 | Runway figure with no stated burn definition | FN-13 |
| AP-FN-14 | Bets with no failure condition | FN-11 |
| AP-FN-15 | Including LTV:CAC with insufficient observation window | FN-02 |
| AP-FN-16 | Pre-mortem absent or only external risks | FN-10 |

---

## Section 6: Verification Checklist

Before declaring a financial model stage-conformant, verify:

- [ ] Stage in `PITCH.yaml` matches the model's horizon (FN-01)
- [ ] Every required metric for the stage has a value (FN-02)
- [ ] Cohort definitions in `GLOSSARY.md` match every cohort claim (FN-03)
- [ ] TAM, SAM, SOM each have top-down + bottom-up triangulation (FN-04)
- [ ] Every source has a tier with rationale (FN-05)
- [ ] Every number in the deck and model links to a proof-point (FN-06)
- [ ] Every projection has a confidence field; ranges used for MED/LOW (FN-07)
- [ ] Deck output rounded to match input precision (FN-08)
- [ ] Assumptions section lists every assumption with rationale (FN-09)
- [ ] Pre-mortem documents at least three risks with mitigations (FN-10)
- [ ] Strategic bets have stop/pivot triggers (FN-11)
- [ ] No vanity metrics on the financials slide (FN-12)
- [ ] Burn/runway definitions in `GLOSSARY.md`; figures specify type (FN-13)
- [ ] Sensitivity analysis present for Series A+ (FN-14)
- [ ] Use of funds tied to falsifiable milestones (FN-15)
- [ ] Round size justified by runway and next-round positioning (FN-16)
- [ ] None of AP-FN-01 through AP-FN-16 present

---

## Relationship to Other Standards

| Standard | Relationship |
|---|---|
| `sequoia-pitch-framework.md` (SQ-) | SQ-07 (Market Size) and SQ-10 (Financials) are content-governed by FN- |
| `critical-thinking-standard.md` | FR (Falsifiability) → FN-11; CC (Confidence Calibration) → FN-07; EH (Epistemic Humility) → FN-09; AT (Adversarial Posture) → FN-10 |
| `investor-objection-catalogue.md` (IO-) | IO- objections target weak FN- compliance |
| `content-quality.md` (CQ-) | CQ-03 (no hedge stacking) and PL (precision of language) reinforce FN-08 |

---

## Version History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-05-13 | Initial release. Sixteen rules across stage-appropriate rigor, market-sizing rigor, reasoning rigor, and specific-metric discipline. Sixteen anti-patterns. |
