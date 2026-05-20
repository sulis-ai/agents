# Business Context Instance Schema (v1alpha1)

> **Used by:** `BusinessContext.yaml` generate stage as `spec.generate.spec_ref`.
> **Mirrors:** the legacy `business-context-intake` outcome's `BUSINESS_CONTEXT_TEMPLATE.md`.
> **Output target:** `product/context/BUSINESS_CONTEXT.md`.

This schema defines the structural shape of a generated `BUSINESS_CONTEXT.md`. The generate stage must produce a Markdown file conforming to this section order and content rules. The evaluate stage's rubric then assesses the resulting document.

---

## Document frontmatter (REQUIRED)

Every BUSINESS_CONTEXT.md begins with YAML frontmatter recording session metadata and provenance hashes:

```yaml
---
session_id: <ISO-8601-date>-<random-suffix>
session_mode: greenfield | baseline | progressive
captured_at: <ISO-8601-datetime>
captured_by: <agent-slug>           # business-strategist
maturity: thin | emerging | stable | mature
provenance:
  inputs:
    - path: product/research/competitive/market-analysis.md
      sha256: <hex>
    - path: transcripts/2026-05-15-founder-call.md
      sha256: <hex>
---
```

Hashes are recomputed at every Kind run; mismatched hashes trigger reconciliation in subsequent runs.

---

## Section order (REQUIRED)

1. **How to Read This Document** (boilerplate explaining V/A/U)
2. **Completeness Dashboard** — coverage table per domain
3. **1. Identity & Team** (5 questions: Q1–Q5)
4. **2. Problem & Market** (4 questions: Q6–Q9)
5. **3. Solution & Product** (4 questions: Q10–Q13)
6. **4. Customers** (3 questions: Q14–Q16)
7. **5. Business Model** (4 questions: Q17–Q20)
8. **6. Competition** (3 questions)
9. **7. Go-to-Market** (4 questions)
10. **8. Technology & Deployment** (4 questions)
11. **9. Risks** (3 questions)
12. **Session Notes** (optional — open observations not tied to a question)
13. **Version** — history table

Total: 34 questions across 9 domains.

---

## Completeness Dashboard format

```markdown
## Completeness Dashboard

| Domain | Coverage | Validated | Assumed | Unknown | Skipped |
|---|---|---|---|---|---|
| 1. Identity & Team | 5/5 | 3 | 2 | 0 | 0 |
| 2. Problem & Market | 4/4 | 2 | 1 | 1 | 0 |
| 3. Solution & Product | 4/4 | 4 | 0 | 0 | 0 |
| 4. Customers | 3/3 | 1 | 1 | 1 | 0 |
| 5. Business Model | 4/4 | 2 | 1 | 1 | 0 |
| 6. Competition | 2/3 | 1 | 1 | 0 | 1 |
| 7. Go-to-Market | 3/4 | 1 | 1 | 1 | 1 |
| 8. Technology & Deployment | 4/4 | 3 | 1 | 0 | 0 |
| 9. Risks | 3/3 | 0 | 2 | 1 | 0 |
| **TOTAL** | **32/34** | **17** | **10** | **5** | **2** |

**Maturity:** stable (94% coverage, 53% Validated of substantive answers)
```

---

## Per-question format (REQUIRED)

Each question is rendered as:

```markdown
### Q{N}. {Question text}

**Status:** Validated | Assumed | Unknown | Skipped

**Answer:** {The substantive answer in plain English.}

**Source:** {For Validated: specific citation. For Assumed: defensible rationale. For Unknown: gap acknowledged. For Skipped: rationale for skipping.}

**Validation path:** {For Assumed answers in load-bearing domains: how this would be validated or invalidated.}
```

**Examples:**

```markdown
### Q1. Why does this organisation exist? What belief or cause drives it?

**Status:** Validated

**Answer:** Sulis exists because "Lovable's great at UIs, not great at backends" — vibe-coding tools have solved frontend generation but produce production-fragile backends. Sulis owns the backend so that founders can ship without re-architecting at scale.

**Source:** Founder transcript 2026-05-20, quoted directly. Reinforced in three separate group conversations referenced in `transcripts/`.
```

```markdown
### Q18. What are your unit economics? (CAC, LTV, payback period, gross margin)

**Status:** Assumed

**Answer:** Target CAC < $500 via product-led growth, LTV > $5,000 (12-month retention × $400/mo target ARPU), gross margin > 75% post infrastructure. Payback < 6 months.

**Source:** Industry benchmarks for B2B PLG SaaS (Bessemer cloud index, OpenView 2025 benchmarks). No closed deals yet to validate.

**Validation path:** Will know within first 10 paying customers — if observed CAC > $1,000 or churn > 5%/month, model invalidated.
```

```markdown
### Q19. What is the tier structure, and how do customers upgrade?

**Status:** Skipped

**Source:** Pre-commercial — pricing has not been designed yet. Will be addressed by the Commercial Kind once founder readiness signals trigger it.
```

---

## Question reference (REQUIRED)

The 34 questions across 9 domains are canonical and live in the studios repo at `methodology/outcomes/utility/business-context-intake/templates/QUESTIONNAIRE_TEMPLATE.md`. The generate stage either:

1. Fetches the questionnaire via `mcp__github__get_file_contents(owner="sulis-ai", repo="studios", path="methodology/outcomes/utility/business-context-intake/templates/QUESTIONNAIRE_TEMPLATE.md", ref={ref})` at runtime, OR
2. (Fallback when studios is unreachable) uses the embedded summary below.

### Embedded summary — 9 domains × 34 questions

**Domain 1: Identity & Team** (5 questions)
- Q1: Why does this organisation exist? What belief or cause drives it?
- Q2: What is the core tension or problem in the world you are responding to?
- Q3: What are the non-negotiable principles that guide every decision?
- Q4: What is the brand identity? (Name, positioning, personality, visual direction)
- Q5: Who is building this, and why are they the right person/team?

**Domain 2: Problem & Market** (4 questions)
- Q6: What specific problem are you solving, and for whom?
- Q7: How do you know this problem is real and urgent? What evidence exists?
- Q8: How large is the addressable market, and is it growing?
- Q9: Who specifically will you NOT serve? What are your anti-goals?

**Domain 3: Solution & Product** (4 questions)
- Q10: What does your product do? (50 characters or less)
- Q11: What is your unique value proposition — why will customers choose you over alternatives?
- Q12: What is the current development stage? (Idea / MVP / Beta / Live / Paying users)
- Q13: What are the strategic bets for the current period, and what would falsify them?

**Domain 4: Customers** (3 questions)
- Q14: Who are your customer segments, and what are their jobs-to-be-done?
- Q15: What user journeys have been defined, and what evidence supports them?
- Q16: What traction do you have? (Users, revenue, growth rate, retention)

**Domain 5: Business Model** (4 questions)
- Q17: How do you make money? What is the pricing model?
- Q18: What are your unit economics? (CAC, LTV, payback period, gross margin)
- Q19: What is the tier structure, and how do customers upgrade?
- Q20: What are the key partnerships and their dependency risk?

**Domain 6: Competition** (3 questions)
- Q21: Who are your top 3 competitors, and what do they do well?
- Q22: What is your defensible advantage — what makes you hard to copy?
- Q23: What category are you in, and how is it evolving?

**Domain 7: Go-to-Market** (4 questions)
- Q24: What are your primary acquisition channels?
- Q25: What is your sales motion? (Self-serve / inside sales / enterprise / hybrid)
- Q26: What is your activation and onboarding strategy?
- Q27: What is your retention and expansion strategy?

**Domain 8: Technology & Deployment** (4 questions)
- Q28: What is your core technology stack and architecture pattern?
- Q29: How do you ensure security, compliance, and data protection?
- Q30: What is your deployment model? (SaaS / self-hosted / hybrid / on-prem)
- Q31: What are your observability, reliability, and scalability commitments?

**Domain 9: Risks** (3 questions)
- Q32: What are the top 3 risks to this venture, and how are you mitigating them?
- Q33: What would cause you to pivot or abandon this venture?
- Q34: What is your runway and burn rate trajectory?

**Note:** Question numbers Q21–Q34 are inferred from the legacy outcome's question structure. The canonical questionnaire in studios is authoritative.

---

## Section-level rules

- **No methodology codes** in answer bodies (no FE-NN, BC-NN, C-07, schema field names).
- **Markdown headings** at consistent levels (H1 = document title, H2 = domain, H3 = question).
- **No emojis** unless the founder has explicitly invited them.
- **Document length:** typically 1500–4000 words depending on maturity. Below 1500 is likely thin; above 4000 is likely over-detailed (use Session Notes section for context that doesn't fit a question).
- **No strategic prescription** (per rubric B1). The document captures WHAT the founder knows. Identity, positioning, pricing, GTM strategy — those are downstream Kinds.
- **Plain English** throughout (per rubric B2).

---

## Relationship to downstream Kinds

`BUSINESS_CONTEXT.md` is the canonical input for:

- **`Identity` Kind** — Q1, Q2, Q3, Q4 ground the WHY discovery.
- **`Vision` Kind** (future) — Q3, Q9, Q11 ground the directional bets.
- **`Strategy` Kind** (future) — Q13, Q24–Q27 ground the strategic articulation.
- **`Brand` Kind** (future) — Q4 grounds the brand positioning.
- **`Commercial` Kind** (future) — Q17, Q18, Q19, Q20 ground the commercial model.
- **`GTM` Kind** (future) — Q24, Q25, Q26 ground the go-to-market plan.

Each downstream Kind's find stage reads BUSINESS_CONTEXT.md first. Each downstream Kind's evaluate stage checks consistency between the produced artifact and BUSINESS_CONTEXT.md (rubric D2 equivalent).

---

## What this schema does NOT cover

- **Strategic recommendations** — those belong in downstream Kinds (Identity, Strategy, Commercial, etc.).
- **Pricing tier design** — Commercial Kind's job.
- **Roadmap sequencing** — Roadmap Kind's job.
- **Identity articulation** — Identity Kind's job. Q1–Q4 here capture the founder's belief; Identity transforms it into a published identity statement.

This Kind is the intake. Everything else interprets the intake.
