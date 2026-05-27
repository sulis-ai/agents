---
name: financial-model
description: >
  Phase 5 of the Investor Deck Coach. Builds a stage-appropriate financial
  model grounded in the proof-points from market-research. Enforces
  financial-rigor-standard (FN-01..16). Produces financial-model.yaml as
  source of truth and invokes scripts/build_xlsx.py + scripts/build_finance_html.py
  to render the Excel model and branded HTML dashboard.
user_invocable: true
---

# Financial Model

When invoked, produce the structured financial model (YAML) and render
the Excel and HTML deliverables. Every input cell is sourced from a
proof-point or marked as an explicit assumption.

## When to invoke

- After `/investor-coach:market-research` returns verdict STRONG or ADEQUATE.
- When the founder updates underlying assumptions (e.g., new pricing
  data, new cohort retention figures).

## When NOT to invoke

- Before market research is complete (no proof-points to ground
  inputs).
- When market research verdict is INSUFFICIENT (insufficient
  evidence to ground a model).

---

## Execution

### Step 1: Read stage gate

Read `PITCH.yaml` `stage` field. Determine required artifacts per
FN-01:

| Stage | Horizon | Required artifacts |
|---|---|---|
| Angel / Pre-seed | Thesis | Market thesis, unit-economic hypothesis, milestone-tied use of funds. **No revenue projection.** |
| Seed | 12 months | Monthly revenue forecast, burn schedule, runway, milestone-tied use of funds |
| Series A | 24 months + cohort | Monthly revenue forecast, cohort retention, CAC by channel, payback, gross margin |
| Series B | 36 months + sensitivity | Quarterly forecast, scaled unit economics, sensitivity table, sales efficiency |

Apply the relevant variant of `financial-model.yaml.template`. Refuse
to build a stage-above model (e.g., Series A model for a seed pitch)
— per FN-01.

### Step 2: Populate from proof-points

For each input field in the YAML:

1. Identify the source proof-point (`pp-NNN`) in `proof-points/`.
2. Cite the proof-point in the YAML's `proof_point:` field.
3. If no proof-point exists, **stop and ask**: can we source this, or
   is this an explicit assumption? Assumptions go in the
   `assumptions:` section with rationale (FN-09).

Required per stage per FN-02:

| Metric | Pre-seed | Seed | A | B |
|---|---|---|---|---|
| Pricing & ACV | thesis | preliminary | confirmed | mature |
| Gross margin | hypothesis | preliminary | confirmed (≥6 mo) | confirmed (≥12 mo) |
| CAC blended | — | optional | required | required |
| CAC by channel | — | — | required | required |
| LTV | — | — | required (≥6 mo) | required (≥12 mo) |
| Payback | — | — | required | required |
| NRR / GRR | — | — | optional / — | required / required |
| Logo retention | — | optional | required | required |
| Sales efficiency | — | — | optional | required |
| Capital efficiency | — | — | optional | required |

### Step 3: Confidence calibration (FN-07)

Every projection has a confidence level: HIGH, MEDIUM, or LOW.

- **HIGH**: directly observed primary data, OR ≥3 Tier-1/2 sources
  converging within 20%
- **MEDIUM**: Tier-1/2 sources with gaps, OR strong analogous data
- **LOW**: single source, extrapolation, judgement-only

For MEDIUM and LOW projections, use **ranges** (low / base / high),
not point estimates. The YAML's `revenue_low / revenue_base /
revenue_high` columns capture this. The HTML dashboard renders the
ranges as bands.

### Step 4: Pre-mortem (FN-10) — required

Before completing the model, conduct a pre-mortem with the founder:

> "If these projections miss by 50% in twelve months, the top three
> reasons are…?"

Capture in YAML `risks:` array with likelihood × impact + mitigation
per risk. **Refuse to complete the model without this section.**

The pre-mortem must include at least one execution risk (not only
external risks like "recession").

### Step 5: Stop / pivot triggers (FN-11)

For each strategic bet implied by the model — paid acquisition
channel, pricing tier, enterprise motion, etc. — define an explicit
trigger:

> "We will pivot the paid-social channel if Month-6 CAC exceeds $40
> against a $10 target."

Capture in YAML `triggers:` array.

### Step 6: Sensitivity analysis (FN-14, Series A+)

For Series A and B, build a 3×3 sensitivity grid:

- Driver 1 (typically revenue growth rate): downside / base / upside
- Driver 2 (typically CAC): downside / base / upside
- Outcome: runway months and 12-month ARR per cell

Downside scenarios MUST be meaningful (e.g., revenue 50% of base, CAC
150% of base — not just 90% / 110%). If every scenario in the grid is
profitable, the sensitivity is insufficient.

For pre-seed and seed, skip (set `sensitivity.enabled: false`).

### Step 7: Use of funds (FN-15)

For every spend category, tie to a falsifiable, dated milestone:

```yaml
use_of_funds:
  - category: "Expand sales team"
    amount_usd: 1500000
    milestone: "Hire VP Sales + 2 AEs by Q1 2027"
    expected_outcome: "Drive $5M new ARR by Q4 2027"
    proof_point: "pp-018"
```

Refuse generic categories ("30% on sales") with no milestone.

### Step 8: Round sizing justification (FN-16)

Capture in `round:` section:

```yaml
round:
  ask_usd: 5000000
  expected_runway_months: 18
  next_round_milestone: "$5M ARR with NRR ≥ 120%"
  next_round_target: "Series B by Q4 2027"
  justification: "..."
```

The justification connects ask amount → milestones funded → next
round.

### Step 9: Render deliverables

Invoke the build scripts:

```bash
python3 scripts/build_xlsx.py \
    .pitch/{slug}/03-financials/MODEL.yaml \
    .pitch/{slug}/03-financials/MODEL.xlsx
```

```bash
python3 scripts/build_finance_html.py \
    .pitch/{slug}/03-financials/MODEL.yaml \
    .pitch/{slug}/brand-assets/tokens.css \
    .pitch/{slug}/03-financials/DASHBOARD.html
```

Verify outputs render correctly. If a render fails, surface the error
to the founder rather than silently shipping a broken deliverable.

### Step 10: Transition

Walk the dashboard with the founder. Confirm the numbers match
expectation. Then propose `/investor-coach:narrative`.

---

## Refusals

Refuse, factually, if:

- The founder asks to project numbers above their stage → "FN-01 says
  a Series A model needs 24 months and cohort data. You're at seed.
  Over-specifying signals naïveté. Let's do the seed model."
- The founder asks to skip the pre-mortem → "The partner will run
  one in the meeting. Better to find the risks here."
- The founder asks to add a number without a proof-point → "Either
  we source it, mark it as an explicit assumption, or cut the claim.
  I won't put unsourced numbers in the deck."
- The founder asks for false precision → "Three significant figures
  from ±30% inputs signals weakness, not strength. Let me round."

---

## Coaching gates

- **Show, don't tell** when a projection looks aggressive — walk
  through what hitting it requires in real terms (customers, ACV,
  retention). The founder will often self-correct.
- **Pre-mortem in coaching tone:** "If this fails in a way we'd kick
  ourselves for not anticipating, what would it be?"
- **Honest about confidence:** MEDIUM is not a weakness. A founder
  who claims HIGH confidence on every projection signals lack of
  self-awareness; the model is more credible with calibrated
  uncertainty.

---

## Gotchas

- **Don't lock the model before market-research is reviewed.** The
  model rests on proof-points; if research is patchy, the model is
  patchy.
- **Don't conflate forecast confidence with founder confidence.**
  HIGH-confidence forecast = strong evidence. The founder's
  conviction is separate.
- **Don't allow vanity metrics into the financial dashboard** (FN-12).
  Cumulative downloads, sign-up counts, press mentions go in the
  appendix or nowhere.
- **Don't extrapolate cohort retention from <3 months of data.**
  Flag as LOW and use ranges.

---

## Output checklist

- [ ] `financial-model.yaml` complete per stage requirements
- [ ] Every input has a proof-point or is in `assumptions`
- [ ] Confidence assigned per projection; ranges used for MED/LOW
- [ ] Pre-mortem present, ≥3 risks, ≥1 execution risk
- [ ] Stop/pivot triggers for each strategic bet
- [ ] Sensitivity grid present (Series A+) with meaningful downside
- [ ] Use of funds milestone-tied
- [ ] Round size justified
- [ ] `financial-model.xlsx` rendered successfully
- [ ] `financial-summary.html` rendered successfully
- [ ] Founder walked through the dashboard
- [ ] Journal entry written
- [ ] Next step (`/investor-coach:narrative`) proposed
