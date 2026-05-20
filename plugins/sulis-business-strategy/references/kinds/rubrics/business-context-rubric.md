# Business Context Rubric (v1alpha1)

> **Used by:** `BusinessContext.yaml` evaluate stage.
> **Replaces:** the legacy business-context-intake Authenticity + Sign-Off gates and the Business Context Quality Triad consensus.
> **Output:** a structured Verdict at `find-output/CONTEXT_VERDICT.md`.

The rubric encodes what the legacy three-lens triad (Domain Expert / Assumption Challenger / Completeness Monitor) collectively checked. Each section maps to one or more lens concerns.

---

## Verdict shape

```yaml
verdict_schema_version: v1alpha1
decision: pass | retry | stop
reason_class: content_deficient | context_deficient | technical_transient | technical_fatal | none
blocking: [list of blocking_criteria triggered, if any]
completeness_dashboard:
  domains_addressed: <n of 9>
  questions_answered: <n of 34>
  validated_count: <n>
  assumed_count: <n>
  unknown_count: <n>
  skipped_count: <n>
  validated_ratio: <percent>
  maturity_label: thin | emerging | stable | mature
specific_feedback:
  - criterion: <criterion-id>
    pass: true | false
    evidence: <quote or signal>
    note: <one-line rationale>
five_whys: <only if reason_class is content_deficient or context_deficient>
```

---

## Section 1 — Coverage (Completeness Monitor)

### C1. All 9 domains addressed

Each domain has at least one substantive answer (Validated, Assumed, or explicitly Skipped with rationale).

- **Pass:** Domain has ≥ 1 substantive answer or explicit skip-with-rationale.
- **Fail:** Domain is silent — no answers, no skip rationale.

### C2. Question coverage ≥ 24/34 (≈ 70%)

At least 70% of questions have substantive answers (Validated + Assumed + explicit-Skipped). Below 70% the context is too thin to support downstream Kinds.

- **Pass:** ≥ 24 of 34 questions covered.
- **Fail (warning):** 18-23 covered — usable but flagged.
- **Fail (BLOCKING via blocking_criteria `fewer_than_three_domains_addressed`):** < 18 OR fewer than 3 domains have any substantive content.

### C3. Validated ratio ≥ 30%

At least 30% of substantive answers are Validated (concrete evidence). Below 30% the context is mostly speculation.

- **Pass:** Validated ≥ 30% of (Validated + Assumed).
- **Fail (warning):** 15-29% Validated — usable, flagged as `emerging` maturity.
- **Fail (BLOCKING via `no_validated_answers_at_all`):** Zero Validated answers.

### C4. No silent skips

Every question marked Skipped has an explicit rationale ("pre-commercial," "not relevant for B2C model," etc.).

- **Pass:** Every Skipped question has a one-line rationale.
- **Fail:** Skipped without rationale.

---

## Section 2 — Defensibility (Assumption Challenger)

### A1. Every Validated answer has provenance

Validated answers cite their source — transcript reference, research file, founder quote, prior artifact path, or measurable data point.

- **Pass:** Every Validated answer has a `Source:` line with a specific citation.
- **Fail (BLOCKING via `missing_provenance_on_validated`):** Any Validated answer lacks provenance. Validated without source is a logical contradiction — it's not validated, it's assumed.

### A2. Every Assumed answer has a defensible rationale

Assumed answers state WHY the founder believes the assumption is defensible (industry knowledge, analogous market, expert input, observed pattern). Not just "I think so."

- **Pass:** Every Assumed answer has a one-line rationale.
- **Fail:** An Assumed answer reads as wishful thinking without rationale.

### A3. Assumption-validation paths named

For Assumed answers in load-bearing domains (Problem & Market, Customers, Business Model, Competition), the answer names HOW the assumption would be validated or invalidated.

- **Pass:** Assumed answers in load-bearing domains include a validation hypothesis ("we'll know this is right when…" / "we'll know this is wrong if…").
- **Fail (warning):** Assumptions in load-bearing domains without validation paths.

### A4. Inflated Validated detection

An answer is marked Validated only when concrete evidence supports it (a sale, a contract, an interview, a measured metric). An answer that's been "validated by reading articles" is Assumed, not Validated.

- **Pass:** Validated answers cite evidence that meets the bar.
- **Fail:** Inflated Validation found — downgrade to Assumed and re-evaluate completeness.

---

## Section 3 — Domain Coherence (Domain Expert)

### D1. Internal consistency

Answers across domains don't contradict each other. Example: if Q11 (value proposition) names "premium B2B SaaS" and Q14 (customer segments) names "individual prosumers," that's an inconsistency worth flagging.

- **Pass:** No detected contradictions across domains.
- **Fail:** One or more cross-domain contradictions surfaced; specific_feedback names them.

### D2. Coherence with existing artifacts

When existing artifacts were detected in find (IDENTITY.md, VISION.md, STRATEGY.md, ANTI_GOALS.md), BUSINESS_CONTEXT.md answers are consistent with them. Drift is surfaced explicitly.

- **Pass:** No silent drift between BUSINESS_CONTEXT and existing artifacts.
- **Fail:** Detected drift — specific_feedback names the artifact and the divergence.

### D3. Answer specificity

Answers are specific to this organisation, not generic statements that could fit any company in the category.

- **Pass:** Answers cite specific names, numbers, dates, people, contracts, products.
- **Fail:** Answers read as templated platitudes ("we serve customers who need our product").

---

## Section 4 — Boundary Compliance

### B1. No strategic prescription

BUSINESS_CONTEXT.md captures WHAT the founder knows. It does NOT prescribe strategic positioning, recommend pricing, articulate identity, or propose GTM motions. Those are downstream Kinds (Identity, Strategy, Commercial, GTM).

- **Pass:** Output describes; does not prescribe.
- **Fail (BLOCKING via `prescription_drift`):** Output contains positioning recommendations, pricing prescriptions, identity articulations, or commercial model proposals.

### B2. No methodology language in body

No FE-NN, BC-NN, C-07, schema field names, internal taxonomy in the BUSINESS_CONTEXT.md body. The provenance frontmatter may use technical fields (hashes, timestamps); the answer bodies use plain English.

- **Pass:** No internal taxonomy in answer bodies.
- **Fail:** Answer body uses internal codes or jargon.

---

## Section 5 — Provenance Integrity

### P1. SHA-256 hashes present and current

The provenance frontmatter records SHA-256 hashes for every input artifact the answers reference. Hashes are current (recomputed at intake time, not stale).

- **Pass:** Every referenced input artifact has a hash; hashes verify against current file state.
- **Fail:** Hashes missing or stale. Downstream reconciliation will fail.

### P2. Mode declaration matches workspace state

The session_mode declared in BRIEF_PACK matches the workspace state at evaluate time (e.g., if mode was "baseline" but BUSINESS_CONTEXT.md now has valid hashes, mode declaration is stale).

- **Pass:** Mode declaration is current.
- **Fail:** Mode declaration is stale — generate may have been driven on outdated assumptions.

---

## Routing rules

| Failure pattern | `reason_class` | Default route |
|---|---|---|
| Rubric criteria fail; BRIEF_PACK was complete; gaps are in answer quality | `content_deficient` | `regenerate` — re-question the weak domains |
| Rubric criteria fail; BRIEF_PACK missed important existing artifacts | `context_deficient` | `re_find` — broaden the scan, re-detect mode |
| LLM timeout / rate limit / transient error | `technical_transient` | `retry` |
| Unrecoverable error (invalid YAML, missing required file) | `technical_fatal` | `stop` |
| Any blocking_criteria fires | `none` (blocking overrides) | `stop` |

**5-whys requirement:** When `reason_class` is `content_deficient` or `context_deficient`, the Verdict includes a five-step root-cause chain. The chain feeds the next iteration's refined question set or scan list.

**Iteration cap:** When `decide.max_iterations` is exhausted without a `pass`, route to `stop` with terminal state `stopped_by_iteration_exhausted`. Honest stop is better than another forced iteration that drags V/A/U scores down further.

---

## Maturity labels

| Label | Criteria |
|---|---|
| **thin** | < 50% question coverage OR < 15% Validated |
| **emerging** | 50-70% coverage AND 15-30% Validated |
| **stable** | 70-90% coverage AND 30-60% Validated |
| **mature** | ≥ 90% coverage AND ≥ 60% Validated |

The maturity label is surfaced in the completeness_dashboard. Downstream Kinds can declare a minimum required maturity (e.g., Identity might require `emerging` or better; Commercial might require `stable` or better).

---

## Mapping from legacy outcome

| Legacy element | Rubric criterion |
|---|---|
| Domain Expert (lead) — conducted intake conversation | The generate stage's conversational intake style |
| Domain Expert — produced V/A/U scoring | C3 (Validated ratio), A1 (provenance), A4 (inflated detection) |
| Assumption Challenger — checked defensibility | A2 (rationale), A3 (validation paths), A4 (inflated detection) |
| Completeness Monitor — tracked coverage | C1 (domain coverage), C2 (question coverage), C4 (silent skips) |
| Boundary Guard (C-06) — no strategic prescription | B1 (no prescription) |
| Reconciliation Mode (v2.0.0) — SHA-256 provenance | P1 (hashes), P2 (mode currency) |
| V/A/U Completeness Dashboard | The completeness_dashboard field in the Verdict |
