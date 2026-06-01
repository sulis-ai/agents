---
id: WP-001
title: Author canonical VERIFICATION_QUESTIONS.md (20 questions + 7-kind adapter table + version)
status: pending
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
kind: docs
primitive: create
group: GENERATE
sequence_id: WP-001
dependsOn: []
blocks: [WP-002, WP-003, WP-004, WP-005, WP-006, WP-007, WP-008]
estimated_token_cost:
  input: 2k
  output: 5k
tdd_section: Form §canonical seam (line 129); FR-006, FR-007
adrs: [ADR-004, ADR-007]
verification:
  adapter: methodology
  artifact: tests/methodology/p_ver/fixtures/canonical_verification_questions_structural_test.py::test_canonical_shape
---

## Context

**Keystone WP.** Authors the single source of truth this entire change
hangs on: `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`.
Every other WP in this change cites this file by relative path; none
of them inline-duplicate.

**TDD reference:** Form pillar identifies one structural seam at line
129 — this file. ADR-004 fixes the location at
`plugins/sulis/references/standards/`. ADR-007 fixes the seven-row
adapter table.

**Why this is the keystone.** No consumer (rubric, agent prompt, skill
prose) can cite this file until it exists. P-VER's citation-presence
check (failure mode 6) refers to this file by path; the rubric cannot
fail-if-missing on a file that itself doesn't exist.

**Pre-Work Prior-Art Check (per `/sulis:plan-work` Step 1):** searched
`plugins/sulis/references/standards/` — no existing
`VERIFICATION_QUESTIONS.md`. No conflicting standard. Closest neighbour
is `decompose-validation-rubric.md` which will *consume* this file
(extended by WP-002), not host its content.

## Contract

### Files created

- `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` — NEW

### Document structure (required)

The file MUST contain, in order:

1. **Front matter** — version field (`version: 1.0.0`), status (`active`),
   purpose (one paragraph).
2. **The 20 canonical questions verbatim** under three labelled groups:
   - `## Foundational (Q1-Q4)` — asked once per change
   - `## Per-integration (Q5-Q13)` — asked once per touched integration
   - `## Per-kind verification adapter (Q14-Q20)` — asked once per change,
     scoped by the change's `kind:`
3. **The seven-row kind→adapter table** (per ADR-007). Each row: `kind`,
   one-line adapter description, concrete verification shape (a worked
   example reference).
4. **Usage block** — short prose instructing consumers (agents, skills,
   rubrics) to **cite this file by relative path**, never inline-duplicate
   the question text (NFR-004, NFR-006). Includes the HTML-comment
   annotation shape the matcher pattern expects:
   `<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->`.
5. **Version history table** — same shape as the
   `decompose-validation-rubric.md` history table (version / date / change).

### Adapter table (verbatim, from ADR-007)

| kind            | adapter (one-liner)                                                                                   |
|---              |---                                                                                                    |
| `methodology`   | Structural assertions + integration test where a fresh design dispatch produces output with the new shape |
| `backend`       | Behavioural API test against a running service + persistence assertion + (where applicable) idempotency / replay check |
| `frontend`      | Component-rendering test with axe-core a11y + visual diff against the design-system tokens + interaction test |
| `async`         | Producer-publishes + consumer-receives integration test against a real broker (or test-container) + dead-letter / replay assertion |
| `infrastructure`| Apply-and-rollback integration test against ephemeral target + drift-check + cost / quota guardrail |
| `documentation` | Link-resolution check + readability score (FK ≤ 10 for founder-facing) + freshness-of-cited-sources check |
| `contract`      | Contract conformance test on both sides of the seam (provider + consumer) + schema-evolution compatibility check |

### The 20 questions (source-of-truth)

Foundational (Q1-Q4) — sourced from the dispatch brief + SRD §"Why this is now":

- Q1. What user-observable behaviour are we verifying?
- Q2. In what environment(s) does verification run (local / CI / dev / staging)?
- Q3. Can the change be verified from a fresh clone with zero prior state (bootstrap-from-zero)?
- Q4. What is the change's `kind:` (drives the adapter choice)?

Per-integration (Q5-Q13) — one set per touched integration:

- Q5. Which external integrations does the change touch (vendors, APIs, brokers)?
- Q6. Is each integration verified real, deferred, or out-of-scope?
- Q7. For real integrations: what credentials / test accounts / sandboxes are required?
- Q8. For deferred integrations: what is the canonical need identifier (slug)?
- Q9. For out-of-scope integrations: what is the justification?
- Q10. Are there idempotency / replay concerns at the integration boundary?
- Q11. Are there auth / authz boundaries crossed by the integration?
- Q12. What is the failure mode if the integration is unavailable during verification?
- Q13. What observability (trace / log / metric) is asserted at the integration boundary?

Per-kind adapter (Q14-Q20) — selected by Q4's answer:

- Q14. Which adapter row applies (from the seven-row table)?
- Q15. What is the concrete test artifact path (per Shape 1 of ADR-003)?
- Q16. If deferred (Shape 2): what is the follow-on identifier?
- Q17. If trivial carveout (Shape 3): what is the justification?
- Q18. Does the WP span multiple adapters (additional-adapters list)?
- Q19. What infrastructure does the adapter need (existing / deferred / out-of-scope)?
- Q20. Is the dogfood acceptance criterion satisfied (the change's own artifacts pass P-VER)?

## Definition of Done

### Red — Failing tests written first

- [ ] `tests/methodology/p_ver/fixtures/canonical_verification_questions_structural_test.py::test_canonical_shape` exists and asserts:
  - File at `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` exists.
  - File contains version field `1.0.0`.
  - File contains 20 questions (regex count of `^- Q\d+\.` ≥ 20).
  - File contains seven adapter rows (regex count of `^\| \`(methodology|backend|frontend|async|infrastructure|documentation|contract)\`` = 7).
  - File contains the HTML-comment annotation shape in the usage block.
- [ ] Initial run of the test FAILS (file does not exist).

### Green — Implementation makes tests pass

- [ ] Author `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` per the structure above.
- [ ] All 20 questions present verbatim.
- [ ] Seven-row adapter table present (matching ADR-007's table).
- [ ] Usage block instructs consumers to cite, not duplicate.
- [ ] Version field `1.0.0`.
- [ ] Test from Red phase passes.

### Blue — Refactor + polish

- [ ] File reads cleanly in founder English (FE-04 — scannable in 30 seconds for the usage block; question groups labelled with plain headings).
- [ ] No internal jargon in the question text (FE-03).
- [ ] Cross-reference links to ADR-004 (location), ADR-007 (adapter table), SRD FR-006 / FR-007.
- [ ] Version history table seeded with the v1.0.0 row.

## Sequence

- **Sequence ID:** WP-001 (keystone, runs first)
- **dependsOn:** none — keystone
- **blocks:** WP-002, WP-003, WP-004, WP-005, WP-006, WP-007, WP-008 (everything else needs this file to exist)
- **Parallelisable with:** none — must complete first

## Estimated Token Cost

- **Input:** ~2k (ADR-007 + ADR-004 + dispatch brief Q-list + SRD §FR-006/FR-007)
- **Output:** ~5k (the new 100-200 line standard file)
- **Total:** ~7k

## Notes

- This file is **the contract**. Every other WP in this change reads it
  by citation. If the question text or adapter row content changes after
  this WP ships, the version field bumps and downstream consumers'
  currency check (P-VER failure mode 7) catches the drift.
- **No tests for the questions' wording.** Wording polish happens in
  Blue; the structural assertions are about presence + count + shape,
  not about specific sentences. The questions are prose, not API.
- **No inline duplication anywhere else.** If WP-002 / WP-003 / etc.
  try to inline the question text, MUC-003 fires — defended by P-VER
  failure mode 6 (citation-presence check in WP-002).
- **Self-rooted P8 anchor:** the canonical need identifier recipe in
  TDD §Canonical Identifiers lives here too (referenced from the
  per-integration Q8). No P8 violation.
