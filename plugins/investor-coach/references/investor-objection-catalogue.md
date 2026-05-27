# Investor Objection Catalogue

<!-- summary -->

A canonical catalogue of investor objections that early-stage and growth-stage
pitches face. Forty objections (IO-01 through IO-40) grouped into nine
categories — Market, Team, Defensibility, Unit Economics, Timing, Competition,
Regulatory, Capital Efficiency, Go-To-Market. Each objection states the
question in investor voice, identifies the slide most likely to trigger it,
suggests the strongest rebuttal pattern, and lists the stages at which it
applies.

The catalogue is the working set for `/investor-coach:adversarial-review`. The skill
selects 10–15 stage-relevant objections, ranks them by risk to *this* pitch
(weakest claim first), and produces `05-adversarial/ADVERSARIAL_REVIEW.md` with founder
rebuttal scoring.

The catalogue is not exhaustive — partner-specific objections (e.g., a fund's
recent loss in an adjacent category) cannot be enumerated in advance. The
catalogue establishes the floor: if a pitch cannot survive the canonical
forty, it cannot survive the partner-specific ones.

<!-- detail -->

> **Version:** 1.0.0
> **Status:** Active

---

## Provenance

This catalogue synthesises:

- NfX, "The 13 Questions VCs Ask"
- Bessemer Venture Partners, anti-portfolio post-mortems (public)
- First Round Review, "The Pitch Deck We Used to Raise $750k" — failure-mode analysis
- a16z partner-meeting prep notes (public talks)
- Y Combinator office-hours archives
- Practitioner knowledge from founders who have raised at each stage

This is practitioner knowledge consolidated from publicly available partner
guidance and founder post-mortems. It is not peer-reviewed research.

---

## Severity Convention

The catalogue uses a different scale than other standards — every objection
is something the founder MAY face, and the rebuttal is what the founder
MUST be able to deliver if asked. The relevant rating per objection is
**likelihood**:

| Likelihood | Meaning |
|---|---|
| **HIGH** | Asked in most partner meetings at the named stage |
| **MEDIUM** | Asked in some partner meetings, especially when the relevant slide is weak |
| **LOW** | Asked situationally — partner background, market context, or specific weakness triggers it |

---

## Format

Each objection follows this format:

```
### IO-NN: Short name

**Likelihood:** HIGH / MEDIUM / LOW
**Stage:** All / Pre-seed+ / Seed+ / A+ / B
**Slide triggered by:** SQ-NN
**Investor voice:** "..."
**Strongest rebuttal pattern:** ...
**Weakest rebuttal pattern (avoid):** ...
**Evidence required to ace it:** ...
```

---

## Section 1: Market

### IO-01: TAM too small

**Likelihood:** HIGH
**Stage:** All
**Slide triggered by:** SQ-07
**Investor voice:** "Even if you win this whole market, the outcome doesn't return our fund."
**Strongest rebuttal pattern:** Show a credible expansion path — the wedge market is X, but it's the foothold for adjacent markets Y and Z. Reference the order in which they unlock. Cite analogous companies that did the same expansion (e.g., Shopify started with merchants, expanded to payments, capital, fulfilment).
**Weakest rebuttal pattern (avoid):** Inflating the TAM after the fact to please the partner.
**Evidence required to ace it:** Bottom-up TAM with named expansion vectors. At least one analogous successful expansion case with shared structural features.

---

### IO-02: Market not ready

**Likelihood:** MEDIUM
**Stage:** Pre-seed, Seed
**Slide triggered by:** SQ-01, SQ-05
**Investor voice:** "I've seen this category attempted three times before. What's different now?"
**Strongest rebuttal pattern:** Name the specific change since the last attempt (cost, technology, behaviour, regulation). Cite the prior attempts and what specifically blocked them. Show the evidence that the blocker no longer applies.
**Weakest rebuttal pattern (avoid):** Claiming the prior attempts were "wrong" without addressing the structural reason they failed.
**Evidence required to ace it:** Knowledge of prior attempts; an articulated theory of why now ≠ then; tier-2 evidence of the relevant shift.

---

### IO-03: Bottom-up math implies penetration that's never been achieved

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-07
**Investor voice:** "Your bottom-up TAM assumes 18% of all SMB pharmacies will use you. What's the precedent for that share?"
**Strongest rebuttal pattern:** Cite a structural reason the share is achievable (e.g., regulatory mandate, distribution lock-in, network effect). Or revise the bottom-up to a more defensible share with the same revenue conclusion.
**Weakest rebuttal pattern (avoid):** "We're confident we can achieve it." (Hand-waving.)
**Evidence required to ace it:** Comparable companies' realised share; named structural reason this category permits higher share.

---

### IO-04: Market timing is too early

**Likelihood:** MEDIUM
**Stage:** Pre-seed, Seed
**Slide triggered by:** SQ-01, SQ-05
**Investor voice:** "This is a good idea, but five years too soon. Customers aren't asking for this yet."
**Strongest rebuttal pattern:** Cite leading indicators of demand (search trends, adjacent product growth, regulatory signals, expert forecasts). Show the early-adopter segment that *is* asking now.
**Weakest rebuttal pattern (avoid):** Asserting demand without evidence.
**Evidence required to ace it:** Customer-discovery interviews with the early-adopter segment; leading-indicator data.

---

### IO-05: Market timing is too late

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-08
**Investor voice:** "The winners in this category are already at scale. You're entering a consolidating market."
**Strongest rebuttal pattern:** Identify the segment the incumbents are not serving well (cost, geography, vertical, feature). Show that segment is meaningful in your SOM.
**Weakest rebuttal pattern (avoid):** Claiming the incumbents are weak.
**Evidence required to ace it:** A named underserved segment with size, evidence of incumbent under-service, and a wedge motion to acquire that segment.

---

## Section 2: Team

### IO-06: Wrong team for the problem

**Likelihood:** HIGH
**Stage:** Pre-seed, Seed
**Slide triggered by:** SQ-09
**Investor voice:** "Why is this team the right team to build this?"
**Strongest rebuttal pattern:** Name the proprietary insight each founder has — earned through specific experience — that competitors lack. Concrete, falsifiable, not credentials.
**Weakest rebuttal pattern (avoid):** Listing past employers and roles without explaining the relevance.
**Evidence required to ace it:** Each founder can state in one sentence the specific reason they are right for this problem.

---

### IO-07: Missing critical role

**Likelihood:** HIGH
**Stage:** Seed+
**Slide triggered by:** SQ-09
**Investor voice:** "Who's your VP Sales? You can't scale a sales-led business without one."
**Strongest rebuttal pattern:** Acknowledge the gap. Name the hiring plan (timeline, target profile, source of pipeline). If a candidate is in late-stage conversation, name them.
**Weakest rebuttal pattern (avoid):** Claiming the founder will fill the role themselves indefinitely.
**Evidence required to ace it:** Honest org chart of who exists today, who is the next critical hire, when the hire closes, and how it's funded.

---

### IO-08: Founder dynamics risk

**Likelihood:** LOW
**Stage:** All
**Slide triggered by:** SQ-09
**Investor voice:** "You and your co-founder split equally — how do you make decisions when you disagree?"
**Strongest rebuttal pattern:** Describe a recent specific disagreement, how it was resolved, and what the decision-making process is. Acknowledge that 50/50 is suboptimal and how it's mitigated (board structure, escalation protocol).
**Weakest rebuttal pattern (avoid):** "We always agree" — implausible and signals lack of self-awareness.
**Evidence required to ace it:** A concrete recent disagreement with a stated resolution mechanism.

---

### IO-09: Solo founder

**Likelihood:** MEDIUM
**Stage:** Pre-seed, Seed
**Slide triggered by:** SQ-09
**Investor voice:** "Solo founders fail at higher rates. What's your plan to bring in a co-founder or sufficient leadership?"
**Strongest rebuttal pattern:** State why solo for this company at this stage. Name the senior hires already in place or in the pipeline. Show evidence the founder has self-awareness about the failure mode.
**Weakest rebuttal pattern (avoid):** Dismissing the statistical concern.
**Evidence required to ace it:** Either a planned co-founder addition or a strong early-leadership team that mitigates the solo risk.

---

## Section 3: Defensibility

### IO-10: No moat

**Likelihood:** HIGH
**Stage:** All
**Slide triggered by:** SQ-08
**Investor voice:** "What stops a well-funded competitor from copying this in 18 months?"
**Strongest rebuttal pattern:** Identify the specific moat type — data network effect, scale economy, switching cost, distribution lock-in, regulatory capture, brand. Show evidence the moat is accruing (e.g., data growing faster than competitors could acquire).
**Weakest rebuttal pattern (avoid):** "First-mover advantage" (rarely durable). "We move faster" (unfalsifiable).
**Evidence required to ace it:** A named moat with a falsifiable accumulation metric and a comparable company that built the same moat.

---

### IO-11: Easily disintermediated

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-06, SQ-08
**Investor voice:** "Your customers could go direct to your supplier and cut you out. Why won't they?"
**Strongest rebuttal pattern:** Show why the supplier doesn't want to serve the customer directly (cost, complexity, contracts) AND why the customer values the layer (aggregation, simplicity, integration). Both sides must want the layer to exist.
**Weakest rebuttal pattern (avoid):** Only addressing one side.
**Evidence required to ace it:** Conversations with both suppliers and customers showing both sides want the layer.

---

### IO-12: Platform risk

**Likelihood:** MEDIUM
**Stage:** All
**Slide triggered by:** SQ-06
**Investor voice:** "You're built on top of [Stripe / Shopify / OpenAI / Apple]. What happens when they build this?"
**Strongest rebuttal pattern:** Acknowledge the risk. State the specific reason the platform won't build (different business model, different customer, regulatory). State the diversification plan and timeline.
**Weakest rebuttal pattern (avoid):** "They won't" (unfalsifiable) or "we'll partner" (without evidence).
**Evidence required to ace it:** A platform-history analysis showing the platform's pattern of building vs. not building adjacent products; a diversification roadmap.

---

### IO-13: Distribution disadvantage

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-06, SQ-08
**Investor voice:** "Incumbents own the distribution channel. How do you reach customers without paying their tax?"
**Strongest rebuttal pattern:** Name a channel the incumbent doesn't dominate (developer-led, community, vertical-specific, regulatory). Show traction in that channel.
**Weakest rebuttal pattern (avoid):** Planning to outspend incumbents on the same channel.
**Evidence required to ace it:** Demonstrated traction in an alternative channel with stated CAC and conversion.

---

## Section 4: Unit Economics

### IO-14: CAC payback too long

**Likelihood:** HIGH
**Stage:** A+
**Slide triggered by:** SQ-10
**Investor voice:** "Your payback period is 24 months. Most SaaS at your stage is under 18. What's driving this?"
**Strongest rebuttal pattern:** Acknowledge the figure. Decompose by channel (the blended figure hides a fast channel and a slow one). State the plan to shift mix toward the fast channel.
**Weakest rebuttal pattern (avoid):** Arguing the benchmark is wrong.
**Evidence required to ace it:** CAC by channel; mix-shift plan; evidence the fast channel can scale.

---

### IO-15: Gross margin too thin

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-10
**Investor voice:** "60% gross margin for a software company? What's eating into it?"
**Strongest rebuttal pattern:** Identify the cost driver (compute, third-party services, hardware, hosting). Show the path to improvement (volume discounts, in-house substitution, architecture).
**Weakest rebuttal pattern (avoid):** Claiming margin will improve "naturally with scale" without specifying the mechanism.
**Evidence required to ace it:** Cost-of-revenue breakdown; named cost-reduction levers with timing.

---

### IO-16: Retention weak

**Likelihood:** HIGH
**Stage:** A+
**Slide triggered by:** SQ-10
**Investor voice:** "Your gross retention is 78%. Best-in-class is 90%+. What's driving churn?"
**Strongest rebuttal pattern:** Decompose churn by cohort, segment, and reason. Identify the controllable causes (onboarding, feature gap) and the structural ones (one-off use case, customer business failure). Show the cohort improving over time.
**Weakest rebuttal pattern (avoid):** Blaming customers ("they didn't use the product right").
**Evidence required to ace it:** Churn-decomposition analysis; named root causes; trend data showing improvement.

---

### IO-17: Net retention below 100%

**Likelihood:** HIGH
**Stage:** A+
**Slide triggered by:** SQ-10
**Investor voice:** "NRR below 100% means you're shrinking inside your installed base. What's the expansion path?"
**Strongest rebuttal pattern:** State the expansion product or motion in the pipeline. State the milestone at which NRR crosses 100%.
**Weakest rebuttal pattern (avoid):** Claiming expansion isn't part of the business model (acceptable for some categories but rare for SaaS).
**Evidence required to ace it:** Expansion roadmap with quantified upside and timeline.

---

### IO-18: LTV:CAC inflated

**Likelihood:** MEDIUM
**Stage:** A+
**Slide triggered by:** SQ-10
**Investor voice:** "Your LTV:CAC is 8:1, which is implausible for your stage. What's your retention assumption?"
**Strongest rebuttal pattern:** State the retention period used (and that it matches actual observed retention, not extrapolated). Acknowledge if the figure is forward-looking and based on early-cohort data.
**Weakest rebuttal pattern (avoid):** Defending an implausible figure.
**Evidence required to ace it:** Observed retention curve; LTV calculation methodology stated explicitly.

---

## Section 5: Timing

### IO-19: No inflection event

**Likelihood:** MEDIUM
**Stage:** Pre-seed, Seed
**Slide triggered by:** SQ-01
**Investor voice:** "Why are you raising now? Has something specific changed?"
**Strongest rebuttal pattern:** Name the specific inflection — a milestone hit, a market shift completed, a hiring window opening, a regulatory change taking effect. Tie the raise to the inflection.
**Weakest rebuttal pattern (avoid):** "We're running out of money" (factually correct in many cases, but framed wrong).
**Evidence required to ace it:** A named, dated inflection with evidence.

---

### IO-20: Raising too early for the milestone

**Likelihood:** MEDIUM
**Stage:** A+
**Slide triggered by:** SQ-10
**Investor voice:** "You're raising a Series A with $400k ARR. Most A-stage companies are at $1M+. Why now?"
**Strongest rebuttal pattern:** State the specific reason A-stage capital unlocks the next milestone faster than waiting. Or acknowledge the stage misalignment and propose a different round size.
**Weakest rebuttal pattern (avoid):** Insisting on A-stage round size at sub-A-stage revenue.
**Evidence required to ace it:** A clear thesis for why the capital deployed now produces disproportionate return.

---

## Section 6: Competition

### IO-21: Incumbent will crush you

**Likelihood:** HIGH
**Stage:** All
**Slide triggered by:** SQ-08
**Investor voice:** "What happens when [Microsoft / Salesforce / Google] decides to compete with you?"
**Strongest rebuttal pattern:** State the structural reason the incumbent won't compete effectively (different business model, internal politics, focus, customer segment). Cite an analogous case where the incumbent did launch and the startup still won (or didn't, with the lesson).
**Weakest rebuttal pattern (avoid):** "They're too slow" (often wrong).
**Evidence required to ace it:** Knowledge of the incumbent's roadmap (public), their incentive structure, and an analogous incumbent-vs-startup case.

---

### IO-22: Fast-follower will catch up

**Likelihood:** HIGH
**Stage:** Seed+
**Slide triggered by:** SQ-08
**Investor voice:** "Your differentiation is a 6-month lead in features. What happens when [Competitor X] ships the same feature?"
**Strongest rebuttal pattern:** State why the lead is durable (network effects, data moat, distribution lock-in) OR why the lead compounds (every week ahead produces more advantage). If the lead is genuinely temporary, state the next-order advantage being built.
**Weakest rebuttal pattern (avoid):** Insisting features alone are sufficient.
**Evidence required to ace it:** A durable or compounding advantage, named and measurable.

---

### IO-23: Worse open-source alternative

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-08
**Investor voice:** "Why should customers pay for this when [open-source project] does 70% of what you do for free?"
**Strongest rebuttal pattern:** State the specific reason the customer's total cost of ownership of the open-source option exceeds your price (operations, security, support, integration). Quantify it.
**Weakest rebuttal pattern (avoid):** Disparaging the open-source project.
**Evidence required to ace it:** Customer case studies showing the TCO calculation; ideally, customers who tried the open-source option first and switched.

---

## Section 7: Regulatory

### IO-24: Pending regulation could break the model

**Likelihood:** MEDIUM
**Stage:** All
**Slide triggered by:** SQ-01, SQ-05
**Investor voice:** "What happens if [proposed regulation] passes?"
**Strongest rebuttal pattern:** State awareness of the regulation. State the impact (positive, neutral, negative). State the mitigation if negative.
**Weakest rebuttal pattern (avoid):** Claiming the regulation won't pass.
**Evidence required to ace it:** Active monitoring of the relevant regulatory bodies; named expert advisors.

---

### IO-25: Jurisdictional barriers to expansion

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-07
**Investor voice:** "Your TAM assumes global. What's the country-by-country regulatory cost?"
**Strongest rebuttal pattern:** State the priority geographies and the specific regulatory cost (licence, data residency, partner requirement) for each. Show the timeline and capital required for each market.
**Weakest rebuttal pattern (avoid):** Assuming the model travels.
**Evidence required to ace it:** A jurisdictional roadmap with specific regulatory milestones and capital requirements.

---

## Section 8: Capital Efficiency

### IO-26: Burn rate too high

**Likelihood:** HIGH
**Stage:** A+
**Slide triggered by:** SQ-10
**Investor voice:** "You're burning $500k/month at $200k MRR. That's 30x your revenue. When does the ratio improve?"
**Strongest rebuttal pattern:** State the planned ratio improvement with milestones. Acknowledge that the current ratio is investment, not steady state, and tie spend to a specific output (e.g., hiring sales to drive ACV that justifies the spend).
**Weakest rebuttal pattern (avoid):** Defending the current ratio as appropriate.
**Evidence required to ace it:** A trajectory showing the ratio improving against named milestones.

---

### IO-27: Ask is too large

**Likelihood:** MEDIUM
**Stage:** All
**Slide triggered by:** SQ-10
**Investor voice:** "You're raising $10M when you've burned $1M to get here. What changes that justifies a 10x acceleration?"
**Strongest rebuttal pattern:** State the specific change in motion or stage that justifies the increase (proven channel + ready to scale; new product line; geographic expansion).
**Weakest rebuttal pattern (avoid):** Sizing the round to founder dilution preferences rather than capital requirements.
**Evidence required to ace it:** A use-of-funds tied to milestones that genuinely requires the requested capital (FN-15).

---

### IO-28: Ask is too small

**Likelihood:** LOW
**Stage:** All
**Slide triggered by:** SQ-10
**Investor voice:** "You're raising $1M. We don't write checks under $2M. What would $2M unlock that $1M doesn't?"
**Strongest rebuttal pattern:** Restate the milestones for $1M; then state what $2M would additionally unlock and whether you'd take it.
**Weakest rebuttal pattern (avoid):** Refusing to engage with the larger size.
**Evidence required to ace it:** A milestone-and-spend hierarchy that scales coherently with round size.

---

### IO-29: Runway insufficient to next round

**Likelihood:** HIGH
**Stage:** All
**Slide triggered by:** SQ-10
**Investor voice:** "This round buys you 14 months. Most Series A rounds take 12-18 months to fundraise. You're under-capitalised."
**Strongest rebuttal pattern:** Acknowledge the tight timeline. State the next-round milestones the runway buys. State the contingency (extension, bridge, revenue-funded).
**Weakest rebuttal pattern (avoid):** Claiming the round will take 6 months to raise.
**Evidence required to ace it:** Runway sized to 18-24 months at projected burn, with milestone-to-next-round positioning.

---

## Section 9: Go-To-Market

### IO-30: GTM motion mismatch

**Likelihood:** HIGH
**Stage:** Seed+
**Slide triggered by:** SQ-06
**Investor voice:** "You're targeting enterprise but your product is a self-serve developer tool. How does that work?"
**Strongest rebuttal pattern:** State the specific motion (PLG-to-enterprise, hybrid, dual-product). Cite a comparable company that succeeded with the same motion.
**Weakest rebuttal pattern (avoid):** Hand-waving the transition from one motion to another.
**Evidence required to ace it:** A named motion with mechanics (e.g., PLG seed → AE-led expansion) and a named comparable.

---

### IO-31: Sales cycle too long

**Likelihood:** MEDIUM
**Stage:** A+
**Slide triggered by:** SQ-10
**Investor voice:** "Your sales cycle is 9 months. How do you forecast revenue with that uncertainty?"
**Strongest rebuttal pattern:** Show the sales-cycle distribution (not just average). State the path to compression (product-led trials, vertical templates, smaller deal sizes). Show cohort improvement.
**Weakest rebuttal pattern (avoid):** Defending the cycle as inherent to the segment without showing compression path.
**Evidence required to ace it:** Cycle distribution data; named compression levers; trend data.

---

### IO-32: Customer concentration

**Likelihood:** HIGH
**Stage:** A+
**Slide triggered by:** SQ-03, SQ-10
**Investor voice:** "Your top three customers represent 60% of revenue. What happens if one churns?"
**Strongest rebuttal pattern:** Acknowledge the concentration. State the diversification plan with timeline. State the renewal probability and expansion plan for each top customer.
**Weakest rebuttal pattern (avoid):** Dismissing the risk.
**Evidence required to ace it:** A customer-concentration trend showing diversification over time; multi-year contracts or strong renewal signals for top customers.

---

### IO-33: Wedge to whole product

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-06, SQ-07
**Investor voice:** "Your wedge product is great. But the customer ultimately needs [full suite]. Why won't they consolidate on [Competitor]?"
**Strongest rebuttal pattern:** State the wedge's strategic role — does the wedge own a foothold that the suite competitor can't reach? Does the wedge produce data the suite competitor lacks? Or is consolidation actually the customer's preference, and your wedge is a stepping-stone to suite?
**Weakest rebuttal pattern (avoid):** Insisting the wedge is sufficient on its own when the customer is buying suites elsewhere.
**Evidence required to ace it:** Customer-buying-pattern data; an articulated wedge-to-suite strategy with timeline.

---

### IO-34: Pricing power

**Likelihood:** MEDIUM
**Stage:** Seed+
**Slide triggered by:** SQ-10
**Investor voice:** "Why is your price $X and not $X/3 or $X*3? What would change customer behaviour at each level?"
**Strongest rebuttal pattern:** State the pricing logic — value-based, cost-plus, competitive. Show willingness-to-pay evidence (customer interviews, A/B tests, competitor pricing). State the planned pricing evolution.
**Weakest rebuttal pattern (avoid):** Pricing based on "what feels right" without methodology.
**Evidence required to ace it:** Stated pricing methodology with evidence.

---

### IO-35: Activation problem

**Likelihood:** MEDIUM
**Stage:** Seed, A
**Slide triggered by:** SQ-10
**Investor voice:** "Your sign-up to first-value conversion is 12%. The benchmark is 30%+. What's the blocker?"
**Strongest rebuttal pattern:** Decompose the activation funnel. Identify the highest-drop step. State the planned fix with expected lift.
**Weakest rebuttal pattern (avoid):** Treating activation as a marketing problem rather than a product problem.
**Evidence required to ace it:** Funnel decomposition with stage-by-stage drop-off; named fix and expected impact.

---

## Section 10: Cross-Cutting

### IO-36: "Tell me about your last setback"

**Likelihood:** HIGH
**Stage:** All
**Slide triggered by:** any
**Investor voice:** "Tell me about a recent setback. What happened, what did you learn?"
**Strongest rebuttal pattern:** Name a specific, recent, substantive setback (not "we hired too fast" — too generic). State what you learned and what you changed.
**Weakest rebuttal pattern (avoid):** "We haven't really had any setbacks." (Disqualifying — signals lack of self-awareness or honesty.)
**Evidence required to ace it:** Genuine self-awareness about a real failure.

---

### IO-37: "Why are you the right partner for us?"

**Likelihood:** MEDIUM
**Stage:** All
**Slide triggered by:** end of meeting
**Investor voice:** "Why are we — specifically — the right partner for this round?"
**Strongest rebuttal pattern:** State the specific reason this fund (their thesis, their portfolio, the partner's background) is a fit. Avoid generic praise.
**Weakest rebuttal pattern (avoid):** "You're a great fund." (Hollow.)
**Evidence required to ace it:** Pre-meeting research on the fund and partner.

---

### IO-38: "What would make you turn this down?"

**Likelihood:** LOW
**Stage:** A+
**Slide triggered by:** end of meeting
**Investor voice:** "If I asked you to identify the strongest reason *not* to invest in this company, what would you say?"
**Strongest rebuttal pattern:** Name a genuine concern, then state how you're addressing it. Signals honesty and self-awareness.
**Weakest rebuttal pattern (avoid):** Trivial concerns or none. The partner already has a list — they want to see if you match.
**Evidence required to ace it:** Genuine knowledge of the company's weaknesses.

---

### IO-39: "Walk me through the cap table"

**Likelihood:** HIGH
**Stage:** A+
**Slide triggered by:** post-meeting due diligence
**Investor voice:** "Walk me through ownership today, what this round does, what your post-money looks like, and what's left for the next round."
**Strongest rebuttal pattern:** Have a clean cap table summary ready. State founder ownership, employee pool, existing investors, this round, post-money. State the planned dilution headroom for the next 18 months.
**Weakest rebuttal pattern (avoid):** Fuzziness on dilution math.
**Evidence required to ace it:** A clean, current cap table; named option pool refresh plan if applicable.

---

### IO-40: "What's your exit strategy?"

**Likelihood:** MEDIUM
**Stage:** A+
**Slide triggered by:** end of meeting
**Investor voice:** "What does an outcome look like for us? Acquisition? IPO? In how many years, at what scale?"
**Strongest rebuttal pattern:** State both pathways. For acquisition, name plausible acquirers and their pattern of acquiring at the relevant scale. For IPO, state the revenue level historically required and the timeline. Acknowledge uncertainty.
**Weakest rebuttal pattern (avoid):** "We're focused on building, not exiting." (Founder-friendly but unhelpful to a fund needing returns.)
**Evidence required to ace it:** Knowledge of comparable exits in the category with scale and multiple.

---

## Section 11: How `/investor-coach:adversarial-review` uses this catalogue

1. **Read `PITCH.yaml`** for stage.
2. **Filter the catalogue** to objections where the stage matches.
3. **Read the deck artifacts** (NARRATIVE.md, slides/, MARKET_RESEARCH.md, financial-model.yaml, proof-points/).
4. **Score current rebuttal strength** for each filtered objection: Strong / Medium / Weak / None — based on whether the deck contains the evidence required to ace it.
5. **Rank riskiest-first** (per AT, riskiest-by-impact-then-by-lowest-evidence first).
6. **Select 10–15** for `05-adversarial/ADVERSARIAL_REVIEW.md`.
7. **For each selected objection**, produce: investor voice, weakest claim it targets, current rebuttal score, mitigation path (with at least two concrete options).

The skill does not invent objections beyond the catalogue at this version.
Future versions MAY add partner-specific objections by reading
partner-research notes if the founder provides them.

---

## Version History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-05-13 | Initial release. Forty canonical objections across nine categories, stage-tagged, with strongest/weakest rebuttal patterns and required evidence. |
