---
id: WP-003
title: Extend requirements-analyst agent prompt — Phase 3 question-asking + canonical citation
status: pending
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-003
dependsOn: [WP-001]
blocks: [WP-008]
estimated_token_cost:
  input: 5k
  output: 3k
tdd_section: Form §requirements-analyst row (line 131); FR-003
adrs: [ADR-001, ADR-004]
verification:
  adapter: methodology
  artifact: tests/methodology/p_ver/fixtures/test_agent_prompts_cite_canonical.py::test_requirements_analyst_cites_canonical
---

## Context

Extends `plugins/sulis/agents/requirements-analyst.md` (the agent that
backs `/sulis:specify`) so that during Phase 3 (Convergent Specification)
the agent reads the canonical question set + asks each applicable
question in plain English, one at a time.

**TDD reference:** Form pillar row at line 131. FR-003 specifies the
agent must cite the canonical by relative path and MUST NOT inline-
duplicate the question text.

**Why this depends on WP-001.** The agent prompt cites the canonical
file by path; the path must exist for the cite to be valid (P-VER
failure mode 4 would fire on a hallucinated path otherwise).

**Pre-Work Prior-Art Check:** `requirements-analyst.md` is 3374 LOC
pre-change. Phase 3 already exists; the extension adds a new sub-section
to Phase 3 instructing question-reading + asking, plus an extension to
the Phase 3 output spec naming the `## Verification Plan` section as a
required SRD subsection.

## Contract

### Files modified

- `plugins/sulis/agents/requirements-analyst.md` — EXTEND (3374 LOC pre)

### Sections added / modified

**New sub-section inside Phase 3 — "Asking the Verification Questions"**
(≈ 40-60 LOC added):

- Instruction to read `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`
  at the start of Phase 3 (single load; no re-read mid-phase).
- Instruction to ask Q1-Q4 (foundational) once per change in plain English,
  one at a time, recording answers in the journal.
- For every integration the SRD names: ask Q5-Q13 (per-integration).
- Infer the change's `kind:` from the SRD's primitive / impact hints;
  ask if ambiguous. Then ask Q14-Q20 (per-kind adapter) — exactly one
  adapter row, selected by the kind.
- Instruction to populate the `## Verification Plan` section (per
  the requirements-templates SKILL.md template — WP-006 introduces it)
  with the recorded answers.
- Instruction to attach the HTML-comment citation annotation:
  `<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->`
  in the section header area.

**New row in the agent's "Required reading" section** citing the
canonical by relative path. **No inline duplication of question text.**

**New row in the Phase 3 output spec** naming the
`## Verification Plan` section as a required output of the produced SRD,
with the six subsection headings from FR-001:

1. `### What user-observable behaviour are we verifying?`
2. `### Verification environment(s)`
3. `### Bootstrap-from-zero case`
4. `### Per-integration verification strategy`
5. `### Per-kind verification adapter`
6. `### Infrastructure needs surfaced (deferred)`

**Alt-flow prose (per UC-001 alt-A and alt-B):**

- If the founder answers "I don't know yet" to a per-integration question:
  record `deferred — need infrastructure to answer X` under
  "Infrastructure needs surfaced (deferred)" with a canonical need
  identifier per FR-011 (recipe in TDD §Canonical Identifiers).
- If the change is a trivial-change carveout candidate: populate with
  `n/a — trivial-change carveout: <justification>` (justification
  required, ≥ 30 substantive chars per MUC-008).

**Exception-flow prose (per UC-001 exception):**

- If the founder answers with `TBD` / blank / `?`: the agent must re-ask
  the specific question, not silently accept the placeholder. P-VER
  failure mode 2 would otherwise fire downstream.

## Definition of Done

### Red — Failing tests written first

- [ ] `tests/methodology/p_ver/fixtures/test_agent_prompts_cite_canonical.py::test_requirements_analyst_cites_canonical` exists and asserts:
  - `plugins/sulis/agents/requirements-analyst.md` contains the literal string `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` at least once.
  - The file contains the HTML-comment annotation `<!-- VERIFICATION_QUESTIONS source: ` somewhere in its instruction prose.
  - A grep for the canonical question text (e.g., `What user-observable behaviour are we verifying?` appearing as a *question instruction*, not as an example header) returns zero hits in this file (NFR-004 anti-duplication check).
  - Phase 3's output spec contains the six required subsection headings.
- [ ] Initial run of the test FAILS.

### Green — Implementation makes tests pass

- [ ] Extend `plugins/sulis/agents/requirements-analyst.md` per the Contract section above.
- [ ] Citation to canonical present (NFR-006).
- [ ] HTML-comment annotation present (matches WP-001's matcher pattern).
- [ ] No inline duplication of question text (NFR-004).
- [ ] Phase 3 output spec extended with six required subsection headings.
- [ ] Alt-flow + exception-flow prose present.
- [ ] Test from Red phase passes.

### Blue — Refactor + polish

- [ ] Inserted prose fits the agent's existing voice + style.
- [ ] Founder-facing prompts (the questions the agent reads aloud) are
  founder-English (FE-01..11 — no internal IDs in the questions; plain
  language).
- [ ] Cross-reference to `VERIFICATION_QUESTIONS.md` is by relative path,
  not absolute.
- [ ] No restating of the canonical's content — cite only.

## Sequence

- **Sequence ID:** WP-003
- **dependsOn:** WP-001 (the canonical file must exist for the cite to be valid)
- **blocks:** WP-008 (E2E test dispatches the updated agent)
- **Parallelisable with:** WP-002, WP-004, WP-006 (different files)

## Estimated Token Cost

- **Input:** ~5k (Phase 3 of the agent prompt + ADR-001 + ADR-004 + the 20-question list)
- **Output:** ~3k (≈ 60 lines of new prose + a section extension)
- **Total:** ~8k

## Notes

- **Anti-pattern alert (MUC-003):** the temptation here is to inline the
  question text "for convenience". Forbidden. The agent must read the
  canonical at runtime, every time. Drift between the canonical and an
  inlined copy is exactly what this change exists to prevent.
- **The agent dispatches one question at a time** per the existing
  facilitation rules; this WP doesn't change the rate of asking, only
  the *source* of the questions.
- **Phase 5 (completeness verification) is unchanged in this WP** — it
  already runs the rubric pass; the new P-VER phase plugs in via WP-006's
  rubric-invocation extension.
