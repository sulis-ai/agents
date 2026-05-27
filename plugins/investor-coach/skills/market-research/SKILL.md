---
name: market-research
description: >
  Phase 4 of the Investor Deck Coach. Runs a rigorous, linear market-research
  pipeline (gather → tier → triangulate → surface contradictions → synthesise)
  adapted from the research-synthesis methodology — without the triad lens
  structure. Produces MARKET_RESEARCH.md, sources/src-NNN-*.md, and
  proof-points/pp-NNN-*.md. Every numerical claim downstream traces to a
  proof-point produced by this skill.
user_invocable: true
---

# Market Research

When invoked, build the evidence dossier behind the deck. Every claim
about market size, growth, customer pain, or competitive positioning
that will appear in the deck or the financial model is sourced and
tiered here.

## When to invoke

- After `/investor-coach:discovery` and `/investor-coach:brand-discovery` are complete.
- When new evidence surfaces that requires re-grounding existing
  claims.

## When NOT to invoke

- Before discovery — the open questions captured in DISCOVERY.md §9
  drive the research.
- After narrative composition — if research changes, the narrative
  must be revised, not patched.

---

## Methodology

A single linear pipeline, **not a multi-lens triad**. Five steps,
performed in order. Adapted from
`tria/methodology/outcomes/utility/research-synthesis` (triad collapsed
into integrated rigor checks).

### Step 1 — Define scope

From `DISCOVERY.md` §9 (open questions), `PITCH.yaml` (stage,
audience), and a brief conversation with the founder, write a scope
declaration:

- **Primary question** — what this research must answer for the deck
- **Sub-questions** — supporting questions
- **Source types prioritised** — analyst reports, regulatory filings,
  primary interviews, public filings, practitioner blogs
- **Time period** — typically 2-3 years of historical + relevant
  forward projections
- **Goal context** — which deck slides this research will support

Output: Scope block at the top of `MARKET_RESEARCH.md`.

### Step 2 — Gather evidence (Evidence Gathering)

Search across multiple categories. For **every supporting search, run
a counter-search** (per CI / Critical Thinking Standard).

| Type of search | Example queries |
|---|---|
| Supporting | "[market] size 2025 report" |
| Counter | "[market] decline", "[market] saturation", "why [market] is shrinking" |
| Triangulation | "[market] growth bottom-up" |
| Competitor | "[competitor] vs [competitor] market share" |
| Adversarial | "[market thesis] is wrong" |

For each source found:

1. Create `sources/src-NNN-{slug}.md` per template
2. Record: title, URL, type, publication date, accessed date
3. Assign tier (T1–T4) per FN-05 with rationale
4. Document biases, limitations, recency, methodology transparency

**Minimum threshold:** ≥3 independent sources before proceeding. ≥1
Tier 1 or Tier 2 source per major claim.

**Independent** means the sources do not derive from each other.
Sources citing each other count as ONE source (SI / Source
Independence).

### Step 3 — Triangulate (Triangulation Gate)

For every market-sizing figure (TAM, SAM, SOM), produce **both**:

- **Top-down:** start from an industry-analyst figure and segment
  down. Cite source.
- **Bottom-up:** start from estimated unit volume × average price.
  Show the math. Cite source for both inputs.

If top-down and bottom-up agree within 2×, mark convergent. If they
diverge by more than 2×, write an explicit reconciliation note (e.g.,
"top-down includes adjacent segments we don't serve").

For every growth rate, cite ≥2 independent sources.

### Step 4 — Surface contradictions (do not average)

When sources disagree:

- Preserve the disagreement explicitly in `MARKET_RESEARCH.md` under
  "Contradictions".
- For each contradiction: Position A (+ source + tier), Position B
  (+ source + tier), why they might differ (methodological /
  temporal / definitional / genuine uncertainty), and resolution
  (reconciled by …, OR unresolvable — treat as caveat).
- **Do not average.** Averaging hides signal. Preserving the tension
  is what makes the research useful.

### Step 5 — Extract atomic proof-points (Atomization Gate)

For every load-bearing claim that will appear in the deck or financial
model, create a proof-point file:

- `proof-points/pp-NNN-{slug}.md` per template
- One claim, one source, per file
- If a claim has multiple supporting sources, create one proof-point
  per source and reference all from the deck slide

This atomization is what makes the deck traceable. Every number on
every slide links to one or more `pp-NNN`s; every `pp-NNN` links to
one `src-NNN`.

### Step 6 — Synthesise (SCQA + Pyramid)

Compose `MARKET_RESEARCH.md`:

1. **Decision Summary (SCQA)** at the top
2. **Executive headline findings** (Pyramid Principle — lead with
   conclusion, ≤4 supporting legs)
3. **Sources Consulted** table with tier distribution
4. **Key Findings** with per-finding confidence and supporting
   proof-points
5. **Market Sizing (TAM/SAM/SOM)** with both methods
6. **Competitive Landscape** with named competitors and falsifiable
   differentiation
7. **Convergence Points** table
8. **Contradictions** (preserved, not averaged)
9. **Gaps Identified** with impact rating
10. **Confidence Assessment** overall + per-finding
11. **Recommendations for the Deck**
12. **Methodology Notes** (reproducibility, sources not consulted)

### Step 7 — Verdict

Set the verdict at the top of `MARKET_RESEARCH.md`:

| Verdict | Criteria |
|---|---|
| **STRONG** | ≥3 Tier-1/2 sources converging on key findings; all market-sizing triangulated |
| **ADEQUATE** | Tier-1/2 sources with some gaps OR Tier-2 convergence with one or two minor gaps |
| **WEAK** | Mostly Tier-3/4 OR significant contradictions unresolved |
| **INSUFFICIENT** | <3 sources OR critical gaps in credible evidence |

If verdict is INSUFFICIENT, do NOT propose the next phase. Return to
the founder, surface what's missing, propose a re-run with additional
search categories.

---

## Anti-patterns (forbidden)

The methodology explicitly forbids these patterns:

| Anti-pattern | Correction |
|---|---|
| Inventing plausible-sounding sources | Verify every source URL/file is real before citing |
| Single-source key findings | Every key finding ≥2 sources or flagged provisional |
| Hidden contradictions | Preserve and analyse divergence |
| Premature synthesis | Steps run in order; don't synthesise before triangulation |
| Vague attributions ("many sources say") | Use counts: "3 Tier-1 sources" |
| All evidence pointing one direction | Document counter-searches explicitly |
| Treating all sources as equal | Every source gets a tier with rationale |
| Hiding "could not determine" | Disclose with the searches attempted |
| TODOs in output | Gate: zero TODOs/TBDs in final MARKET_RESEARCH.md |
| Answering narrow question when foundational issue found | Escalate to founder |

---

## Coaching gates

- **Show, don't tell:** when the founder's claimed market size is
  unsupported, walk through the bottom-up math together rather than
  declaring it wrong.
- **CI in practice:** when the founder cites a McKinsey report, run a
  counter-search ("[market] not growing", "[market] saturation") and
  surface the result before accepting the figure.
- **SI in practice:** when two sources agree, check whether they're
  actually independent or both citing the same upstream number.
- **EH in practice:** distinguish what's known (sourced) from what's
  inferred (derived) from what's assumed (taken as given). Mark
  assumptions for adversarial review.

---

## Refusals

Refuse, factually, if:

- The founder asks to include a market-size figure without a tiered
  source → "I can't put that in the deck without a proof-point. Let's
  find a source or mark it as an assumption to flag for the
  adversarial review."
- The founder asks to skip triangulation → "Top-down without
  bottom-up is the most common pitch failure mode. Five more
  minutes of math here saves a partner objection."
- The founder asks to remove a contradiction from the report → "The
  contradiction is signal. If a partner asks 'I saw a McKinsey report
  with a different number,' you want to be ready with the answer.
  Hiding it doesn't help."

---

## Gotchas

- **Don't crawl indefinitely.** Diminishing returns set in around
  15–20 sources for most pitches. The verdict gate determines
  sufficiency, not source count.
- **Don't trust a single analyst report as Tier 1.** Analyst reports
  are Tier 2. Tier 1 is primary data — the company's own customer
  list, a regulator's filing, a survey with named methodology.
- **Don't conflate TAM with revenue opportunity.** TAM is the total;
  SAM is what your motion reaches; SOM is what you'll capture in the
  horizon.
- **Don't extrapolate from a single cohort.** Growth-rate claims
  based on six months of data should be flagged LOW confidence.
- **Don't average contradictions.** A 22% growth claim and a 5%
  growth claim don't become 13%. They become a contradiction to
  resolve or to surface.

---

## Output checklist

Before declaring market research complete:

- [ ] Scope declared at top of `MARKET_RESEARCH.md`
- [ ] ≥3 independent sources, each tiered
- [ ] ≥1 Tier-1/2 source per major claim
- [ ] TAM / SAM / SOM each triangulated top-down + bottom-up
- [ ] Counter-searches documented for every supporting search
- [ ] Contradictions surfaced, not averaged
- [ ] Atomic proof-points created for every load-bearing claim
- [ ] SCQA decision summary at top
- [ ] Pyramid-style findings (lead with conclusion)
- [ ] Confidence levels assigned per finding
- [ ] Gaps identified with impact rating
- [ ] Verdict (STRONG / ADEQUATE / WEAK / INSUFFICIENT) set
- [ ] No TODO/TBD markers in final output
- [ ] If verdict ≥ ADEQUATE: propose `/investor-coach:financial-model`
- [ ] If verdict = INSUFFICIENT: surface gaps to founder, propose re-run
