# Critical Thinking Standard

<!-- summary -->
Thirteen analytical principles and nine anti-patterns that govern how research, analysis,
and reasoning are conducted. Organised into three phases that map to how analysis is
actually performed: **input** (framing the question, evaluating incoming evidence),
**processing** (reasoning about the evidence), and **output** (structuring and expressing
conclusions). Each principle states when it applies and what to do. Ensures rigour,
intellectual honesty, and evidence-based conclusions across all analytical work.
<!-- /summary -->

> **Version:** 2.0.0
> **Status:** Active

---

## Provenance

These principles encode analytical methodology drawing on: structured analytic techniques
(Heuer & Pherson, 2014), Bayesian reasoning, MECE problem decomposition (Minto, 1987),
the Pyramid Principle (Minto, 1987), SCQA narrative framing, epistemic humility literature,
Lean Startup assumption testing (Maurya, 2012; Ries, 2011), Continuous Discovery (Torres,
2021), and practitioner knowledge from research, strategy, and validation work.

---

## Boundary Definition

This standard contains **universal critical thinking principles only**. Content belongs
here if and only if it passes the **ProjectX test**: replacing every project name, file
path, and technology-specific example with a fictional "ProjectX" equivalent requires
zero semantic changes to the principle statement.

Content that fails the ProjectX test belongs in the project's architecture file, not here.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. Violations block delivery. |
| **SHOULD** | Default. Deviation requires explicit justification. |

---

## Three-Phase Model

Standards are organised by the phase of analytical work where they apply. This structure
tells you **when** to apply each principle, not just **what** it says.

| Phase | When It Applies | Principles |
|-------|----------------|------------|
| **Input** | Receiving a question, task, or body of evidence. Before analysis begins. | BI, OI, CI, SI, HE |
| **Processing** | Reasoning about the evidence. During analysis. | FR, CC, MECE, PG, EH, AT |
| **Output** | Structuring and expressing conclusions. When producing deliverables. | PP, PL |

---

## Input Phase — Framing and Evidence Gathering

> **When:** You receive a question, task, or body of evidence.
> **What to do:** Frame the question before researching. Start from external reality.
> Gather evidence from both sides. Verify source independence. Rank evidence by type.

<!-- detail -->

### BI: Begin with Inquiry

**Severity:** MUST

Before producing any analysis, articulate the question you are answering. If you cannot
state the question clearly, you are not ready to begin analysis.

| Attribute | Detail |
|-----------|--------|
| **Rule** | Every analytical output begins with an explicitly stated question or hypothesis. The question is written down before research begins. |
| **Template** | "The question this analysis answers is: [question]. This question matters because: [context]. We will know the answer is adequate when: [success criteria]." |
| **Verification** | The stated question exists. It is specific enough to be answerable. It includes success criteria. The analysis directly addresses the stated question. |
| **Red Flags** | Analysis that "explores" a topic without a stated question. Conclusions that answer a different question than the one stated. Questions so broad they cannot be falsified ("What is the state of the market?"). |

---

### OI: Outside-In Reasoning

**Severity:** SHOULD

Start from external reality — user needs, market conditions, observed behaviour — and
reason inward to solutions. Do not start from internal structure and reason outward
to justify existing approaches.

| Attribute | Detail |
|-----------|--------|
| **Rule** | Analysis begins with external evidence (user behaviour, market data, observed outcomes) before consulting internal structure (existing systems, current categorisations, organisational boundaries). Internal structure informs feasibility, not desirability. |
| **Template** | "External evidence shows: [observations]. Given this evidence, the ideal approach would be: [unconstrained solution]. Given internal constraints ([constraints]), the feasible approach is: [constrained solution]. Gap between ideal and feasible: [gap]." |
| **Verification** | The analysis starts with external evidence. Internal structure is consulted for feasibility, not as the starting point. Conclusions are not merely rationalisations of the current approach. |
| **Red Flags** | "We should do X because that's how our system is structured." Decomposing a problem along internal boundaries rather than along the user's actual experience. Skipping external evidence and starting from existing categorisations. |

---

### CI: Counter-Investigation

**Severity:** MUST

For every supporting search, conduct a counter-search. Evidence gathered in only one
direction is advocacy, not analysis.

| Attribute | Detail |
|-----------|--------|
| **Rule** | For every search that supports a hypothesis, conduct at least one search designed to find counter-evidence. Document counter-evidence explicitly, even if weak or absent. Search at least two different sources or communities for triangulation. |
| **Template** | "Supporting search: [query]. Counter-search: [query]. Counter-evidence found: [findings or 'none found — methodology limitations noted']. Triangulation: [sources consulted]." |
| **Example** | Research question: "Do developers struggle with deployment complexity?" Required searches: (1) "deployment complexity frustration developers" (supporting), (2) "deployment made easy" or "deployment solved" (counter), (3) "deployment best practices 2025" (neutral/current state). |
| **Verification** | Counter-searches are documented for each supporting search. Counter-evidence is presented alongside supporting evidence. Methodology limitations are noted. |
| **Red Flags** | All evidence points in one direction with no documented counter-search. Research stops as soon as confirming evidence is found. |

---

### SI: Source Independence

**Severity:** MUST

Conclusions must be supported by multiple independent sources. A single source, regardless
of its authority, is a data point — not a conclusion.

| Attribute | Detail |
|-----------|--------|
| **Rule** | No factual claim rests on a single source. When only one source exists, the claim is explicitly marked as single-source and treated as provisional. Independent means the sources do not derive from each other — sources citing each other count as ONE source. |
| **Template** | "This claim is supported by [N] independent sources: [list]. These sources are independent because [explanation]." Or: "This claim rests on a single source ([source]). It is treated as provisional." |
| **Verification** | Each factual claim cites at least two independent sources. Single-source claims are explicitly flagged. Sources are actually independent (not one quoting the other). |
| **Red Flags** | Multiple citations that all trace back to the same original source. Sources from a single community or vendor ecosystem presented as independent. Citing a secondary summary instead of the primary source. Complaints from a specific time period presented as current (may be resolved). |

---

### HE: Hierarchy of Evidence

**Severity:** MUST

Not all evidence is equal. Rank evidence by reliability and make the ranking explicit
when presenting conclusions.

| Attribute | Detail |
|-----------|--------|
| **Rule** | When multiple types of evidence inform a conclusion, rank them by reliability. Higher-ranked evidence takes precedence when evidence conflicts. |
| **Evidence Hierarchy (strongest to weakest)** | 1. Directly observed, measured data from the specific context. 2. Systematic reviews or meta-analyses of relevant research. 3. Controlled experiments or rigorous studies. 4. Observational data from analogous contexts. 5. Expert opinion with stated reasoning. 6. Anecdote, analogy, or common sense. |
| **Verification** | The type of evidence is identified for each claim. When evidence conflicts, higher-ranked evidence takes precedence or the conflict is documented. Conclusions are not based solely on low-ranked evidence when higher-ranked evidence is available. |
| **Red Flags** | Treating an anecdote as equivalent to measured data. Ignoring systematic evidence because it conflicts with expert opinion. Presenting expert opinion as empirical fact. |

<!-- /detail -->

---

## Processing Phase — Reasoning and Analysis

> **When:** You have gathered evidence and are reasoning about it.
> **What to do:** Ensure claims are falsifiable. Calibrate confidence to evidence.
> Decompose problems cleanly. Ground analysis in irreducible units. Acknowledge what
> you don't know. Argue against your own conclusions.

<!-- detail -->

### FR: Falsifiability Requirement

**Severity:** MUST

Every claim must be stated in a form that can, in principle, be proven wrong. If a
claim cannot be falsified, it is not an analytical conclusion — it is an opinion or
a tautology.

| Attribute | Detail |
|-----------|--------|
| **Rule** | Claims are stated in falsifiable form. For each claim, identify what evidence would disprove it. If no evidence could disprove it, restate the claim or acknowledge it as a value judgement. For strategic bets, define explicit stop/pivot/re-evaluate criteria. |
| **Template** | "Claim: [statement]. This claim would be falsified by: [specific evidence that would disprove it]." For strategic bets: "We will STOP if: [condition]. We will PIVOT if: [condition]. We will RE-EVALUATE if: [trigger]." |
| **Pre-Mortem** | For significant decisions: "If this fails, the most likely reasons are: 1. [Reason]. 2. [Reason]. 3. [Reason]." |
| **Verification** | Each analytical claim has an identified falsification condition. Strategic bets have explicit stop/pivot criteria. Pre-mortem is documented for significant decisions. |
| **Red Flags** | Claims that are true by definition. Claims so vague that any outcome confirms them. Moving the goalposts when counter-evidence appears. "This approach might work" — unfalsifiable because "might" covers all outcomes. |

---

### CC: Confidence Calibration

**Severity:** MUST

Attach explicit confidence levels to claims. Match the precision of claims to the
precision of evidence. Do not present rough estimates as exact figures or general
trends as specific predictions.

| Attribute | Detail |
|-----------|--------|
| **Rule** | Every non-trivial claim carries an explicit confidence indicator calibrated to evidence quality and quantity, not to the analyst's conviction. Ranges are preferred over point estimates when uncertainty is significant. |
| **Confidence Scale** | **High** — Multiple independent sources, directly observed data, or well-established research. **Medium** — Some supporting evidence but gaps exist, or evidence is indirect. **Low** — Single source, extrapolation from limited data, or analyst judgement with minimal supporting evidence. |
| **Confidence Decay** | Evidence older than 2 years: flag for re-validation. Technology-specific claims decay faster (6–12 months). Market and behaviour claims may persist longer (2–3 years). |
| **Template** | "Claim: [statement]. Confidence: [High/Medium/Low]. Basis: [evidence summary]. Key uncertainty: [what could change this assessment]." |
| **Verification** | Claims have explicit confidence levels. The stated confidence matches the underlying evidence. Key uncertainties are identified. Claim precision matches evidence precision — no false precision. |
| **Red Flags** | Presenting low-confidence claims with the same certainty as high-confidence claims. "The market opportunity is $4,237,000" based on back-of-envelope estimation. Precise numbers without error margins. |

---

### MECE: Mutually Exclusive, Collectively Exhaustive

**Severity:** SHOULD

When decomposing a problem, ensure categories are mutually exclusive (no item belongs
in more than one category) and collectively exhaustive (all items are accounted for).

| Attribute | Detail |
|-----------|--------|
| **Rule** | Problem decompositions, option analyses, and categorisation schemes are MECE. When perfect MECE is impractical, deviations are documented with rationale. Apply the Leg Test: if removing a category doesn't weaken the conclusion, it's fluff. Apply the "So What?" test: every finding must affect the recommendation. |
| **Template** | "The options/categories are: [list]. These are mutually exclusive because: [explanation]. These are collectively exhaustive because: [explanation or acknowledgement of known gaps]." |
| **Verification** | No item falls into multiple categories. All relevant items are accounted for. Catch-all "Other" categories do not contain more items than named categories. Every finding passes the "So What?" test. |
| **Red Flags** | Overlapping categories that force items into multiple buckets. Missing categories that cause items to fall through. Findings that don't affect the recommendation — fluff, remove them. "We can build, buy, or partner" presented as exhaustive when "do nothing" was not considered. |

---

### PG: Primitive Grounding

**Severity:** SHOULD

Every analysis must be grounded in irreducible, independently testable units at the
stated level of analysis. Primitives are the atoms of analysis — MECE validates that
categories don't overlap and cover the space; Primitive Grounding validates that those
categories are real rather than arbitrary groupings.

| Attribute | Detail |
|-----------|--------|
| **Rule** | Every analysis identifies its primitives at the stated level of analysis. A primitive is irreducible at that level: it cannot be decomposed further without changing the decision it informs. Each primitive must be independently changeable, independently validatable, and independently falsifiable. |
| **Level-of-Analysis Anchor** | Every primitive decomposition declares its decision context. Primitives are relative to the decision being made, not absolute. The same element may be primitive at one level and composite at another. |
| **Termination Condition** | Decomposition stops when further splitting would not change any decision at the stated level of analysis. Over-decomposition is as harmful as under-decomposition. |
| **Template** | "Decision context: [what decision this informs]. Level: [e.g., strategy, architecture, implementation]. Primitives: [list with independence and irreducibility justification]." |
| **Verification** | Primitives are declared with decision context. Each passes the independence test. Decomposition has stopped at the right level. Two "primitives" that must always change together are flagged as one primitive or a hidden dependency. |
| **Red Flags** | Categories that pass MECE but could be reorganised arbitrarily. No declared level of analysis. Decomposition continuing past the point where it changes decisions. |

---

### EH: Epistemic Humility

**Severity:** MUST

Acknowledge the limits of your knowledge explicitly. Distinguish between what you know,
what you think, and what you are guessing. Treat "no evidence found" as a finding, not
a gap to hide.

| Attribute | Detail |
|-----------|--------|
| **Rule** | Every analysis explicitly identifies: what is **known** (supported by evidence), what is **inferred** (derived from evidence but not directly observed), and what is **assumed** (taken as given without direct evidence). Assumptions are documented and flagged for validation. What couldn't be determined is disclosed with the searches attempted. |
| **On Weak Evidence** | Weak evidence should guide exploration, not warrant dismissal. Distinguish: "bad idea" (evidence actively contradicts), "unvalidated idea" (insufficient evidence to judge), "needs exploration" (promising but requires more research). When evidence is insufficient, identify the next research step rather than dismissing. |
| **Template** | "Known: [evidence-based facts]. Inferred: [logical deductions from known facts]. Assumed: [statements taken as given — to be validated]. Could not determine: [questions and searches attempted]." |
| **Verification** | The analysis distinguishes known facts, inferences, and assumptions. Assumptions are listed and flagged. Gaps are disclosed with methodology. Unvalidated ideas are given exploration paths, not dismissed. |
| **Red Flags** | Presenting assumptions as established facts. No uncertainty language anywhere. "This won't work" without evidence. "Nobody wants this" without counter-search. Hiding what couldn't be determined. |

---

### AT: Adversarial Posture

**Severity:** SHOULD

The default posture for validation is adversarial: seek to disprove before seeking to
confirm. Actively argue against your own conclusions before presenting them.

| Attribute | Detail |
|-----------|--------|
| **Rule** | Before finalising a conclusion, construct the strongest possible argument against it. Seek evidence that would disprove the hypothesis before seeking evidence that would confirm it. Test riskiest assumptions first — ordered by impact (what damage if wrong) then by evidence level (least evidence first). |
| **Template** | "Conclusion: [statement]. Strongest counter-argument: [argument]. Why the conclusion holds despite this: [rebuttal]. Conditions under which the counter-argument would prevail: [conditions]." |
| **Confirmation-Seeking Exception** | If validation starts from "how do we confirm this?", the choice must be stated explicitly with rationale for why adversarial posture was inappropriate. |
| **Verification** | Counter-arguments exist for each major conclusion. Counter-arguments are genuinely strong (not strawmen). Rebuttals address counter-arguments directly. Riskiest assumptions are tested first. |
| **Red Flags** | No counter-arguments considered. Counter-arguments that are weak strawmen. All tests designed to produce positive results. Riskiest assumptions tested last or not at all. Validation plan that starts with "How do we confirm...?" without justification. |

<!-- /detail -->

---

## Output Phase — Communication and Presentation

> **When:** You are structuring and expressing your conclusions.
> **What to do:** Lead with the conclusion, not the journey. Use precise language.
> Back every quantitative term with a metric. Frame findings for the decision maker.

<!-- detail -->

### PP: Pyramid Principle

**Severity:** SHOULD

Start with the conclusion. Build supporting evidence beneath it. Frame findings as
a story for the decision maker, not a technical inventory.

| Attribute | Detail |
|-----------|--------|
| **Rule** | Lead with the recommendation or conclusion. Support with 2–4 "legs" (key reasons), each of which is necessary (passes the Leg Test). Details follow the structure, not precede it. For decision-oriented outputs, use SCQA framing: Situation (context), Complication (what changed or went wrong), Question (what needs deciding), Answer (what to do). |
| **Why Pyramid Structure** | Traditional narrative (context → evidence → analysis → conclusion) buries the lead. Pyramid structure (conclusion → supporting legs → details) lets the reader know the answer immediately and drill into evidence as needed. |
| **SCQA Template** | "**Situation:** [context]. **Complication:** [what problem or change emerged]. **Question:** [what needs deciding — may differ from original if complications warrant]. **Answer:** [what to do]." |
| **Escalation** | If findings reveal issues bigger than the original question — methodology inconsistency, architectural conflict, missing foundational decision — flag this prominently. The Complication can change the Question. |
| **Verification** | Output leads with conclusion. Supporting legs are necessary (pass Leg Test). Details follow structure. Decision-oriented outputs use SCQA. If complications changed the question, this is flagged. |
| **Red Flags** | Starting with background/context instead of conclusion. Burying the recommendation at the end. Listing findings without synthesising into legs. Answering a narrow question when a bigger issue was discovered. |

---

### PL: Precision of Language

**Severity:** SHOULD

Use precise language. Avoid weasel words, hedge stacking, unsupported superlatives,
and vague quantifiers. When you mean "some", don't say "many." When you mean
"we believe", don't say "it is known."

| Attribute | Detail |
|-----------|--------|
| **Rule** | Use specific language. Quantify where possible. Attribute claims to their source. Avoid passive constructions that hide agency. Avoid stacking hedges. Every quantitative term requires a metric or explicit qualification. |
| **Prohibited Terms** | "revolutionary", "disruptive", "unprecedented", "game-changing", "best-in-class", "cutting-edge", "world-class", "amazing", "incredible." Replace with specific comparisons or remove entirely. |
| **Terms Requiring Metrics** | "significant" → define threshold ("significant (>40% improvement)"). "many" → quantify ("many (12 of 15 sources)"). "most" → percentage. "growing" → rate. "large" → size. "fast" → measurement. |
| **Words to Avoid** | "it is known that" (known by whom?), "clearly" (if it were clear, you wouldn't need the word), "stakeholders" (which ones?), "best practice" (according to whom?), "leverage" (use "use"), "synergy" (describe the specific interaction). |
| **Verification** | No prohibited terms remain. Quantitative terms have metrics. Claims are attributed to specific sources. Passive voice is not used to hide agency. Hedge words are used singly, not stacked. |
| **Red Flags** | Multiple hedge words in one sentence. Vague quantifiers without supporting data. "It is widely believed that best practices suggest leveraging synergies to drive significant value" — this sentence says nothing. |

<!-- /detail -->

---

## Anti-Patterns

Nine common reasoning failures. Each is tagged with the principles that mitigate it.

<!-- detail -->

| ID | Anti-Pattern | How It Manifests | Detection | Mitigation |
|----|-------------|-----------------|-----------|------------|
| AP-01 | **Confirmation Bias** | Cherry-picking data. Dismissing contradictory evidence as "outliers." Stopping research at first confirming result. | All evidence points one direction. No counter-evidence documented. | CI, AT — counter-search and adversarial posture. |
| AP-02 | **Anchoring** | First estimate becomes the baseline. Initial framing constrains all analysis. A competitor's approach becomes the template. | Final conclusions suspiciously close to initial estimates. Alternative framings not considered. | OI — outside-in reasoning. Generate estimates independently before consulting benchmarks. |
| AP-03 | **Survivorship Bias** | "X did Y and succeeded, so we should do Y" — ignoring failures. Analysing only active users, not churned. | Sample includes only successes. Failure cases absent. | Ask: "What would this data look like if we included failures?" |
| AP-04 | **Authority Bias** | "The CEO said X, so X is true." Expert opinion treated as empirical evidence. Valid criticism dismissed for lack of credentials. | Appeals to authority instead of evidence. Source prestige substitutes for evaluation. | HE — hierarchy of evidence. Ask: "Would I accept this from an unknown source?" |
| AP-05 | **Sunk Cost Fallacy** | "We've spent 6 months on this, we can't stop now." Evaluating options by past cost, not future value. | Past investment cited as reason to continue. No future-value analysis. | FR — define upfront what would cause abandonment. Evaluate on future value only. |
| AP-06 | **Narrative Fallacy** | "We launched X, metrics improved, therefore X caused it." Post-hoc stories presented as causal analysis. | Causal claims without controlled comparison. Alternative explanations not considered. | CC — mark post-hoc explanations as low confidence. Demand controlled comparison. |
| AP-07 | **False Dichotomy** | "Either we build it ourselves or we don't do it." Only two options presented. | Exactly two options. No middle ground explored. | MECE — enumerate all options. Ask: "What options are we not seeing?" |
| AP-08 | **Scope Creep in Analysis** | "One more interesting angle." Deliverables grow beyond brief. Tangential findings given equal weight. | Analysis far beyond original scope. Original question buried. | BI — return to stated question. "Does this finding help answer the question?" |
| AP-09 | **Precision Bias** | "ROI will be 14.3%" based on rough estimates. Precise numbers without error margins. | Precision exceeds input data quality. | CC — use ranges when uncertain. Match output precision to input precision. |

<!-- /detail -->

---

## Quality Checklist

Before delivering any analytical output, verify against each phase:

### Input Phase
- [ ] **BI:** The question being answered is explicitly stated with success criteria
- [ ] **OI:** Analysis starts from external evidence, not internal structure
- [ ] **CI:** Counter-searches conducted and documented for each supporting search
- [ ] **SI:** No factual claim rests on a single source (or single-source claims are
  flagged as provisional)
- [ ] **HE:** Evidence types are identified and ranked; higher-ranked evidence takes
  precedence

### Processing Phase
- [ ] **FR:** All claims are stated in falsifiable form with identified falsification
  conditions
- [ ] **CC:** All non-trivial claims carry explicit confidence levels calibrated to
  evidence quality; claim precision matches evidence precision
- [ ] **MECE:** Problem decompositions are mutually exclusive and collectively exhaustive
  (or gaps are documented); every finding passes the "So What?" test
- [ ] **PG:** Primitives are identified at the stated level of analysis with decision
  context declared
- [ ] **EH:** Known facts, inferences, and assumptions are distinguished; assumptions
  are documented; gaps are disclosed
- [ ] **AT:** Counter-arguments constructed and addressed for major conclusions;
  riskiest assumptions tested first

### Output Phase
- [ ] **PP:** Output leads with conclusion, supported by necessary legs; SCQA framing
  used for decision-oriented outputs
- [ ] **PL:** No prohibited terms; quantitative terms have metrics; no hedge stacking

### Anti-Patterns
- [ ] Output has been checked against AP-01 through AP-09

---

## Application

These principles apply across all analytical work. The phase model helps prioritise:

### Research Tasks

All thirteen principles apply. Research is the primary domain for this standard.
Pay particular attention to:
- **Input:** CI (counter-searches), SI (source independence), HE (evidence ranking)
- **Processing:** EH (distinguish facts from inferences), AT (adversarial posture)
- **Anti-patterns:** AP-01 (confirmation bias), AP-03 (survivorship bias)

### Strategic Analysis

Strategy work is especially vulnerable to narrative construction and false precision.
Pay particular attention to:
- **Input:** OI (start from market reality, not internal structure)
- **Processing:** FR (falsifiable strategic claims), CC (confidence on projections),
  AT (seek to disprove)
- **Anti-patterns:** AP-05 (sunk cost), AP-06 (narrative fallacy)

### Validation Work

When validating designs, plans, or approaches against requirements or evidence.
Pay particular attention to:
- **Input:** BI (state what you are validating and success criteria)
- **Processing:** AT (argue against the thing being validated), EH (surface assumptions)
- **Anti-patterns:** AP-01 (confirmation bias), AP-02 (anchoring)

### Requirements Specification

When defining requirements, user needs, or problem statements.
Pay particular attention to:
- **Input:** OI (derive from external evidence, not internal structure)
- **Processing:** MECE (complete, non-overlapping requirements), CC (match precision
  to confidence)
- **Anti-patterns:** AP-03 (survivorship bias — consider unserved users)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-13 | Initial adaptation. 13 principles, 9 anti-patterns. |
| 2.0.0 | 2026-03-19 | Major revision. Synthesised from two battle-tested source standards. Restructured around three-phase model (input/processing/output) for prompt-effective application. Added CI, HE, PG, PP, PL. Enriched FR (pre-mortem, stop/pivot), CC (confidence decay, proportional precision), EH (honest uncertainty, exploration guidance), AT (riskiest-first, confirmation exception). Consolidated anti-patterns into table format with principle cross-references. |
