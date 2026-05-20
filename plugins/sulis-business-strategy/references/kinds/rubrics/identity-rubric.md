# Identity Rubric (v1alpha1)

> **Used by:** `Identity.yaml` evaluate stage.
> **Replaces:** the legacy identity-articulation Authenticity Gate + Sign-Off Gate criteria.
> **Output:** a structured Verdict at `find-output/IDENTITY_VERDICT.md`.

The rubric encodes what the legacy three-lens triad (Belief Crystallizer / Authenticity Validator / Expression Architect) collectively checked. Each section maps to one or more lens concerns. The evaluate stage runs each criterion against the generated `product/organization/IDENTITY.md` and the inputs in `find-output/IDENTITY_BRIEF_PACK.md`.

---

## Verdict shape

The evaluate stage emits a Verdict at `verdict_path` with this structure:

```yaml
verdict_schema_version: v1alpha1
decision: pass | retry | stop
reason_class: content_deficient | context_deficient | technical_transient | technical_fatal | none
blocking: [list of blocking_criteria triggered, if any]
specific_feedback:
  - criterion: <criterion-id>
    pass: true | false
    evidence: <quote or signal from BRIEF_PACK or IDENTITY.md>
    note: <one-line rationale>
five_whys: <only if reason_class is content_deficient or context_deficient — root-cause chain>
```

`decide` consumes this Verdict and routes per `spec.decide.reason_class_routing`.

---

## Section 1 — Authenticity (Belief Crystallizer + Authenticity Validator)

### A1. WHY is grounded in evidence

The Tension, Belief, and Cause are each supported by at least one quote, signal, or specific data point from BRIEF_PACK. No "we believe X" without evidence of why.

- **Pass:** Every WHY claim has an evidence anchor.
- **Fail:** Any claim is unsupported by BRIEF_PACK content.

### A2. Competitor substitution test (BLOCKING)

Substitute the WHY/HOW/WHAT statements with the name of a named competitor (from BRIEF_PACK competitor_signals). If the statement still fits the competitor, the identity is generic.

- **Pass:** No competitor name fits the WHY or core HOW.
- **Fail (BLOCKING):** Statement is generic; any competitor could claim it.

### A3. MECE check on WHY/HOW/WHAT

The three blocks must be mutually exclusive (no overlap) and collectively exhaustive (cover the identity completely).

- **Pass:** Each block answers a distinct question and together they cover the WHY, the HOW, and the WHAT without gap or duplication.
- **Fail:** Blocks overlap (e.g., a "principle" is restated as a "value proposition") or a gap remains (e.g., HOW is missing).

### A4. Anti-goal coherence (BLOCKING)

Identity does not contradict published anti-goals (`product/offerings/primary/ANTI_GOALS.md`).

- **Pass:** No identity claim contradicts an anti-goal.
- **Fail (BLOCKING):** Identity asserts something the anti-goals explicitly reject.

### A5. Honesty about staging

Where the organisation is still building toward a state, the identity uses staging language ("we have encoded X" / "we are building Y" / "we will build Z") rather than claiming completion.

- **Pass:** Aspirational claims are explicitly framed as aspirational.
- **Fail:** Identity claims capabilities or states that don't yet exist as if they're present.

---

## Section 2 — Falsifiability (Belief Crystallizer)

### F1. Principles include trade-offs

Each HOW principle includes a "this rules out…" or "trade-off:" clause that names what the principle excludes.

- **Pass:** Every principle has a falsifiability clause.
- **Fail:** Any principle is so abstract that nothing is ruled out by adopting it.

### F2. Specific over general

The WHY tension is specific to this organisation's market and moment, not a generic industry observation.

- **Pass:** Tension cites specific dynamics, data, or constraints particular to this organisation.
- **Fail:** Tension reads like a generic statement that could open a McKinsey deck on any industry.

---

## Section 3 — Distinctiveness (Authenticity Validator + Expression Architect)

### D1. Distinctive position vs. competitors

Identity makes a positioning claim that named competitors do not make (verified against competitor_signals in BRIEF_PACK).

- **Pass:** A specific positioning element is unique to this identity.
- **Fail:** Position is indistinguishable from competitors covered in BRIEF_PACK.

### D2. Distinctive voice in tone

If TONE_OF_VOICE.md exists or is generated alongside, the voice attributes are distinctive (not "we're friendly and professional" — which all brands say).

- **Pass:** Voice attributes are specific and contrasted with what the brand is NOT.
- **Fail:** Voice attributes are generic ("authentic," "approachable," "human").

---

## Section 4 — Voice and language (Expression Architect)

### V1. Tone compliance — Pragmatic Authority (T-01)

Identity speaks as an operator with results, not a theorist with ideas. No "we passionately believe", no "we're on a mission to revolutionise."

- **Pass:** Voice is clinical and grounded throughout.
- **Fail:** Any sentence reads as performative excitement or inflated mission language.

### V2. Tone compliance — Radical Clarity (T-02)

No forbidden vocabulary: passion, magic, empower, leverage, seamless, revolutionary, game-changing, cutting-edge, best-in-class, amazing, incredible.

- **Pass:** No forbidden words in any body text.
- **Fail:** Any forbidden word appears.

### V3. Zero hyperbole

No superlatives without quantification. "Fastest" requires a benchmark. "Most secure" requires evidence.

- **Pass:** Every superlative either has a benchmark or is removed.
- **Fail:** Unbacked superlatives appear in body text.

---

## Section 5 — Evidence quality (cross-cutting)

### E1. Evidence-to-claim ratio ≥ 4/5

For every five identity claims, at least four are directly grounded in a BRIEF_PACK quote or signal.

- **Pass:** Ratio ≥ 4/5 across the document.
- **Fail (BLOCKING if zero evidence):** Ratio below 4/5, OR no founder evidence underlies any claim.

### E2. Market reality grounding ≥ 4/5

For every five strategic positioning statements, at least four are tested against market context (competitors, customers, regulatory) from BRIEF_PACK.

- **Pass:** Ratio ≥ 4/5.
- **Fail:** Identity is inside-out wishful thinking with no external grounding.

---

## Routing rules

The decide stage consumes the Verdict and routes per `spec.decide.reason_class_routing`. Classification logic:

| Failure pattern | `reason_class` | Default route |
|---|---|---|
| Generate produced output that fails rubric criteria; BRIEF_PACK was complete | `content_deficient` | `regenerate` (re-run generate with refined constraints derived from the specific_feedback) |
| Generate's failures trace to missing or thin BRIEF_PACK content | `context_deficient` | `re_find` (re-run find with adjusted `inputs_to_scan` or a broader scan) |
| LLM timeout, rate limit, or other recoverable error | `technical_transient` | `retry` (stage-level retry, no Kind iteration counter increment) |
| Unrecoverable error (e.g., invalid YAML, missing required file) | `technical_fatal` | `stop` |
| Any `blocking_criteria` fires | `none` (blocking overrides) | `stop` regardless of reason class |

**5-whys root-cause requirement:** When `reason_class` is `content_deficient` or `context_deficient`, the Verdict must include a five-step root-cause chain. The chain feeds the next iteration's refined constraints or inputs.

**Iteration cap:** When `decide.max_iterations` is exhausted without a `pass`, route to `stop` with the terminal state `stopped_by_iteration_exhausted`.

---

## Mapping from legacy outcome

The legacy `identity-articulation` outcome (v2.5.0) used two gates and a three-lens triad. The rubric replaces both:

| Legacy element | Rubric criterion |
|---|---|
| Authenticity Gate: WHY/HOW/WHAT alignment | A3 (MECE check) |
| Authenticity Gate: competitor substitution test | A2 (BLOCKING) |
| Authenticity Gate: authenticity checklist (6 criteria) | A1, A5, F1, F2 (combined) |
| Sign-Off Gate: triad consensus | The Verdict structure with `decision` + `specific_feedback` |
| Sign-Off Gate: tone compliance (T-01, T-02) | V1, V2, V3 |
| Verification spiral C-07: STANDARD_TIER_DEFAULT | The decide stage's max_iterations=3 loop |
| Verification spiral: evidence-to-claim ratio | E1 |
| Verification spiral: market reality grounding | E2 |

The triad's *function* — multi-perspective evaluation with consensus — is preserved structurally. The triad's *mechanism* — three parallel agent lanes negotiating sign-off — is replaced by a single evaluate stage that applies all the rubric criteria and emits a structured Verdict.
