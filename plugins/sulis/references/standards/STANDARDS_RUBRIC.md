# Standards Rubric

> **Adapted from platform v1.0.0 (2026-03-18). Sulis-local v1.0.0 (2026-05-24).**
> Significant trim: 26-standard inventory reduced to 5 sulis-local standards;
> Governance Standards section reduced to applicable scope; Ambiguity Log reset.
> Vocabulary: "outcome" → "skill"; GRAPH.yaml node `context` block → SKILL.md frontmatter `standards:` block.

> **Purpose:** Practical companion to the sulis standards catalogue. Maps which standards
> apply in each context slot (input / processing / output / governance) for common skill action types.
> Skill authors select from this rubric when declaring their skill's standards in frontmatter (add-skill Gate 2).
>
> **Living document.** Evolves as new standards are added to sulis.

---

## Phase Classification

Every sulis standard has a primary phase and optionally secondary phases. add-skill Gate 2 uses
the primary phase for placement in the SKILL.md frontmatter `standards:` block. This rubric documents
when secondary phases apply.

### Phase Definitions

| Phase | Where Applied | What It Governs |
|-------|---------------|-----------------|
| **input** | At skill invocation — author / framework assembles context | How context is assembled, what to include, reference validation |
| **processing** | Inside the skill body — reasoning constraints during execution | How the skill thinks, analytical frameworks, decision criteria |
| **output** | Near end of skill execution — delivery shape | How the skill delivers results, tone, structure, framing |
| **governance** | Not per-skill — applies at orchestration / verification level | Verification mechanics, gates, cross-cutting compliance |

---

## Standards Phase Classification

### Sulis Standards Inventory (5 standards)

| Standard | Primary | Secondary | Rationale |
|----------|---------|-----------|-----------|
| CRITICAL_THINKING_STANDARD.md | processing | output | Primary: reasoning constraints (BI / SI / CC / MECE / FR / NH / HU / EH / PG / OI / AT). Secondary: output framing (SCQA, Pyramid). |
| DECOMPOSITION_PROCEDURE.md | processing | — | Operational procedure for primitive decomposition (PD-01..06). Applied during add-skill Gate 1 primitive discovery + tier composition review. |
| SPIRAL_TEMPLATES.md | governance | — | Verification rubric (ACCA + dimensions + Independence Check + VERIFICATION_REPORT.md). Applies at verification level, not per skill body. |
| STANDARDS_RUBRIC.md (this file) | input | — | How skill authors assemble their `standards:` frontmatter block. Governs the standards-selection process at skill-authoring time. |
| REFERENTIAL_INTEGRITY_STANDARD.md | input | — | Cross-skill reference validation (depends_on / optional_input / related_to / supersedes). Validated before skill invocation; declared in SKILL.md frontmatter `related_skills:` block. |

---

## Classification Summary

| Phase | Count (Primary) | Standards |
|-------|----------------|-----------|
| **governance** | 1 | SPIRAL_TEMPLATES |
| **input** | 2 | STANDARDS_RUBRIC, REFERENTIAL_INTEGRITY |
| **processing** | 2 | CRITICAL_THINKING, DECOMPOSITION_PROCEDURE |
| **output** | 0 | _(none yet — sulis has not yet ported a primary-output standard; CRITICAL_THINKING serves as secondary)_ |

**Multi-phase standards (primary + secondary):** 1 of 5 (CRITICAL_THINKING).

Future standards (e.g., a tone standard, a founder-facing-conventions cross-cutting standard if formalised) will populate the output phase.

---

## Typical Combinations by Skill Action Type

These are the default standard selections for each skill action type. Skill authors
start here and adjust per gate if needed.

### perspective_analysis (Analytical Lens)

A skill that takes a lens / framework and applies it to a target (e.g., scoring against a primitive catalogue).

| Slot | Standards | Rationale |
|------|-----------|-----------|
| Input | REFERENTIAL_INTEGRITY_STANDARD | Validate the references the lens needs (e.g., codebase paths exist) |
| Processing | CRITICAL_THINKING_STANDARD | MECE on categories, balanced investigation, falsifiability, PG on grounding |
| Output | _(CRITICAL_THINKING secondary)_ | SCQA framing if output goes to founder |

**Skill-specific additions:**

- Audit skills (check-*): + DECOMPOSITION_PROCEDURE (processing) for per-primitive coverage decomposition
- Authoring skills (add-skill): + DECOMPOSITION_PROCEDURE (processing) for Gate 1 primitive discovery

### tension_analysis (Surfacing Disagreements)

A skill that compares multiple inputs and surfaces tensions (e.g., comparing two skill scopes for MECE overlap).

| Slot | Standards | Rationale |
|------|-----------|-----------|
| Input | REFERENTIAL_INTEGRITY_STANDARD | Validate referenced artifacts exist |
| Processing | CRITICAL_THINKING_STANDARD | Identify genuine tensions vs surface differences (MECE + counter-evidence) |
| Output | _(CRITICAL_THINKING secondary)_ | Pyramid structure for tension report |

### synthesis (Combining Perspectives)

A skill that combines multiple inputs into a single output (e.g., code-health combining all 7 tier results).

| Slot | Standards | Rationale |
|------|-----------|-----------|
| Input | REFERENTIAL_INTEGRITY_STANDARD | Validate cross-source dependencies |
| Processing | CRITICAL_THINKING_STANDARD | SCQA framing, Pyramid Principle, MECE on sources |
| Output | _(CRITICAL_THINKING secondary)_ | Founder-mode output uses SCQA |

### artifact_write (Producing Documents)

A skill that produces a document on disk (e.g., SKILL.md, VERIFICATION_REPORT.md, CHECKUP.md).

| Slot | Standards | Rationale |
|------|-----------|-----------|
| Input | REFERENTIAL_INTEGRITY_STANDARD | Validate references the document will cite |
| Processing | _(domain-specific; usually CRITICAL_THINKING for analytical docs)_ | Depends on what's being written |
| Output | _(CRITICAL_THINKING secondary)_ | Linguistic audit, structure |

### scope_capture (Gathering Context)

A skill that gathers context before action (e.g., add-skill Gate 1 BRIEF_PACK assembly).

| Slot | Standards | Rationale |
|------|-----------|-----------|
| Input | REFERENTIAL_INTEGRITY_STANDARD | Validate inputs exist |
| Processing | CRITICAL_THINKING_STANDARD + DECOMPOSITION_PROCEDURE | Validate completeness of captured scope; if primitive discovery is part of scope-capture, apply PD-01..06 |
| Output | _(none — capture is internal-state, not delivery)_ | |

---

## Governance Standards (Not Per-Skill)

These standards are NOT selected per skill. They apply at the verification / orchestration level:

| Standard | When Applied |
|----------|--------------|
| SPIRAL_TEMPLATES.md | At verification — every skill cites a tier (LIGHT / STANDARD / HEAVY); spiral mechanics apply automatically |

(Future governance standards — e.g., a sulis EXECUTION_STANDARD if sulis grows orchestration needs — would be listed here.)

---

## How to Use This Rubric

1. **Identify the skill action type** of your skill (perspective_analysis, tension_analysis, synthesis, artifact_write, scope_capture)
2. **Copy the default combination** from the table above
3. **Add skill-specific standards** based on the skill's domain (e.g., audit skills add DECOMPOSITION_PROCEDURE)
4. **Adjust if needed** — remove standards that don't apply, add standards for unusual cases
5. **Record in SKILL.md frontmatter** in the `standards:` block:

```yaml
---
name: check-security
description: Use when ...
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
  output: [CRITICAL_THINKING_STANDARD]  # secondary — for SCQA framing in founder mode
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
---
```

---

## Ambiguity Log

Standards where classification required judgment:

| Standard | Decision | Rationale | Confidence |
|----------|----------|-----------|-----------|
| CRITICAL_THINKING_STANDARD | processing (primary), output (secondary) | Core purpose is reasoning. SCQA/Pyramid are output framing but secondary to the analytical disciplines. | High |
| STANDARDS_RUBRIC (this doc) | input | Used by skill author / add-skill Gate 2 to assemble standards; governs context assembly at authoring time. Not used by skill bodies during runtime. | High |

Sulis-local ambiguities encountered during authoring will be added here. Start: empty (apart from the two clear cases inherited from the platform classification logic).

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-24 | Initial sulis-local port. Adapted from platform v1.0.0 (2026-03-18). 26-standard inventory reduced to 5 sulis-local standards. Governance Standards section reduced to applicable scope (SPIRAL_TEMPLATES only). Ambiguity Log reset (2 entries inherited from platform reasoning, rest start empty). How-to-Use example switched from GRAPH.yaml `context` block to SKILL.md frontmatter `standards:` block. Function-specific additions (engineering-principles, accessibility-wcag-aa, brand-growth, etc.) dropped — sulis ports those on demand. |
