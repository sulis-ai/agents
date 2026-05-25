# Sulis Standards

> **Eight cross-cutting standards.** Seven ported from the platform (`/Users/iain/Documents/repos/platform/methodology/standards/`) and optimised for sulis scale; the eighth (`WORK_PACKAGE_STANDARD`) authored sulis-local in v0.27.0 to codify the WP primitive between detection / characterisation / execution skills. They ground reasoning, decomposition, verification, cross-reference integrity, standards-phase classification, insight-delivery framing, voice / vocabulary, and the unit of execution work across every sulis skill and agent.

This is the entry point. Read this first; then read each standard in the order below.

## Conclusion (Pyramid Principle — lead with the answer)

When you author or upsurge a sulis skill or agent, you cite the standards at specific gates / phases in your SKILL.md or agent.md. They provide:

- A measurable rubric (ACCA + 4 other dimensions in STANDARD tier; +1 Independence Check in HEAVY tier) for "is this skill done?"
- A primitive-discovery procedure (PG + PD) for "what should this skill cover?"
- Hard rules on cross-skill reference integrity (RI-01..05) for "does this skill name things that exist?"
- A reasoning discipline (BI / SI / CC / MECE / PG / NH / FR / HU / EH / DF / PP / OI / AT) for "is the analysis sound?"
- Insight-delivery framing (7 coaching tenets) for "will this land without triggering defensiveness?" — founder-facing only
- Vocabulary + voice constraints (T-01..T-05 + lexicon) for "is this in operator voice with the right vocabulary?" — founder-facing only

The standards replace `add-skill`'s previous ad-hoc methodology with rigour proven at platform scale.

## The standards by tier

The eight standards split into two tiers — methodology (applies everywhere) + founder-communication (applies to founder-facing surfaces only):

### Methodology tier (all skills, all audiences)

1. CRITICAL_THINKING_STANDARD — how the skill thinks
2. DECOMPOSITION_PROCEDURE — how the skill decomposes
3. SPIRAL_TEMPLATES — how the skill is verified
4. STANDARDS_RUBRIC — which standards apply where
5. REFERENTIAL_INTEGRITY_STANDARD — cross-skill hygiene
6. WORK_PACKAGE_STANDARD — the unit of executable work (sulis-local)

### Founder-communication tier (founder-facing skills + agents only)

7. COACHING_STANDARD — how to deliver insight without triggering defensiveness
8. TONE_STANDARD — vocabulary + voice for founder-facing surfaces

The founder-communication tier composes with the methodology tier — they don't replace each other. A founder-facing skill cites both.

## The methodology standards (in detail)

### 1. CRITICAL_THINKING_STANDARD.md (~700 lines)

**What it governs:** how the skill thinks. 13 principles + 9 anti-patterns + Quality Checklist.

**Primary phase:** `processing` (reasoning constraints inside the skill body)
**Secondary phase:** `output` (SCQA / Pyramid for delivery framing)

**The principles:**

- **BI** (Balanced Investigation), **SI** (Source Independence), **CC** (Confidence Calibration), **NH** (No Hyperbole) — evidence integrity
- **FR** (Falsifiability), **HU** (Honest Uncertainty), **EH** (Encouragement with Honesty) — intellectual honesty under uncertainty
- **MECE**, **PP** (Pyramid Principle), **DF** (Decision Framing / SCQA) — structural discipline
- **PG** (Primitive Grounding), **OI** (Outside-In Reasoning), **AT** (Adversarial Testing Posture) — analytical grounding

Cited by: every analytical / audit / aggregator skill in sulis.

### 2. DECOMPOSITION_PROCEDURE.md (~115 lines)

**What it governs:** the operational procedure for decomposing into primitives. 6 requirements (PD-01..PD-06).

**Primary phase:** `processing` (applied during add-skill Gate 1 primitive discovery + tier composition review)

**The requirements:**

- **PD-01** Directed graph with acyclic disclosure ordering
- **PD-02** Scale constraints (fan-out ≤ 7, depth ≤ 5)
- **PD-03** Independence gate (PG-02 alignment)
- **PD-04** Termination condition (PG-04 alignment)
- **PD-05** Dependency typing (depends-on / enables / conflicts-with)
- **PD-06** Provenance + phase (extracted / inferred / user-stated)

Where CRITICAL_THINKING §11 (PG) governs the *thinking* about primitives, DECOMPOSITION_PROCEDURE governs the *doing*.

Cited by: `add-skill` Gate 1; per-skill upsurge loops; tier composition review.

### 3. SPIRAL_TEMPLATES.md (~250 lines)

**What it governs:** the verification rubric. Three tier templates (LIGHT / STANDARD / HEAVY) + ACCA universal dimension + VERIFICATION_REPORT.md template.

**Primary phase:** `governance` (applies at verification level, not per skill body)

**The tiers:**

- **LIGHT** — ACCA only; mechanical skills
- **STANDARD** (default for most check-*) — ACCA + Evidence Grounding + Structural Coherence + Honest Uncertainty + Codebase Referential Integrity
- **HEAVY** (for methodology + founder-visible verdict skills) — STANDARD + Outcome-Specific Rigor + Independence Check (external sub-agent, fresh context)

**The forcing function:** VERIFICATION_REPORT.md on disk. A single filesystem check determines compliance — `test -f` + `grep "Verdict:.*PASS"`. If the file is absent, the skill is definitionally incomplete.

**The high-leverage dimension:** Codebase Referential Integrity (derived from platform ADR-164) — every tool / file / path the skill claims to use must trace to the codebase with a verified path. NEW entities exempt only if explicitly flagged. Catches the hallucination failure mode ("we use Semgrep" without actually wiring it).

Cited by: every sulis skill in its `verification_spiral:` frontmatter block.

### 4. STANDARDS_RUBRIC.md (~120 lines)

**What it governs:** which standards apply where. Phase classification model (input / processing / output / governance) + typical combinations by skill action type.

**Primary phase:** `input` (used by skill author / add-skill Gate 2 to assemble the SKILL.md `standards:` block)

**How to use it:** identify your skill's action type (perspective_analysis / tension_analysis / synthesis / artifact_write / scope_capture), copy the default combination, adjust for skill domain, record in frontmatter.

Cited by: `add-skill` Gate 2.

### 5. REFERENTIAL_INTEGRITY_STANDARD.md (~110 lines)

**What it governs:** cross-skill reference integrity. Four canonical relationship types + 5 validation rules.

**Primary phase:** `input` (validated before skill invocation; declared in SKILL.md frontmatter)

**The relationship types:**

- `depends_on` — hard prerequisite; ordering constraint
- `optional_input` — soft prerequisite; enhances, not blocks
- `related_to` — conceptual association; no ordering
- `supersedes` — replacement relationship

**The validation rules:**

- **RI-01** Dangling reference (ERROR)
- **RI-02** Circular dependency (ERROR)
- **RI-03** Non-standard vocabulary (ERROR)
- **RI-04** Missing section (WARN)
- **RI-05** Tier-registry drift (WARN)

Enforcement currently manual. Sulis-local validator script (`plugins/sulis/_lib/standards/integrity_validator.py`) deferred to a follow-up commit.

Cited by: every sulis skill in its `related_skills:` frontmatter block.

### 6. WORK_PACKAGE_STANDARD.md (~580 lines) — sulis-local, NEW in v0.27.0 — methodology tier

**What it governs:** the canonical unit of executable work. 11 requirements (WP-01..WP-11) covering identity, scope, lineage, status lifecycle, executor dispatch, composition, and loop-closed verification.

**Primary phase:** `processing` (consumed by characterisation skills; produced by them too)

**The kinds:**

- `backend` — RGB-TDD loop; unit + integration + smoke gates
- `frontend` — visual diff + a11y + perf budget gates (NEW; executor TBD)
- `async` — chaos test + idempotency + DLQ gates (NEW; executor TBD)
- `docs` — link-integrity + a11y (NEW; light executor TBD)
- `infra` — Terraform plan + drift + staging destroy-test (NEW; executor TBD)
- `composite` — orchestrates child WPs of different kinds; merges atomically

**The lineage chain (PROV-O-aligned YAML):**

- `derived_from` — which findings this WP came from
- `generated_by` — which characterisation activity + agent created it
- `addresses_findings` — finding signatures the loop-closed check will verify gone
- `invalidated_by` — set when the loop closes (proof the finding is gone)

Field names borrow W3C PROV-O vocabulary; format stays YAML (no JSON-LD machinery). Migration path to JSON-LD preserved via field-name alignment.

**The status lifecycle:** `todo` → `in_progress` → `done` → `closed` (loop-closed) → optionally `regressed`. Also `blocked`, `sleeping`, `abandoned`.

Cited by: `/sulis:address-findings` (produces WPs), `sulis-execution:executor` (consumes), `/sulis:execute` (founder-facing dispatcher). Per-kind execution mechanics live in companion standards (`WP_BACKEND_STANDARD`, `WP_FRONTEND_STANDARD`, `WP_ASYNC_STANDARD`, etc.) — to be authored alongside each kind's executor.

---

## The founder-communication standards (in detail)

### 7. COACHING_STANDARD.md (~280 lines) — founder-communication tier

**What it governs:** how the Sulis agent (and every founder-facing specialist) delivers insight, feedback, and recommendations. The core rule: frame issues as structural gaps, not personal failures.

**Primary phase:** `output` (applied when constructing founder-facing strings that deliver feedback or recommend action)

**The seven tenets:**

- **Structural over personal** — "There's a gap in..." not "You forgot to..."
- **Diagnostic over prescriptive** — "Let's evaluate whether..." not "You need to..."
- **Questions over statements** — invite reflection, don't impose
- **Modelling over telling** — demonstrate behaviour, don't lecture
- **Hypotheses over conclusions** — "I'm forming a hypothesis that..." not "The problem is..."
- **Sequence for relationship capital** — gentle early, direct only after trust
- **Room to step up** — frame as opportunity, not correction

**The forcing function:** the seven-question Pass/Fail validation checklist + red-flag / green-light phrase tables. Apply before emitting any founder-facing feedback string.

Cited by: every founder-facing skill at Gate 4 (Evaluate); every founder-facing agent's response-generation phase; the Sulis agent in every coach-mode interaction.

### 8. TONE_STANDARD.md (~290 lines) — founder-communication tier

**What it governs:** vocabulary and voice register for every founder-facing surface. Sulis agent responses, specialist agents' founder-mode output, `/sulis:*` command output, skill chrome, error messages, dashboard view.

**Primary phase:** `output` (applied when constructing founder-facing strings)

**The five directives:**

- **T-01 Pragmatic Authority** — operator voice, not theorist
- **T-02 Radical Clarity** — plain English, fewest words, no romantic metaphors
- **T-03 Build + Market Reality** — connect technical to commercial-or-operational outcome
- **T-04 Governance Over Mystification** — AI as governed activity, not magic
- **T-05 Vocabulary Governance** — three-zone framework (ban / preserve / coin-selectively)

**The forcing function:** systemic lexicon (Section A preferred terms) + forbidden vocabulary list (15 banned terms with concrete replacements) + seven-item validation checklist.

**What it does NOT govern:** technical-mode output (when founder runs `/sulis:jargon on` or `--raw`); internal artifacts; operator-facing skills.

Cited by: every founder-facing skill at Gate 4 (Evaluate); every founder-facing agent's response-generation phase; `/sulis:add-agent` Gate 2 register declaration.

---

## Adoption order

If you're new to sulis standards, read in this order:

**Methodology tier first (everyone needs these):**

1. **CRITICAL_THINKING_STANDARD** — the epistemological foundation. Everything else assumes you've internalised MECE / Pyramid / SCQA / Primitive Grounding.
2. **DECOMPOSITION_PROCEDURE** — the operational complement to PG. Read after Critical Thinking §11.
3. **SPIRAL_TEMPLATES** — the verification rubric. Once you can think and decompose, this is how you prove the skill is done.
4. **STANDARDS_RUBRIC** — how to declare which standards apply. Practical glue for new skill authors.
5. **REFERENTIAL_INTEGRITY_STANDARD** — cross-skill hygiene. Matters as the skill ecosystem grows.
6. **WORK_PACKAGE_STANDARD** — the unit of executable work. Read when you start producing or executing WPs (skills that emit findings into the pipeline, characterisation skills, the executor).

**Founder-communication tier (only if authoring founder-facing skills or agents):**

7. **COACHING_STANDARD** — how to deliver insight without triggering defensiveness. Read before authoring any founder-facing skill that surfaces findings, recommendations, or feedback.
8. **TONE_STANDARD** — vocabulary and voice for founder-facing surfaces. Read alongside COACHING — they compose.

Plus `plugins/sulis/references/founder-facing-conventions.md` for sulis-layer apply rules (FE-06 application, echo-before-act, prompt-before-destroy, dual-register pattern).

---

## How a skill cites the standards

In SKILL.md frontmatter:

```yaml
---
name: check-security
description: Use when the founder asks "is this safe to ship?" — runs a deep multi-tool security + data-protection + supply-chain assessment.
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
  output: [CRITICAL_THINKING_STANDARD]  # secondary for SCQA in founder mode
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  custom_dimensions:
    - name: "Attack Chain Coverage"
      threshold: ">= 4/5"
      standard_reference: "sulis-local primitive catalogue §SEC chain patterns"
      scorer: generating_agent
related_skills:
  - relationship: depends_on
    skill: code-health
    notes: invoked as wired tier 2 in code-health orchestrator
  - relationship: depends_on
    skill: _lib/tools/semgrep
    notes: tool wrapper for SEC-03 / SEC-04 / SEC-05 / SEC-06 / DAT-03 / INF-04
---
```

---

## Provenance and divergence from platform

Seven of the eight standards are adapted from `/Users/iain/Documents/repos/platform/methodology/standards/`. Each ported file's header records the platform source version + the sulis-local version. The Version History section in each file lists what was trimmed / adapted.

`WORK_PACKAGE_STANDARD.md` (the eighth) is **sulis-local with no platform precedent.** It codifies the WP primitive that `sulis-execution` uses informally, plus the per-kind execution shapes the methodology needs going forward (frontend, async, etc.). Authored in v0.27.0 alongside the deep-mode code-health architecture so the find → plan → execute → verify loop has a canonical unit.

Recently added (v0.31.0):

- **COACHING_STANDARD** — ported from platform `COACHING_WITHOUT_CONFLICT.md` (2026-01-30) ahead of the `add-agent` skill. The seven tenets are universal coaching mechanics — they port verbatim. The "Application in Sulis" section maps each tenet onto Sulis agent behaviour at each journey stage.
- **TONE_STANDARD** — ported from platform `TONE_STANDARD.md` v2.0.0 (2026-03-05) ahead of the `add-agent` skill. Five directives + systemic lexicon + forbidden vocabulary port verbatim; applicability rewritten from "OFM artifacts" to "founder-facing sulis surfaces"; three sulis-specific Category C terms added ("change", "patch set", "Sulis").

What's NOT ported (deliberate):

- **EXECUTION_STANDARD.md (full)** — only ACCA is inlined into SPIRAL_TEMPLATES.md. The full constitutional constraints (C-01..C-06) are platform-specific orchestration machinery; sulis doesn't currently need them.
- **OFM-specific standards** (PRODUCTION_LIFECYCLE, TRIAD_DESIGN, OUTCOME_ARCHITECTURE, BRIEFING_STANDARD, STEP_SPECIFICATION, MANIFEST_STANDARD, HANDOFF_CONTRACT, DAG_SCHEMA, RIGOR_PROPAGATION, EXECUTION_BRANCH_CONVENTION) — OFM-only.
- **Function-specific standards** (engineering-principles, accessibility-wcag-aa, content-quality, persuasive-content, brand-growth, cognitive-load, agentic-interface, technology-selection, FRONTEND_BEST_PRACTICES, DESIGN_VALIDATION_STANDARD, TECHNOLOGY_REUSE_STANDARD) — port on demand if a sulis skill needs them.

When a sulis skill grows a need that one of these covers, port that standard on the same shape: adapt vocabulary, trim platform-specific machinery, keep principles + templates, place under this directory.

---

## What's next

- **Phase 1** of the upsurge plan: rewrite `plugins/sulis/skills/add-skill/SKILL.md` to v0.7.0 — gates cite these standards directly.
- **Phase 2:** per-skill upsurge loops — each check-* skill re-authored against the new methodology + scored under the spiral rubric.
- **Phase 3:** tier composition review using MECE + PG applied to the tier layout itself.

See `/Users/iain/.claude/plans/eager-crunching-quail.md` for the full plan.
