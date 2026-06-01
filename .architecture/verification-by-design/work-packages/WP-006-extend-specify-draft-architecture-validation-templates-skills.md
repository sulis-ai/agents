---
id: WP-006
title: Wire P-VER into specify / draft-architecture / requirements-validation skills + add Verification Plan template block
status: pending
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-006
dependsOn: [WP-001, WP-002, WP-003, WP-004]
blocks: [WP-008]
estimated_token_cost:
  input: 6k
  output: 4k
tdd_section: Form §specify/draft-architecture/requirements-validation rows (lines 134-136); Form §requirements-templates row (line 137); FR-001, FR-002, FR-009
adrs: [ADR-001, ADR-004]
verification:
  adapter: methodology
  artifact: tests/methodology/p_ver/fixtures/test_orchestrator_skills_invoke_pver.py::test_specify_and_draft_architecture_and_validation_invoke_pver
---

## Context

Wires P-VER into the three orchestrator skills + adds the
`## Verification Plan` template block to `requirements-templates/SKILL.md`.
Each skill update is small (≈ 20-40 LOC) and they share dependencies
(WP-001 canonical, WP-002 rubric, WP-003 + WP-004 agent prompts) — so
they ship together as one orchestrator-skill-glue WP.

**TDD reference:** Form pillar rows at lines 134-137. FR-001 (SRD
template), FR-002 (TDD template — produced by draft-architecture), FR-009
(rubric P-VER invoked by validation).

**Why one WP, not four?** Each skill's change is a small wiring
extension citing the same upstream files (WP-001 canonical + WP-002
rubric + WP-003/004 agents). Splitting into four WPs would inflate
sequencing without adding atomicity — each individual change is < 50 LOC
and they all read the same upstream. P2 atomicity test (one engineer,
one branch): one engineer can hold the four wiring changes in their head.
Touch surface: 4 files, well under the 15-file MUST ceiling.

**Pre-Work Prior-Art Check:** each file already has its own orchestrator
structure. The extensions plug into existing dispatch / rubric / template
hooks; no new top-level sections.

## Contract

### Files modified

- `plugins/sulis/skills/specify/SKILL.md` — EXTEND (494 LOC pre)
- `plugins/sulis/skills/draft-architecture/SKILL.md` — EXTEND (565 LOC pre)
- `plugins/sulis/skills/requirements-validation/SKILL.md` — EXTEND (701 LOC pre)
- `plugins/sulis/skills/requirements-templates/SKILL.md` — EXTEND (745 LOC pre)

### specify/SKILL.md changes (≈ 20-30 LOC)

- Cite `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` in the
  Required Reading section.
- Cite `plugins/sulis/references/decompose-validation-rubric.md` §Phase 9
  (P-VER).
- After the existing requirements-analyst dispatch step, invoke P-VER
  against the produced SRD as part of the completeness-verification step.
- Failure mode: if P-VER fails, surface the founder-readable failure
  message + re-enter Phase 3 for the unresolved questions.

### draft-architecture/SKILL.md changes (≈ 20-30 LOC)

- Cite `VERIFICATION_QUESTIONS.md` + the rubric file in Required Reading.
- After the existing engineering-architect dispatch step, invoke P-VER
  against the produced TDD.
- Surface SRD↔TDD contradictions per UC-002 alt-A (the agent's job per
  WP-004; the skill's job is to render them to the founder).

### requirements-validation/SKILL.md changes (≈ 20-30 LOC)

- Cite `VERIFICATION_QUESTIONS.md` + the rubric.
- Extend the rubric-invocation step to invoke P-VER as part of the rubric
  pass.
- Verdict semantics: P-VER FAIL → overall rubric FAIL (per the
  rubric's verdict computation).

### requirements-templates/SKILL.md changes (≈ 50-70 LOC) — the template block

- New top-level template block named "Verification Plan section template"
  near the existing SRD section templates.
- The block contains the `## Verification Plan` heading + the six required
  subsections (per FR-001):

  ```markdown
  ## Verification Plan
  
  <!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->
  
  ### What user-observable behaviour are we verifying?
  
  {agent populates with answer to Q1, ≥ 30 substantive chars}
  
  ### Verification environment(s)
  
  {agent populates with answer to Q2}
  
  ### Bootstrap-from-zero case
  
  {agent populates with answer to Q3}
  
  ### Per-integration verification strategy
  
  {agent populates with answers to Q5-Q13 per touched integration}
  
  ### Per-kind verification adapter
  
  **Adapter (from VERIFICATION_QUESTIONS.md row for `kind: <K>`):** {one-liner}
  
  {agent populates with answers to Q14-Q20}
  
  ### Infrastructure needs surfaced (deferred)
  
  {agent populates with deferred entries per canonical identifier recipe}
  ```

- Cite ADR-001 (section name decision), ADR-007 (adapter table).
- No inline duplication of the question text — instructions read
  "agent answers Q1" etc., referencing the canonical.

## Definition of Done

### Red — Failing tests written first

- [ ] `tests/methodology/p_ver/fixtures/test_orchestrator_skills_invoke_pver.py::test_specify_and_draft_architecture_and_validation_invoke_pver` exists and asserts:
  - Each of the three orchestrator SKILL.md files cites the rubric (or its P-VER phase).
  - Each contains an invocation step naming P-VER explicitly.
- [ ] `tests/methodology/p_ver/fixtures/test_template_block_in_requirements_templates.py::test_verification_plan_template_present` exists and asserts:
  - `plugins/sulis/skills/requirements-templates/SKILL.md` contains a `## Verification Plan` template block.
  - The block contains all six required subsection headings in order.
  - The block contains the HTML-comment annotation.
  - The block contains no inline duplication of canonical question text.
- [ ] Both tests FAIL initially.

### Green — Implementation makes tests pass

- [ ] Extend `specify/SKILL.md` per Contract.
- [ ] Extend `draft-architecture/SKILL.md` per Contract.
- [ ] Extend `requirements-validation/SKILL.md` per Contract.
- [ ] Extend `requirements-templates/SKILL.md` with the template block.
- [ ] All citations to canonical / rubric / ADRs present.
- [ ] Both tests from Red phase pass.

### Blue — Refactor + polish

- [ ] Each skill's extension fits the file's existing voice + structure.
- [ ] The template block uses founder-English placeholder text (FE-04 — readable in plain English).
- [ ] No inline duplication anywhere.
- [ ] Cross-references between the four files are by relative path.

## Sequence

- **Sequence ID:** WP-006
- **dependsOn:** WP-001 (canonical), WP-002 (rubric P-VER spec), WP-003 (requirements-analyst extended — specify orchestrates it), WP-004 (engineering-architect extended — draft-architecture orchestrates it)
- **blocks:** WP-008 (E2E test runs through these orchestrators)
- **Parallelisable with:** WP-005, WP-007 (different files)

## Estimated Token Cost

- **Input:** ~6k (four SKILL.md files relevant sections + the four ADRs + the template structure)
- **Output:** ~4k (≈ 130 LOC across four files)
- **Total:** ~10k

## Notes

- **Why this WP is co-located (justification recorded for P2 atomicity):**
  four small file edits (< 50 LOC each), all wiring the same upstream
  (canonical + rubric + agents) into orchestrators. Splitting into four
  WPs would inflate the dependency graph without adding atomicity. P2 test
  (one engineer, one branch): four small wiring changes fit one branch +
  one PR; no cross-skill coordination needed.
- **Anti-pattern alert (MUC-003):** the requirements-templates SKILL.md
  template block is the most tempting place to inline the questions.
  Forbidden — it uses placeholder instructions ("agent answers Q1") that
  read the canonical at runtime.
- **No new top-level sections in the orchestrator SKILL.md files.** All
  extensions plug into existing dispatch / completeness-verification /
  rubric-invocation steps.
