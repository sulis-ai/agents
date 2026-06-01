---
id: WP-002
title: Extend decompose-validation-rubric.md with P-VER (8 failure modes + grandfather + merge-date constant)
status: pending
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-002
dependsOn: [WP-001]
blocks: [WP-005, WP-007, WP-008]
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: Form §rubric host (line 130); Armor §gate-integrity table (lines 191-200); FR-009, FR-010, FR-014, FR-016
adrs: [ADR-002, ADR-006]
verification:
  adapter: methodology
  artifact: tests/methodology/p_ver/fixtures/test_p_ver_phase.py::test_phase_pver_present_and_complete
---

## Context

Adds a new phase (**P-VER**, numbered P9) to
`plugins/sulis/references/decompose-validation-rubric.md`. P-VER is the
methodology gate that asserts every change's SRD, TDD, and WP set carries
a populated Verification Plan section + valid per-WP `verification:`
frontmatter.

**TDD reference:** Form pillar line 130 names this file as the rubric
host. Armor pillar lines 191-200 enumerate the eight failure modes P-VER
must implement (one per MUC system response).

**Why this depends on WP-001.** P-VER's citation-presence check (failure
mode 6) references `VERIFICATION_QUESTIONS.md` by relative path. Until
WP-001 lands, P-VER points at a non-existent file.

**Why this also carries the merge-date constant.** FR-016 mandates the
constant be machine-readable, committed alongside the rubric extension.
ADR-002 fixes the location at the rubric file's front matter
(`verification_required_from:`) — `sulis-change finish` fills it in at
merge time.

**Pre-Work Prior-Art Check:** `decompose-validation-rubric.md` already
has Phase 8 (added 2026-06-01). P-VER becomes Phase 9. The existing
phases' check ID convention (`{phase}.{NN}`) extends naturally to
`9.01..9.NN`.

## Contract

### Files modified

- `plugins/sulis/references/decompose-validation-rubric.md` — EXTEND
  (424 LOC pre, est. +200 LOC post)

### Sections added / modified

**Front matter — new field (no shape change to existing keys):**

```yaml
verification_required_from: ""    # ISO-8601 date; filled in by sulis-change finish at merge
```

**New "Phase 9 — P-VER (Verification Plan)" section** between the existing
"Phase 8 — Cross-WP identifier canonicalisation" and "Anti-patterns for
the validation run itself" sections.

**New eight failure-mode check rows (9.01..9.08)** — one per Armor pillar
table row in the TDD:

| ID | Severity | Check | Pass criterion | MUC |
|---|---|---|---|---|
| **9.01** | MUST | `## Verification Plan` section present in SRD and TDD | Section header regex match | (structural) |
| **9.02** | MUST | No placeholder content in any required subsection | Block-list scan + ≥30 substantive chars per subsection | MUC-001 |
| **9.03** | MUST | `n/a` answers carry a ≥30-char justification | Per-subsection scan; bare `n/a` fails | MUC-008 |
| **9.04** | MUST | Named `existing` infrastructure paths resolve | Repo grep against each cited path | MUC-002 |
| **9.05** | MUST | The change's `kind:` has an adapter row in the canonical | Lookup against `VERIFICATION_QUESTIONS.md`'s table | MUC-007 |
| **9.06** | MUST | The artifact contains a literal citation to `VERIFICATION_QUESTIONS.md` | Regex match on the path + HTML-comment annotation | MUC-003 |
| **9.07** | MUST | Citation version is within currency of the canonical's version field | Parse canonical version, parse citation version, compare semver-minor | MUC-004 |
| **9.08** | MUST | Per-WP `verification:` field present + adapter matches kind | YAML parse of WP frontmatter; lookup against canonical adapter table | MUC-006, MUC-007 |

**New "Grandfather check" sub-phase (per ADR-002 + ADR-006):**

- Before any 9.01..9.08 check runs, the rubric reads `started_at` from
  `.changes/{slug}.yaml` and compares against `verification_required_from`.
- If `started_at` precedes the constant → return `PASS — grandfathered`,
  skip all P-VER checks.
- If the constant is empty (pre-merge state, dogfood case) → run all
  checks against the live artifacts (NFR-005 dogfood gate).
- If `started_at` is missing or unparseable → fall back to "not
  grandfathered" and apply P-VER normally.
- Edits to grandfathered changes inherit grandfather status (ADR-006);
  edit-status is read from the change record, not inferred.

**New "Verdict semantics" sub-section:**

- Any 9.01..9.08 MUST failure halts decomposition with the failure
  message format: `P-VER: {check ID} failed for {artifact path}.
  Remediation: {one-line action}.`
- The remediation strings are founder-readable (FE-01..11 applied per
  the open question pinned in TDD §"Open Architecture Questions" item 2).

**New row in the Verdict + Phase-by-phase results tables** so the
summary table includes Phase 9.

**New row in the Methodology self-attestation** so the rubric run
reports its P-VER coverage:

```markdown
- [✓] **P9 P-VER (Verification Plan).** <N> artifacts checked. Section
  presence: <K> pass / <M> fail. Placeholder scan: <K> pass / <M> fail.
  Citation presence: <K> pass / <M> fail. Per-WP field: <K> pass / <M>
  fail. Grandfather: <N> grandfathered changes skipped.
```

**New row in the Version history table:**

```markdown
| 0.3.0 | <date filled at merge> | Added Phase 9 — P-VER (Verification
Plan). 8 failure-mode checks + grandfather sub-phase. Anchor case:
release-train + discovery dogfood — both shipped without end-to-end
verification, surfacing two latent defects post-merge. |
```

## Definition of Done

### Red — Failing tests written first

- [ ] `tests/methodology/p_ver/fixtures/test_p_ver_phase.py::test_phase_pver_present_and_complete` exists and asserts:
  - The rubric file contains a `## Phase 9 — P-VER (Verification Plan)` section header.
  - The section contains rows for checks 9.01..9.08 (regex count of `^\| \*\*9\.\d{2}\*\*` = 8).
  - The rubric front matter contains `verification_required_from:` key.
  - The Methodology self-attestation block contains a P9 row.
- [ ] Initial run of the test FAILS (the section doesn't exist yet).

### Green — Implementation makes tests pass

- [ ] Extend `decompose-validation-rubric.md` per the Contract section above.
- [ ] All eight check rows present with the IDs / severities / criteria specified.
- [ ] Grandfather sub-phase prose present, citing ADR-002 + ADR-006.
- [ ] Front matter has `verification_required_from:` (empty string default).
- [ ] Methodology self-attestation extended.
- [ ] Phase-by-phase results table extended with Phase 9 row.
- [ ] Version history extended with the 0.3.0 row.
- [ ] Test from Red phase passes.

### Blue — Refactor + polish

- [ ] Each failure message string is founder-readable (FE-04 — concrete next-action, no jargon).
- [ ] Cross-reference link from each check row back to the source MUC + the source TDD §Armor pillar row.
- [ ] Section ordering preserved (Phase 9 between Phase 8 and Anti-patterns).
- [ ] No restating of `VERIFICATION_QUESTIONS.md` content — citation only.

## Sequence

- **Sequence ID:** WP-002
- **dependsOn:** WP-001 (P-VER cites the canonical by path; the path must exist)
- **blocks:** WP-005 (plan-work needs P-VER to validate `verification:` field), WP-007 (fixtures assert against P-VER), WP-008 (E2E test invokes P-VER)
- **Parallelisable with:** WP-003, WP-004, WP-006 (different files; no shared edit surface)

## Estimated Token Cost

- **Input:** ~4k (existing rubric 424 lines + ADR-002 + ADR-006 + Armor table from TDD)
- **Output:** ~4k (≈ 200 lines of new prose + table rows)
- **Total:** ~8k

## Notes

- **P-VER is prose, not Python.** This WP authors the rubric *check spec*;
  the actual enforcement is invocation by the validating skill / agent
  (WP-005, WP-006). The fixture tests in WP-007 assert the prose contract.
- **The merge-date constant is the only field `sulis-change finish` must
  touch in this file** at merge time. Everything else is committed in
  this WP and never edited by the finish flow.
- **No code execution in this WP.** The Python implementation of P-VER
  (if any) lives in the existing `plugins/sulis/scripts/` rubric harness;
  this WP only authors the prose spec it reads.
