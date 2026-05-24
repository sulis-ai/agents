# Sulis Standards

> **Five cross-cutting standards** ported from the platform (`/Users/iain/Documents/repos/platform/methodology/standards/`) and optimised for sulis scale. They ground reasoning, decomposition, verification, cross-reference integrity, and standards-phase classification across every sulis skill.

This is the entry point. Read this first; then read each standard in the order below.

## Conclusion (Pyramid Principle — lead with the answer)

When you author or upsurge a sulis skill, you cite the five standards at specific gates / phases in your SKILL.md. They provide:

- A measurable rubric (ACCA + 4 other dimensions in STANDARD tier; +1 Independence Check in HEAVY tier) for "is this skill done?"
- A primitive-discovery procedure (PG + PD) for "what should this skill cover?"
- Hard rules on cross-skill reference integrity (RI-01..05) for "does this skill name things that exist?"
- A reasoning discipline (BI / SI / CC / MECE / PG / NH / FR / HU / EH / DF / PP / OI / AT) for "is the analysis sound?"

The standards replace `add-skill`'s previous ad-hoc methodology with rigour proven at platform scale.

## The five standards

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

---

## Adoption order

If you're new to sulis standards, read in this order:

1. **CRITICAL_THINKING_STANDARD** — the epistemological foundation. Everything else assumes you've internalised MECE / Pyramid / SCQA / Primitive Grounding.
2. **DECOMPOSITION_PROCEDURE** — the operational complement to PG. Read after Critical Thinking §11.
3. **SPIRAL_TEMPLATES** — the verification rubric. Once you can think and decompose, this is how you prove the skill is done.
4. **STANDARDS_RUBRIC** — how to declare which standards apply. Practical glue for new skill authors.
5. **REFERENTIAL_INTEGRITY_STANDARD** — cross-skill hygiene. The last layer; matters most as the skill ecosystem grows.

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

All five standards are adapted from `/Users/iain/Documents/repos/platform/methodology/standards/`. Each ported file's header records the platform source version + the sulis-local version. The Version History section in each file lists what was trimmed / adapted.

What's NOT ported (deliberate):

- **EXECUTION_STANDARD.md (full)** — only ACCA is inlined into SPIRAL_TEMPLATES.md. The full constitutional constraints (C-01..C-06) are platform-specific orchestration machinery; sulis doesn't currently need them.
- **OFM-specific standards** (PRODUCTION_LIFECYCLE, TRIAD_DESIGN, OUTCOME_ARCHITECTURE, BRIEFING_STANDARD, STEP_SPECIFICATION, MANIFEST_STANDARD, HANDOFF_CONTRACT, DAG_SCHEMA, RIGOR_PROPAGATION, EXECUTION_BRANCH_CONVENTION) — OFM-only.
- **Function-specific standards** (engineering-principles, accessibility-wcag-aa, content-quality, persuasive-content, brand-growth, cognitive-load, agentic-interface, technology-selection, TONE_STANDARD, FRONTEND_BEST_PRACTICES, COACHING_WITHOUT_CONFLICT, DESIGN_VALIDATION_STANDARD, TECHNOLOGY_REUSE_STANDARD) — port on demand if a sulis skill needs them.

When a sulis skill grows a need that one of these covers, port that standard on the same shape: adapt vocabulary, trim platform-specific machinery, keep principles + templates, place under this directory.

---

## What's next

- **Phase 1** of the upsurge plan: rewrite `plugins/sulis/skills/add-skill/SKILL.md` to v0.7.0 — gates cite these standards directly.
- **Phase 2:** per-skill upsurge loops — each check-* skill re-authored against the new methodology + scored under the spiral rubric.
- **Phase 3:** tier composition review using MECE + PG applied to the tier layout itself.

See `/Users/iain/.claude/plans/eager-crunching-quail.md` for the full plan.
