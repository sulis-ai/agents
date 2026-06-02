---
id: WP-004
title: Extend engineering-architect agent prompt — concretion questions + SRD↔TDD contradiction surfacing + canonical citation
status: pending
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-004
dependsOn: [WP-001]
blocks: [WP-008]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form §engineering-architect row (line 132); FR-004
adrs: [ADR-001, ADR-004]
verification:
  adapter: methodology
  artifact: tests/methodology/p_ver/fixtures/test_agent_prompts_cite_canonical.py::test_engineering_architect_cites_canonical
---

## Context

Extends `plugins/sulis/agents/engineering-architect.md` (the agent that
backs `/sulis:draft-architecture`) so it (a) reads the SRD's Verification
Plan section as part of standard input, (b) asks the implementation-side
concretion questions for each strategy named in the SRD, (c) populates
the TDD's Verification Plan section with concretised answers, (d) surfaces
explicit contradictions between SRD plan and TDD plan rather than
silently overriding.

**TDD reference:** Form pillar row at line 132. FR-004 specifies the
agent must cite the canonical + ask concretion questions + surface
contradictions.

**Why this depends on WP-001.** Same as WP-003 — the agent prompt cites
the canonical file by path; the path must exist.

**Pre-Work Prior-Art Check:** `engineering-architect.md` is 822 LOC
pre-change. It already has prose for "ingest the SRD"; the extension
adds explicit Verification Plan ingestion + concretion-question
instruction + the contradiction-surface instruction.

## Contract

### Files modified

- `plugins/sulis/agents/engineering-architect.md` — EXTEND (822 LOC pre)

### Sections added / modified

**Extension to the agent's "Reading the SRD" section** (≈ 20-30 LOC):

- Explicit instruction to read the SRD's `## Verification Plan` section
  as a first-class input (not optional, not skippable).
- Instruction to parse each of the six subsections.
- Instruction to apply the per-kind adapter from
  `VERIFICATION_QUESTIONS.md` matching the change's `kind:` value.

**New sub-section "Concretion questions"** (≈ 30-40 LOC):

- For each strategy named in the SRD's "Per-integration verification
  strategy" subsection, the agent MUST resolve the SRD's abstractions
  ("real vs mocked") into TDD-level specifics:
  - Specific test artifact path (e.g.,
    `tests/api/test_orders.py::test_post_creates_order`).
  - Specific mock identity / fixture location / sandbox endpoint.
  - Specific resilience primitive (timeout / retry / circuit breaker)
    if the integration is over HTTP/RPC.
- For each `existing` infrastructure piece named in the SRD: the agent
  MUST verify the path resolves at design time (matches P-VER failure
  mode 4 — the agent surfaces hallucinated paths before they reach the
  rubric).
- For each `deferred` entry: the agent MUST confirm the canonical need
  identifier follows the recipe (TDD §Canonical Identifiers).

**New sub-section "Surfacing contradictions"** (UC-002 alt-A, ≈ 20 LOC):

- When the TDD's concretion of a strategy contradicts the SRD's plan
  (e.g., SRD says "real Stripe sandbox", TDD says "recording mock"),
  the agent MUST NOT silently override. It surfaces the contradiction
  explicitly in a `## Open Architecture Questions` row or as an inline
  `**Contradiction with SRD:** {what SRD said} → {what TDD proposes}`
  callout, and either resolves to one ADR or escalates to the founder.

**New row in the agent's "Required reading" section** citing
`VERIFICATION_QUESTIONS.md` by relative path. **No inline duplication.**

**Extension to the TDD output spec** naming the
`## Verification Plan` section as a required TDD output. The TDD's plan
concretises the SRD's plan, citing the SRD by relative path (so the
trace from SRD to TDD is explicit per CW-05 / load-bearing-context
discipline). The HTML-comment annotation goes on the TDD's section too.

## Definition of Done

### Red — Failing tests written first

- [ ] `tests/methodology/p_ver/fixtures/test_agent_prompts_cite_canonical.py::test_engineering_architect_cites_canonical` exists and asserts:
  - `plugins/sulis/agents/engineering-architect.md` contains the literal string `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` at least once.
  - The file contains the HTML-comment annotation pattern.
  - A grep for canonical question text returns zero hits (anti-duplication).
  - The agent prompt contains the phrase `Contradiction with SRD` (or equivalent contradiction-surface marker).
  - The TDD output spec lists `## Verification Plan` as required.
- [ ] Initial run of the test FAILS.

### Green — Implementation makes tests pass

- [ ] Extend `plugins/sulis/agents/engineering-architect.md` per the Contract section above.
- [ ] Citation to canonical present.
- [ ] HTML-comment annotation present in the TDD output template.
- [ ] No inline duplication of question text.
- [ ] Concretion-question sub-section present with the worked examples shown above.
- [ ] Contradiction-surface sub-section present.
- [ ] TDD output spec extended with `## Verification Plan` as required output.
- [ ] Test from Red phase passes.

### Blue — Refactor + polish

- [ ] Inserted prose matches the engineering-architect's senior-engineer voice.
- [ ] Concretion-question examples are realistic + traceable to TDD §Canonical Identifiers.
- [ ] Cross-reference to `VERIFICATION_QUESTIONS.md` is by relative path.
- [ ] No restating of the canonical's content.

## Sequence

- **Sequence ID:** WP-004
- **dependsOn:** WP-001 (canonical file must exist)
- **blocks:** WP-008 (E2E test dispatches the updated agent)
- **Parallelisable with:** WP-002, WP-003, WP-006 (different files)

## Estimated Token Cost

- **Input:** ~3k (relevant portions of the agent prompt + ADR-001 + ADR-004 + the seven adapters)
- **Output:** ~3k (≈ 80 lines of new prose)
- **Total:** ~6k

## Notes

- **Anti-pattern alert (MUC-003):** same as WP-003 — the temptation to
  inline the question text is the failure mode this change prevents.
- **The agent's Phase 5 (rubric pass) is unchanged in this WP.** It will
  invoke P-VER once WP-006 wires the rubric-invocation in.
- **Contradiction-surfacing is load-bearing.** Without it, the TDD can
  quietly disagree with the SRD and the founder never knows. UC-002
  alt-A's whole point is to make disagreement explicit.
