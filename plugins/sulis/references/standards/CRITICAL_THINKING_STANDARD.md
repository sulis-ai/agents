# Critical Thinking Standard

> **Adapted from platform v1.5.0 (2026-03-06). Sulis-local v1.0.0 (2026-05-24).**
> Only "Application to Skills" and "Reference" sections diverge from the platform original.
> Vocabulary: "outcome" → "skill"; "OFM artifact" → "SKILL.md / references / scripts".

> **"Accuracy is paramount. We don't want anyone to waste time going down a rabbit hole.
> We also mustn't be discouraging - they might have something they've not articulated."**

This standard applies to ALL analytical, audit, and assessment skills in sulis. It ensures
balanced, evidence-based decision-making without false positives or premature rejection.

<!-- summary -->

This is the epistemological foundation for analytical work in sulis. It governs HOW skills think — the reasoning disciplines that must hold before any conclusion is stated, any recommendation made, any evidence cited. The companion `SPIRAL_TEMPLATES.md` governs HOW skills are verified (ACCA, dimensions, independence check). Think of it this way: verification without critical thinking produces confidently wrong outputs; critical thinking without verification discipline produces insights that never ship.

Thirteen principles, each with a coded identifier and numbered requirements. The codes matter — they appear in skill quality checklists, VERIFICATION_REPORT.md scoring rationales, and adversarial review templates.

The structural principles come first. MECE (Section 5) demands categories that neither overlap nor leave gaps; the Leg Test and "So What?" test prune fluff. Pyramid Principle (Section 7) inverts traditional narrative: conclusion first, supporting legs beneath, details last. Every analytical output uses SCQA framing (Section 10) — Situation, Complication, Question, Answer — because decision makers need stories, not technical inventories.

Evidence integrity occupies four sections. Balanced Investigation (BI) requires counter-searches for every supporting search. Source Independence (SI) collapses echo chambers into single sources. Confidence Calibration (CC) maps evidence quality to five tiers from VALIDATED down to CONTRADICTED, with explicit decay rates. No Hyperbole (NH) bans superlatives outright and demands metrics behind quantitative language — "significant" means nothing without a threshold.

Three principles govern intellectual honesty under uncertainty. Falsifiability (FR) requires every hypothesis to state what evidence would kill it. Honest Uncertainty (HU) treats "no evidence found" as a finding, not a gap to hide. Encouragement with Honesty (EH) distinguishes "bad idea" from "unvalidated idea" — weak evidence guides exploration, it does not warrant dismissal.

The analytical grounding principles are the most recent additions. Primitive Grounding (PG, v1.3.0) ensures that MECE categories are irreducible at the stated level of analysis, not arbitrary groupings. Decomposition stops when further splitting would not change any decision. Outside-In Reasoning (OI, v1.4.0) requires analysis to begin from external context — user jobs, problem structure, existing landscape — before consulting internal sulis structure. OI is flag-level, not halt-level: violation triggers review, not blocked execution.

Adversarial Testing Posture (AT, v1.5.0) makes the default validation posture adversarial — seek to disprove before seeking to confirm. Confirmation-seeking validation produces the same result as no validation; adversarial validation produces invalidations when the assumption fails, which is the useful output.

Nine anti-patterns (AP-01 through AP-09) codify the most common reasoning failures: cherry-picking, echo validation, optimistic interpretation, premature rejection, confirmation search, recency bias, volume conflation, authority assumption, and over-decomposition.

The Quality Checklist at section end is the pre-flight check. Twenty-three items, each tagged to a principle code. No skill output passes review without it.

For verification mechanics, read `SPIRAL_TEMPLATES.md` (the rubric this standard is scored under). For decomposition procedure, read `DECOMPOSITION_PROCEDURE.md` (the operational complement to Primitive Grounding).

<!-- detail -->

---

## Core Principles

### 1. Balanced Investigation (BI)

> **For every supporting search, conduct a counter-search.**

| Requirement | Description |
|-------------|-------------|
| **BI-01** | For every "X is broken" search, also search "X is solved" or "X best practices" |
| **BI-02** | Document counter-evidence explicitly, even if weak or absent |
| **BI-03** | Note limitations of the research methodology |
| **BI-04** | Search at least 2 different communities/platforms for triangulation |

**Example:**
```
Research Question: "Do developers struggle with deployment complexity?"

REQUIRED SEARCHES:
1. "deployment complexity frustration developers" (supporting)
2. "deployment made easy" OR "deployment solved" (counter)
3. "deployment best practices 2025" (neutral/current state)
```

---

### 2. Source Independence (SI)

> **Triangulation requires INDEPENDENT sources, not echo chambers.**

| Requirement | Description |
|-------------|-------------|
| **SI-01** | Sources citing each other count as ONE source, not multiple |
| **SI-02** | Sources from the same community (e.g., same subreddit) require skepticism |
| **SI-03** | Look for primary sources, not just aggregated opinions |
| **SI-04** | Note when sources may share common bias (e.g., all from startup community) |

**Red Flags:**
- 5 blog posts all citing the same survey
- Multiple Reddit threads started by the same user
- Sources from a single vendor ecosystem
- Complaints from a specific time period (may be resolved)

---

### 3. Falsifiability Requirement (FR)

> **Every hypothesis must have explicit falsification criteria.**

| Requirement | Description |
|-------------|-------------|
| **FR-01** | State "What evidence would change our conclusion?" |
| **FR-02** | Define "We will STOP if..." criteria for strategic bets. Falsification criteria must target specific primitives, not abstractions (see Section 11: Primitive Grounding). |
| **FR-03** | Include pre-mortem: "If this fails, it will be because..." |
| **FR-04** | Set review triggers that force re-evaluation |

**Template for Strategic Bets:**
```markdown
## Bet: {Name}

**Hypothesis:** We believe {X} will result in {Y}.

**Falsification Criteria:**
- We will STOP if: {specific measurable condition}
- We will PIVOT if: {different specific condition}
- We will RE-EVALUATE if: {trigger condition}

**Pre-Mortem:**
If this bet fails, the most likely reasons are:
1. {Reason 1}
2. {Reason 2}
3. {Reason 3}
```

---

### 4. Confidence Calibration (CC)

> **Match confidence level to evidence quality.**

| Status | Evidence Required | Confidence |
|--------|-------------------|------------|
| **VALIDATED** | 5+ independent sources, triangulated | High |
| **SUPPORTED** | 3-4 sources, some triangulation | Medium |
| **EMERGING** | 2 sources, consistent pattern | Low |
| **UNVALIDATED** | <2 sources, no clear pattern | None |
| **CONTRADICTED** | Evidence actively refutes hypothesis | Negative |

**Confidence Decay:**
- Evidence older than 2 years: Flag for re-validation
- Technology-specific claims: Decay faster (6-12 months)
- Market/behavior claims: May persist longer (2-3 years)

---

### 5. MECE Principle (MECE)

> **Every analysis must be Mutually Exclusive and Collectively Exhaustive.**

| Requirement | Description |
|-------------|-------------|
| **MECE-01** | Categories must not overlap (mutually exclusive). Categories must either BE primitives or be explicitly composed OF primitives at the stated level of analysis (see Section 11: Primitive Grounding). |
| **MECE-02** | Categories must cover the entire problem space (collectively exhaustive) |
| **MECE-03** | Apply the "Leg Test" - if removing a category doesn't weaken the conclusion, it's fluff |
| **MECE-04** | Apply the "So What?" test - every finding must affect the recommendation |

**MECE Validation Template:**
```markdown
## MECE Validation

### Mutually Exclusive Check
| Category | Overlaps With? | Resolution |
|----------|----------------|------------|
| {Cat A} | None | ✓ |
| {Cat B} | {Cat A partially} | Split into distinct categories |

### Collectively Exhaustive Check
| Domain | Covered By | Gap? |
|--------|------------|------|
| {Area 1} | {Category A} | ✓ |
| {Area 2} | NOT COVERED | ✗ Add category |

### Leg Test
| Category | If Removed, Does Conclusion Still Stand? | Essential? |
|----------|------------------------------------------|------------|
| {Cat A} | No - conclusion weakens | Essential |
| {Cat B} | Yes - conclusion unchanged | FLUFF - Remove |

### "So What?" Test
| Finding | Does It Change Recommendation? | Keep? |
|---------|-------------------------------|-------|
| {Finding 1} | Yes - affects approach | Keep |
| {Finding 2} | No - interesting but irrelevant | Remove |
```

**Red Flags:**
- Categories that could fit in multiple buckets → not mutually exclusive
- Analysis that misses obvious areas → not collectively exhaustive
- Findings that don't affect the recommendation → fluff, remove them
- Research that doesn't pass the "so what?" test → wasted effort

---

### 6. No Hyperbole (NH)

> **Avoid superlatives unless directly quoting sources.**
> **Zero tolerance for salesy, marketing-speak, or unsubstantiated claims.**

| Requirement | Description |
|-------------|-------------|
| **NH-01** | No superlatives without specific metrics |
| **NH-02** | No prohibited terms (see list below) |
| **NH-03** | Every claim must be verifiable |
| **NH-04** | Include confidence statement with evidence count |

**Anti-Pattern → Correct Approach:**

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| "Everyone struggles with X" | "X% of surveyed developers report struggling with X (Source)" |
| "This is the biggest problem" | "X is frequently cited as a pain point (N sources)" |
| "The market is huge" | "TAM estimated at $X (Source: Y, 2025)" or "TAM: UNKNOWN - requires validation" |
| "Users love this" | "User feedback indicates [specific quote]" |

**Prohibited Terms (remove or replace):**

| Prohibited | Replacement |
|------------|-------------|
| "revolutionary" | "novel approach" or "different from existing solutions in that..." |
| "disruptive" | "changes the existing pattern by..." |
| "unprecedented" | "not found in prior literature" or "first observed in..." |
| "game-changing" | "significant because..." (with specific reason) |
| "best-in-class" | "compared favorably to X, Y, Z because..." |
| "cutting-edge" | "recently developed" or "uses [specific technology]" |
| "world-class" | [remove entirely or cite specific ranking] |
| "amazing/incredible" | [remove entirely or use specific metric] |
| "comprehensive" | "covers {N} of {M} known cases" or "covers categories A/B/C" |
| "robust" | "handles {specific failure modes}" |
| "powerful" | [remove entirely or replace with capability description] |

**Terms Requiring Metric Backing:**

| Term | Metric Required | Example |
|------|-----------------|---------|
| "significant" | Define threshold | "significant (>40% improvement)" |
| "many" | Quantify | "many (12 of 15 sources)" |
| "most" | Percentage | "most (78% of respondents)" |
| "growing" | Rate | "growing (23% YoY)" |
| "large" | Size | "large ($2.3B TAM)" |
| "fast" | Speed | "fast (sub-100ms p99)" |

**Required Qualifiers:**
- Market size: Must cite source OR mark "ESTIMATE - NOT VALIDATED"
- User sentiment: Must reference actual quotes or data
- Competitive claims: Must be verifiable
- Performance claims: Must include measurement methodology

**Linguistic Audit Template:**
```markdown
## Linguistic Audit

### Prohibited Terms Check
| Term Found | Location | Action |
|------------|----------|--------|
| [None found] | — | ✓ |
| OR | | |
| "revolutionary" | Section 3, para 2 | Replaced with "novel approach that..." |

### Terms Requiring Metrics
| Term | Metric Provided? | Status |
|------|------------------|--------|
| "significant" | Yes - "40% improvement" | ✓ |
| "many" | Yes - "12 of 15 sources" | ✓ |

### Confidence Statement
"This conclusion has [HIGH/MEDIUM/LOW] confidence based on [X] independent sources.
We would change this conclusion if [specific evidence]."

### Audit Status
- [ ] No prohibited terms remain
- [ ] All quantitative terms have metrics
- [ ] Confidence statement included
```

---

### 7. Pyramid Principle (PP)

> **Start with the conclusion. Build supporting legs beneath it.**

| Requirement | Description |
|-------------|-------------|
| **PP-01** | Lead with the recommendation/conclusion |
| **PP-02** | Support with 2-4 "legs" (key reasons) |
| **PP-03** | Each leg must be necessary (passes Leg Test) |
| **PP-04** | Details follow the structure, not precede it |

**Why Pyramid Structure?**

Traditional narrative: Context → Evidence → Analysis → Conclusion
- Reader must wade through everything to find the answer
- Buries the lead
- Wastes time if reader disagrees with conclusion

Pyramid structure: Conclusion → Supporting Legs → Details
- Reader knows the answer immediately
- Can drill into supporting evidence as needed
- Efficient for decision-making

**Pyramid Structure Template:**
```markdown
## Recommendation

**Conclusion:** [Do X, not Y]

**Supporting Legs:**

| Leg | Summary | Evidence |
|-----|---------|----------|
| 1. [Reason 1] | [One sentence] | [X sources, Section Y] |
| 2. [Reason 2] | [One sentence] | [X sources, Section Y] |
| 3. [Reason 3] | [One sentence] | [X sources, Section Y] |

**Leg Test:** Removing any leg weakens the conclusion.

**Confidence:** [HIGH/MEDIUM/LOW] based on [X] independent sources.

---

## Supporting Analysis

### Leg 1: [Reason 1]
[Detailed evidence and analysis]

### Leg 2: [Reason 2]
[Detailed evidence and analysis]

### Leg 3: [Reason 3]
[Detailed evidence and analysis]
```

**Anti-Patterns:**
- Starting with background/context instead of conclusion
- Burying the recommendation at the end
- Listing findings without synthesizing into legs
- Having legs that don't actually support the conclusion

---

### 8. Honest Uncertainty (HU)

> **"No evidence found" is valuable information.**

| Requirement | Description |
|-------------|-------------|
| **HU-01** | Explicitly state what couldn't be determined |
| **HU-02** | Distinguish "validated false" from "not enough evidence" |
| **HU-03** | Document searches attempted that yielded nothing |
| **HU-04** | Note gaps in available information |

**Uncertainty Disclosure Template:**
```markdown
## What We Couldn't Determine

| Question | Searches Attempted | Result |
|----------|-------------------|--------|
| {Question 1} | {Search queries} | No relevant results |
| {Question 2} | {Search queries} | Insufficient evidence |

**Research Limitations:**
- {Limitation 1}
- {Limitation 2}
```

---

### 9. Encouragement with Honesty (EH)

> **Weak evidence shouldn't discourage - it should guide exploration.**

| Situation | Response |
|-----------|----------|
| Weak evidence, interesting idea | "This needs more research. Here's how to explore..." |
| Poorly articulated idea | Ask clarifying questions before judging |
| Counter-evidence exists | Present both sides, let user decide |
| No evidence either way | "This is uncharted territory. Consider small experiments..." |

**Key Distinction:**
- "Bad idea" = Evidence actively contradicts the hypothesis
- "Unvalidated idea" = Insufficient evidence to judge
- "Needs exploration" = Promising but requires more research

**NEVER say:**
- "This won't work" (unless evidence proves it)
- "Nobody wants this" (unless searched and found counter-evidence)
- "This is a bad idea" (without explaining WHY based on evidence)

**INSTEAD say:**
- "Evidence is insufficient to validate this. To strengthen the case, search for..."
- "I found counter-evidence that suggests [X]. However, you may want to explore [Y]..."
- "This is an uncharted area. Consider running a small experiment to validate..."

---

### 10. Decision Framing (DF)

> **Every analytical output must tell a story to the decision maker, not center on technicals.**
>
> _"Don't center on the technicals. That's not what a decision maker cares about.
> Tell a story about a commander!"_

| Requirement | Description |
|-------------|-------------|
| **DF-01** | Frame findings using SCQA (Situation, Complication, Question, Answer) |
| **DF-02** | Explicitly state what decision this informs |
| **DF-03** | If findings CHANGE the original question, flag this prominently |
| **DF-04** | Include escalation recommendation when findings reveal issues beyond scope |

**The SCQA Framework:**

Analysis must be framed as a story for the decision maker:

| Element | Purpose | Example |
|---------|---------|---------|
| **Situation** | Context the decision maker is operating in | "We're deciding whether to ship the new check-security skill to founders" |
| **Complication** | What problem or change emerged | "We discovered tier 2 covers ~5 of 12 SEC+DAT primitives; founders may misread 'green' as full coverage" |
| **Question** | What needs to be decided (may differ from original) | "Should we deepen check-security before shipping, or ship with explicit scope caveat?" |
| **Answer** | What they should do | "Deepen first — the trust cost of misleading 'green' outweighs the delay" |

**SCQA Template:**
```markdown
## Decision Summary

**Situation:** {Context the decision maker is operating in}

**Complication:** {What problem or change emerged from this work}

**Question:** {What needs to be decided - may differ from original question if complications warrant}

**Answer:** {What the decision maker should do}

### Supporting Evidence
{Technical details organized by Pyramid Principle - conclusion first, then supporting legs}
```

**Why SCQA Matters:**

| Anti-Pattern | Problem | SCQA Solution |
|--------------|---------|---------------|
| Leading with technicals | Decision maker loses interest, misses the point | Lead with the story |
| Answering narrow question | Misses bigger issues discovered during work | Complication can change the Question |
| Burying recommendations | Decision maker must hunt for what to do | Answer is explicit and prominent |
| No escalation path | Foundational issues go unaddressed | Complication triggers appropriate response |

**Escalation Triggers:**

When analysis reveals issues BIGGER than the original question:

| Discovery | Escalation Recommendation |
|-----------|--------------------------|
| Methodology inconsistency | Recommend methodology change (re-run add-skill) before original decision |
| Architecture conflict | Recommend resolution before continuing |
| Missing foundational decision | Flag that original question can't be answered yet |
| Scope too narrow | Recommend broadening work before deciding |

**DF Anti-Patterns:**

| Anti-Pattern | Why It's Wrong | Correct Approach |
|--------------|----------------|------------------|
| Centering on technicals | Decision makers don't care about file paths | Frame as decision story |
| Answering narrow question when bigger issue found | Misses the real problem | Change the Question in SCQA |
| Hiding complications in details | Decision maker misses critical context | Complication is prominent |
| No clear answer | Decision maker left uncertain | Answer is explicit action |

---

## Anti-Patterns

| ID | Anti-Pattern | Description | Correct Approach |
|----|--------------|-------------|------------------|
| AP-01 | Cherry-picking | Selecting only supportive evidence | Include counter-evidence section |
| AP-02 | Echo validation | Finding sources that cite each other | Require independent sources |
| AP-03 | Optimistic interpretation | Treating ambiguous as positive | Flag ambiguity explicitly |
| AP-04 | Premature rejection | Dismissing idea without exploration | Suggest exploration path |
| AP-05 | Confirmation search | Only searching for what you want | Neutral + counter queries |
| AP-06 | Recency bias | Ignoring that problems may be solved | Check for recent solutions |
| AP-07 | Volume conflation | Treating engagement as validation | Distinguish entertainment from pain |
| AP-08 | Authority assumption | Trusting sources without verification | Verify claims independently |
| AP-09 | Over-decomposition | Decomposing beyond the level where further splitting changes decisions | Apply PG-04 termination condition: stop when splitting doesn't change the decision at the stated level of analysis |

---

### 11. Primitive Grounding (PG)

> **Every analysis must be grounded in irreducible, independently-testable units (primitives) at the stated level of analysis.**
>
> Primitives are the atoms of analysis. MECE validates that categories don't overlap and cover the space.
> Primitive Grounding validates that those categories are *real* (irreducible) rather than arbitrary groupings.
> Falsification validates that hypotheses can be disproven. Primitive Grounding ensures falsification targets
> specific testable units rather than vague abstractions.

| Requirement | Description |
|-------------|-------------|
| **PG-01** | Every analysis must identify the primitives at the stated level of analysis. A primitive is irreducible at that level: it cannot be decomposed further without changing the decision it informs. |
| **PG-02** | Independence test: a candidate primitive must be independently changeable, independently validatable, and independently falsifiable. If changing A requires changing B to preserve correctness, they are one primitive or share a hidden dependency. |
| **PG-03** | Level-of-analysis anchor: every primitive decomposition must declare its decision context. Primitives are relative to the decision being made, not absolute. The same element may be primitive at one level and composite at another. |
| **PG-04** | Termination condition: decomposition stops when further splitting would not change any decision at the stated level of analysis. Over-decomposition is as harmful as under-decomposition. |

**Primitive Grounding Template:**
```markdown
## Primitive Grounding

### Level of Analysis
**Decision context:** {What decision does this analysis inform?}
**Level:** {e.g., skill-scope, primitive-coverage, tier-composition}

### Primitives Identified
| Primitive | Definition | Independence Test | Irreducibility Test |
|-----------|-----------|-------------------|---------------------|
| {Name} | {What it is at this level} | Can change independently of other primitives? YES/NO | Further splitting changes the decision? NO = primitive |

### Termination Check
| Candidate Split | Would It Change the Decision? | Action |
|-----------------|------------------------------|--------|
| {Split A into A1, A2} | NO — same decision either way | STOP: A is primitive at this level |
| {Split B into B1, B2} | YES — different decision for B1 vs B2 | SPLIT: B is composite |
```

**Worked Example — When to STOP (sulis-local):**
```
Decision: "What primitives should check-security cover?"
Level: skill primitive scope

Primitives identified:
- SEC-01 access control (can change independently of SEC-03) ✓
- SEC-03 injection (can change independently of SEC-05) ✓
- SEC-07 secrets in git history (can change independently of HEAD-only scan) ✓

Candidate split: SEC-03 injection → SQL injection, NoSQL injection, command injection
Question: Does splitting change the primitive-coverage decision?
Answer: NO — we decide to cover "SEC-03 injection" using a Semgrep injection rule pack;
        whether the pack catches SQL vs NoSQL vs command is a tool detail, not a scope decision.
Action: STOP. SEC-03 is primitive at the skill-scope level.

Note: If the decision were "which Semgrep rules to enable," SEC-03 IS composite and the
individual rule families are the primitives. The level of analysis determines what is primitive.
```

**Red Flags:**
- Categories that pass MECE but could be reorganised arbitrarily → missing primitive grounding
- Falsification criteria targeting abstractions ("the skill will catch security issues") → not primitive-specific
- No declared level of analysis → primitives are unanchored
- Decomposition continuing past the point where it changes decisions → over-decomposition (AP-09)
- Two "primitives" that must always change together → hidden dependency, actually one primitive

---

### 12. Outside-In Reasoning (OI)

> **Reasoning begins from external needs, user jobs-to-be-done, and the problem space.
> Internal sulis structure informs HOW to serve those needs, not WHAT needs to serve.**
>
> Outside-in reasoning prevents the sulis methodology's own structure from biasing analysis.
> When identifying skill scope, primitive coverage, or tier composition, start from the user's
> actual problem — not from existing skill directories, the 7-tier registry, or internal taxonomy.

| Requirement | Description |
|-------------|-------------|
| **OI-01** | When identifying what a skill needs (scope, primitives, tools), start from external context: user's actual problem, evidence from prior incidents, the failure modes the skill must catch. Consult internal sulis structure only after external context is established. |
| **OI-02** | When the reasoning direction matters (skill scope decisions, tier composition reviews), explicitly state whether the analysis is outside-in (from user problem) or inside-out (from existing structure). If inside-out is used, justify why. |
| **OI-03** | External validation: compare internally-derived conclusions against at least one external framework or benchmark (e.g., codebase-assess primitive catalogue, OWASP, SLSA). Document the comparison. |

**Verification criteria:** An analysis violates OI when the first step consults internal
sulis structure (existing tiers, registered skills, established patterns) before establishing
external context. The violation is observable: check whether the analysis references internal
sulis artifacts before external frameworks or user-problem context.

**Scoping statement:** OI is a thinking standard (flag-level), not a constitutional
constraint (halt-level). Violation produces a flag for review, not a blocked execution.
OI applies most strongly to skill scope decisions, primitive-coverage decisions, and
tier-composition reviews — where inside-out bias has demonstrated harm. For
implementation tasks where internal structure is the primary subject matter, OI-01 does
not apply but OI-02 (direction declaration) still applies.

**Red Flags:**
- Analysis begins by listing existing tier-registry entries or check-* skill scopes
- Primitives identified that mirror internal structure rather than user problems
- No external framework consulted before conclusions drawn
- "What does sulis have?" asked before "What does this user need?"

---

### 13. Adversarial Testing Posture (AT)

> **The default posture for validation is adversarial: seek to disprove before seeking to confirm.**
>
> Confirmation-seeking validation produces the same result as no validation — the author
> believes what they believed before. Adversarial validation produces invalidations when
> the assumption fails, which is the useful output. This principle is structural, not
> dispositional: it is encoded through process design, not by asking agents to "be skeptical."

| Requirement | Description |
|-------------|-------------|
| **AT-01** | The default posture for any validation activity is adversarial. Seek evidence that would disprove the hypothesis before seeking evidence that would confirm it. |
| **AT-02** | Riskiest assumptions are tested first. Assumptions are ordered by impact (what damage if wrong) then by evidence level (least evidence first). Low-risk or well-evidenced assumptions are tested later. |
| **AT-03** | Confirmation-seeking must be documented as a deliberate deviation with justification. If validation starts from "how do we confirm this?", the choice must be stated explicitly with rationale for why adversarial posture was inappropriate. |

**Adversarial Posture Template:**
```markdown
## Adversarial Validation

**Hypothesis:** {What we believe}

**Invalidation Signals (test these first):**
1. {Evidence that would disprove the hypothesis}
2. {Evidence that would disprove the hypothesis}

**Attack Patterns:**
- {How a hostile evaluator would challenge this}
- {What the strongest counter-argument is}

**Confirmation Evidence (seek second):**
- {Evidence that would support the hypothesis}
```

**Why This Matters:**

| Framework | Adversarial Principle |
|-----------|----------------------|
| Lean Startup | Riskiest Assumption Test — attack riskiest first |
| Mom Test | Adversarial interview design to counter social confirmation bias |
| Strategyzer Test Card | "What do we want to disprove?" not "What do we want to confirm?" |
| Continuous Discovery | "Trying to find evidence that would cause you to abandon the opportunity" |

**Red Flags:**
- Validation plan starts with "How do we confirm...?" without adversarial framing
- All tests designed to produce positive results (confirmation search, AP-05)
- Invalidation signals are vague or unmeasurable ("users don't like it")
- Riskiest assumptions tested last or not at all

**Source:** Maurya (2012) *Running Lean*; Strategyzer (2020) *Test Card* and *Assumptions Mapping*; Torres (2021) *Continuous Discovery Habits*.

---

## Application to Skills

### Authoring Skills (`add-skill`)

The methodology skill itself must hold to the standard it codifies. The five gates map to principles:

| Gate | Required Principles |
|------|---------------------|
| 1 Find | BI-01..04 (counter-search for prior art), SI-01..04 (independent BRIEF_PACK sources), CC (confidence on "no existing skill" judgment) |
| 1 Find — Primitive Discovery | PG-01..04 (level of analysis + irreducibility + independence + termination); see `DECOMPOSITION_PROCEDURE.md` for the operational complement |
| 2 Scope Lock | OI-01..03 (outside-in: start from user problem, not existing skill catalogue) |
| 3 Generate | MECE (When-to/When-not-to are mutually exclusive + collectively exhaustive), Pyramid (conclusion first), NH (linguistic audit) |
| 4 Evaluate | HU (deferred perspectives surfaced honestly), CC (per-perspective confidence) |
| 5 Adversarial | AT-01..03 (default adversarial; riskiest assumptions first), FR (each gotcha has falsification: prior-failure source) |

### Assessment Skills (`check-security`, `check-build`, `check-tests`, `check-reliability`, `check-readability`, `check-maintainability`, `check-polish`)

Audit-pattern skills produce findings + hypotheses that drive founder decisions. They must hold to the same evidence standards as research skills.

**Required Sections in Output:**

1. **Findings:** every finding cites file:line + tool evidence (BI-02, CC)
2. **Counter-evidence consideration:** for advisory findings, note when the pattern may be intentional (BI-01)
3. **Hypotheses:** what we couldn't fully determine, with confidence + verification question (HU-01..04, EH)
4. **Limitations:** what couldn't be checked (tools unavailable, language not supported) (HU-03)

**Required Elements per Primitive:**

1. **Falsification:** what would invalidate this primitive's pass/fail verdict (FR-01)
2. **Provenance:** extracted from codebase patterns / inferred from external framework / user-stated (PG-03)
3. **Pre-mortem on false-positive risk:** if this finding is wrong, why? (FR-03)

### Aggregator Skills (`code-health`, `inbox`)

Aggregator-pattern skills synthesise across many sources. They must hold MECE on what they cover + Pyramid on what they say.

**Required Checks:**

1. **MECE coverage:** declared sources are mutually exclusive (no double-count) and collectively exhaustive (declared scope)
2. **SCQA framing:** founder-mode output leads with Situation/Complication/Question/Answer (DF-01..04)
3. **Pyramid structure:** conclusion (overall verdict) first; supporting legs (per-source rollups); details (raw findings) last (PP-01..04)
4. **Honest uncertainty:** when a source is unavailable or stale, surface it as a finding not hide it (HU-01..04)

---

## Quality Checklist

Before finalizing any analytical, audit, or assessment output:

- [ ] **BI:** Did I search for counter-evidence?
- [ ] **SI:** Are my sources truly independent?
- [ ] **FR:** Have I stated what would change my conclusion?
- [ ] **CC:** Does my confidence match my evidence quality?
- [ ] **MECE:** Are my categories mutually exclusive and collectively exhaustive?
- [ ] **MECE:** Does every finding pass the "So What?" test?
- [ ] **NH:** Have I avoided unsupported superlatives (linguistic audit)?
- [ ] **PP:** Does output lead with conclusion, supported by legs?
- [ ] **HU:** Have I disclosed what I couldn't determine?
- [ ] **EH:** If evidence is weak, have I provided an exploration path?
- [ ] **DF:** Is output framed as SCQA story for the decision maker?
- [ ] **DF:** If complications change the question, is this flagged prominently?
- [ ] **DF:** If escalation needed, is the recommendation explicit?
- [ ] **PG:** Have I identified primitives at the stated level of analysis?
- [ ] **PG:** Do my primitives pass the independence test (changeable, validatable, falsifiable independently)?
- [ ] **PG:** Have I declared the decision context (level-of-analysis anchor)?
- [ ] **PG:** Have I stopped decomposing where further splitting doesn't change the decision?
- [ ] **OI:** Did I start from external context before consulting internal sulis structure?
- [ ] **OI:** Have I declared the reasoning direction (outside-in or inside-out) where it matters?
- [ ] **OI:** Have I compared internally-derived conclusions against an external framework?
- [ ] **AT:** Did I seek to disprove before seeking to confirm?
- [ ] **AT:** Are riskiest assumptions tested first (by impact, then by evidence level)?
- [ ] **AT:** If confirmation-seeking was used, is the deviation documented with justification?

---

## Reference

This standard is cited by:

- `plugins/sulis/skills/add-skill/SKILL.md` (Gates 1, 2, 3, 4, 5 each cite specific principles)
- `plugins/sulis/skills/check-security/SKILL.md` (Assessment Skills section)
- `plugins/sulis/skills/check-build/SKILL.md`
- `plugins/sulis/skills/check-tests/SKILL.md`
- `plugins/sulis/skills/check-reliability/SKILL.md`
- `plugins/sulis/skills/check-readability/SKILL.md`
- `plugins/sulis/skills/check-maintainability/SKILL.md`
- `plugins/sulis/skills/check-polish/SKILL.md`
- `plugins/sulis/skills/code-health/SKILL.md` (Aggregator Skills section)
- `plugins/sulis/skills/inbox/SKILL.md` (Aggregator Skills section)

Companion standards:

- `DECOMPOSITION_PROCEDURE.md` — operational procedure for decomposition (complements PG-01..04)
- `SPIRAL_TEMPLATES.md` — the rubric this standard is scored under (ACCA + Evidence Grounding + Structural Coherence dimensions cite this document)
- `STANDARDS_RUBRIC.md` — phase classification (this standard is `processing` phase, secondary `output`)
- `REFERENTIAL_INTEGRITY_STANDARD.md` — cross-skill relationship declaration

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-24 | Initial sulis-local port. Adapted from platform v1.5.0 (2026-03-06). Application-to-skills and Reference sections rewritten for sulis context. NH-02 extended with "comprehensive", "robust", "powerful" — observed sulis drift patterns. SCQA + PG worked examples replaced with sulis-relevant scenarios. |
